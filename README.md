# pyruleset

Conditional values that compose with `|` and can be defined as JSON: the first branch whose
condition matches decides.

```python
price = (
    when(tier__eq("gold"), subtotal * Decimal("0.80"), label="gold 20%")
    | when(items__ge(10), subtotal * Decimal("0.95"), label="bulk 5%")
    | otherwise(subtotal)
)

price(order)  # Decimal('142.5000')
price.explain(order)  # 'bulk 5%'
```

Conditions are any `T -> bool` callable, such as a
[pyspecification](https://github.com/aaltatan/pyspecification) `Predicate`. Values are any
`T -> V` callable, such as a [pyformula](https://github.com/aaltatan/pyformula) `Formula`, a
[pyflowstep](https://github.com/aaltatan/pyflowstep) `Flow`, or a plain function.

| Piece | What it does |
| --- | --- |
| [`when`, `otherwise`](#quick-start) | Build branches and the fallback, chained with `\|` |
| [`Ruleset`](#deciding-and-explaining) | Callable: returns the value of the first matching branch; `explain` and `decide` say which one |
| [`PartialRuleset`](#a-missing-fallback-is-a-type-error) | Branches without a fallback: composes, but is not callable |
| [`RulesetCompiler`](#from-json) | Builds a `Ruleset` from JSON, delegating `when` and `then` to compilers you inject |
| [`get_ruleset_json_schema`](#json-schema) | The JSON Schema of that JSON, embedding your condition and value schemas |

## Installation

```bash
pip install pyruleset
```

or with uv:

```bash
uv add pyruleset
```

Python 3.12+. The only runtime dependency is
[pyvocabulary](https://github.com/aaltatan/pyvocabulary). pyspecification, pyformula and
pyflowstep are optional: pyruleset only needs callables.

## Quick start

The examples in this README build on each other and run as doctests.

```python
>>> from dataclasses import dataclass
>>> from decimal import Decimal
>>> from pyformula import variable
>>> from pyspecification import object_rule
>>> from pyruleset import otherwise, when

>>> @dataclass(frozen=True)
... class Order:
...     tier: str
...     subtotal: Decimal
...     items: int

>>> @object_rule()
... def tier__eq(order: Order, tier: str) -> bool:
...     return order.tier == tier

>>> @object_rule()
... def items__ge(order: Order, count: int) -> bool:
...     return order.items >= count

>>> @variable()
... def subtotal(order: Order) -> Decimal:
...     return order.subtotal

>>> price = (
...     when(tier__eq("gold"), subtotal * Decimal("0.80"), label="gold 20%")
...     | when(items__ge(10), subtotal * Decimal("0.95"), label="bulk 5%")
...     | otherwise(subtotal)
... )
>>> price
Ruleset(gold 20% | bulk 5% | otherwise)

>>> order = Order("regular", Decimal("150.00"), 12)
>>> price(order)
Decimal('142.5000')

```

Branches are tried in order and the first match wins. Conditions after the match are not
evaluated. When nothing matches, the `otherwise` value is used.

## Deciding and explaining

`explain(subject)` names the branch that decided, e.g. for an audit log: its label, else the
condition's name, else `"otherwise"`. `decide(subject)` returns the `Branch` (or `Otherwise`)
itself.

```python
>>> price.explain(order)
'bulk 5%'
>>> price.explain(Order("regular", Decimal("60.00"), 1))
'otherwise'
>>> price.decide(order)
Branch(condition=..., label='bulk 5%')

>>> unlabelled = when(items__ge(10), subtotal) | otherwise(subtotal)
>>> unlabelled.explain(order), unlabelled
('items__ge', Ruleset(items__ge | otherwise))

```

A condition can return any value: truthy counts as a match.

```python
>>> size = when(len, lambda items: f"{len(items)} items") | otherwise(lambda _: "empty")
>>> size([1, 2]), size([])
('2 items', 'empty')

```

## A missing fallback is a type error

`when(...) | when(...)` is a `PartialRuleset`. It composes, but it has no `__call__`, so a
type checker flags a call to it, and at run time it fails instead of returning `None`. Only
`| otherwise(...)` (or `| ruleset`) makes it callable.

```python
>>> partial = when(tier__eq("gold"), subtotal * Decimal("0.80"), label="gold")
>>> partial
PartialRuleset(gold)
>>> partial(order)
Traceback (most recent call last):
...
TypeError: 'PartialRuleset' object is not callable

```

A `Ruleset` is closed: it has no `|`, so nothing can be added after its fallback by accident.

## Overrides on top of a base policy

`partial | ruleset` puts the partial's branches first. The base policy stays unchanged, and
the override is easy to drop later.

```python
>>> black_friday = when(items__ge(5), subtotal * Decimal("0.70"), label="black friday")
>>> today = black_friday | price
>>> today
Ruleset(black friday | gold 20% | bulk 5% | otherwise)
>>> today(order), price(order)
(Decimal('105.0000'), Decimal('142.5000'))

```

Every operator returns a new object; rulesets are frozen dataclasses.

## Any callable as a value

Values do not have to be formulas. A pyflowstep `Flow` turns the ruleset into "pick a
procedure and run it":

```python
>>> from pyflowstep import step
>>> @step
... def add(total: int, amount: int) -> int:
...     return total + amount

>>> bonus = when(lambda n: n >= 100, add(10) >> add(5), label="big") | otherwise(add(0))
>>> bonus(100), bonus(7)
(115, 7)

```

## From JSON

A definition has `branches` (optional) and `otherwise` (required). Each branch has `when`,
`then` and an optional `label`:

```json
{
  "branches": [
    {"label": "gold 20%",
     "when": {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": false},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.80]}}
  ],
  "otherwise": "subtotal"
}
```

pyruleset does not know the languages inside `when` and `then`. `RulesetCompiler` delegates
them to the compilers you pass in: anything with a `compile(definition)` method, such as
pyspecification's `PredicateCompiler` and pyformula's `FormulaCompiler`.

```python
>>> import json
>>> from pyformula import FormulaCompiler
>>> from pyspecification import Predicate, PredicateCompiler
>>> from pyruleset import RulesetCompiler

>>> rules = {"tier__eq": tier__eq, "items__ge": items__ge}
>>> compiler = RulesetCompiler(
...     PredicateCompiler(
...         rules,
...         lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
...     ),
...     FormulaCompiler({"subtotal": subtotal}),
... )

>>> stored = '''
... {
...   "branches": [
...     {"label": "gold 20%",
...      "when": {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": false},
...      "then": {"operator": "multiply", "expressions": ["subtotal", 0.80]}}
...   ],
...   "otherwise": "subtotal"
... }
... '''
>>> policy = compiler.compile(json.loads(stored, parse_float=Decimal))
>>> policy
Ruleset(gold 20% | otherwise)
>>> policy(Order("gold", Decimal("120.00"), 2))
Decimal('96.0000')

```

### Errors

The whole definition is checked when it is compiled, before any subject is evaluated.

A wrong shape raises `InvalidRulesetDefinitionError` (also a `ValueError`) with its JSON
path:

```python
>>> compiler.compile({"branches": []})
Traceback (most recent call last):
...
pyruleset.exceptions.InvalidRulesetDefinitionError: Invalid ruleset at $: missing 'otherwise'

```

Errors from the injected compilers keep their own type. pyruleset only adds a note with the
full JSON path, nested paths included (e.g. `at $.branches[1].when.expressions[0]`):

```python
>>> from pyspecification import RuleDoesNotExistError
>>> typo = json.loads(stored.replace("tier__eq", "tier__is"), parse_float=Decimal)
>>> try:
...     compiler.compile(typo)
... except RuleDoesNotExistError as error:
...     print(f"{type(error).__name__}: {error}", error.__notes__)
RuleDoesNotExistError: Rule 'tier__is' does not exist. Available rules: tier__eq, items__ge ['at $.branches[0].when']

```

## Money

`json.loads` turns `0.80` into a binary float, which then leaks into every `Decimal` it
touches. Keep money exact in one of two ways:

- Parse with `json.loads(text, parse_float=Decimal)`, as above, so every JSON number with a
  decimal point becomes a `Decimal` before it reaches the compiler.
- Or, with pyformula 0.2+, build the value compiler with
  `FormulaCompiler(variables, literal=decimal_literal)`, which converts each number literal
  through `str` (`Decimal("0.8")`, not `Decimal(0.8)`), whoever parsed the JSON.

## JSON Schema

`get_ruleset_json_schema(condition_schema, value_schema)` describes a definition, e.g. to
validate an admin form or to get completion in an editor. The two schemas describe one
`when` and one `then`/`otherwise`. Each is embedded under its own `$id`, so the
`#/$defs/...` refs inside it keep pointing into itself.

```python
>>> from jsonschema import Draft202012Validator
>>> from pyspecification import get_expression_json_schema
>>> from pyruleset import get_ruleset_json_schema

>>> formula_schema = {"anyOf": [{"const": "subtotal"}, {"type": "number"}, {"type": "object"}]}
>>> schema = get_ruleset_json_schema(get_expression_json_schema(rules), formula_schema)
>>> validator = Draft202012Validator(schema)
>>> validator.is_valid(json.loads(stored))
True
>>> validator.is_valid(json.loads(stored.replace("tier__eq", "tier__is")))
False

```

`jsonschema` is only used here to show the schema at work; pyruleset does not depend on it.

## First match only

A ruleset picks exactly one value. There is no "all matches" mode, on purpose: each ruleset
stays easy to read and to explain. To stack several decisions, give each part its own
ruleset and add the results:

```python
>>> shipping = (
...     when(items__ge(10), lambda _: Decimal("0.00"), label="free shipping")
...     | otherwise(lambda _: Decimal("5.00"))
... )
>>> def total(order: Order) -> Decimal:
...     return price(order) + shipping(order)
>>> small = Order("regular", Decimal("60.00"), 1)
>>> total(small), [price.explain(small), shipping.explain(small)]
(Decimal('65.00'), ['otherwise', 'otherwise'])

```

Progressive brackets (tax bands) are not a ruleset either: they are a sum of clamped terms,
one per band.

## Examples

Runnable scripts in [`examples/`](examples), each asserting its own results:

- [`pricing_policy.py`](examples/pricing_policy.py): a JSON policy from an admin panel,
  rejected on save with the JSON path of a typo, and `explain` for the audit log.
- [`expense_approvals.py`](examples/expense_approvals.py): who approves an expense, with a
  temporary "CFO on leave" override on top of the base policy.
- [`ticket_routing.py`](examples/ticket_routing.py): each branch's value is a pyflowstep
  `Flow` that assigns, prioritizes and tags the ticket.

```bash
uv run python examples/pricing_policy.py
```

## API reference

| Name | Kind | Summary |
| --- | --- | --- |
| `when(condition, value, /, *, label=None) -> PartialRuleset` | function | One branch; chain more with `\|` |
| `otherwise(value, /) -> Otherwise` | function | The fallback that closes a ruleset |
| `Ruleset(branches, fallback)` | class | `__call__(subject)`, `decide(subject)`, `explain(subject)` |
| `PartialRuleset(branches)` | class | `\|` with a partial, an `Otherwise` or a `Ruleset`; not callable |
| `Branch(condition, value, label=None)` | class | One `when` pair; `str()` is its label or condition name |
| `Otherwise(value)` | class | What `decide` returns when no branch matches |
| `FALLBACK_LABEL` | constant | `"otherwise"`, what `explain` returns for the fallback |
| `Condition[T]`, `Value[T, V]` | type | `Callable[[T], Any]`, `Callable[[T], V]` |
| `RulesetCompiler(conditions, values, /)` | class | `compile(definition) -> Ruleset` |
| `Compiler[F]` | protocol | Anything with `compile(definition, /) -> F` |
| `RulesetDict`, `BranchDict` | type | `TypedDict`s of the JSON shape |
| `get_ruleset_json_schema(condition_schema, value_schema, /) -> dict` | function | JSON Schema of a definition |
| `PyrulesetError` | exception | Base class of pyruleset's errors |
| `InvalidRulesetDefinitionError` | exception | Wrong definition shape; also a `ValueError` |

## Development

```bash
uv sync
uv run pytest --cov --cov-branch     # tests, doctests in src/ and this README, examples
uv run --python 3.13 pytest
uvx ruff check . && uvx ruff format --check .
uvx pyright src
```

## License

GPL-3.0-only.
