# pyruleset

Conditional values that compose with `|` and can be defined as JSON: the first branch whose
condition matches decides.

```python
from decimal import Decimal

from pyruleset import otherwise, when

price = (
    when(tier__eq("gold"), subtotal * Decimal("0.80"), label="gold 20%")
    | when(tier__eq("silver") & subtotal__ge(200), subtotal * Decimal("0.90"), label="silver 10%")
    | when(items__ge(10), subtotal * Decimal("0.95"), label="bulk 5%")
    | otherwise(subtotal)
)

price(order)  # Decimal('142.5000')
price.explain(order)  # 'bulk 5%'
price  # Ruleset(gold 20% | silver 10% | bulk 5% | otherwise)
```

Conditions are any `T -> bool` callable, such as a
[pyspecification](https://github.com/aaltatan/pyspecification) `Predicate`. Values are any
`T -> V` callable, such as a [pyformula](https://github.com/aaltatan/pyformula) `Formula` or
a [pyflowstep](https://github.com/aaltatan/pyflowstep) `Flow`.

## Fail early

- A chain without `otherwise(...)` is a `PartialRuleset`, which is not callable, so a missing
  fallback is caught by the type checker.
- `RulesetCompiler` checks the whole definition when it is compiled, and errors carry the
  full JSON path, e.g. `at $.branches[1].when.expressions[0]`.

## From JSON

```python
import json
from decimal import Decimal

from pyruleset import RulesetCompiler

compiler = RulesetCompiler(predicate_compiler, formula_compiler)
policy = compiler.compile(json.loads(stored_policy, parse_float=Decimal))
```

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

## Money

`json.loads` turns `0.80` into a binary float, which then leaks into every `Decimal` it
touches. Keep money exact in one of two ways:

- Parse with `json.loads(text, parse_float=Decimal)`, so every JSON number with a decimal point
  becomes a `Decimal` before it reaches the compiler.
- Or, with pyformula 0.2+, build the value compiler with
  `FormulaCompiler(variables, literal=decimal_literal)`, which converts each number literal
  through `str` (`Decimal("0.8")`, not `Decimal(0.8)`), whoever parsed the JSON.

## JSON Schema

`get_ruleset_json_schema(condition_schema, value_schema)` describes a definition for an
editor or an admin form. The two schemas describe one `when` and one `then`/`otherwise`.
Each is embedded under its own `$id`, so the `#/$defs/...` refs inside it keep working.

```python
from pyspecification import get_expression_json_schema

from pyruleset import get_ruleset_json_schema

schema = get_ruleset_json_schema(get_expression_json_schema(rules), formula_schema)
```

## Examples

- [examples/pricing_policy.py](examples/pricing_policy.py): a JSON policy from an admin panel,
  rejected on save with the JSON path of a typo, and `explain` for the audit log.
- [examples/expense_approvals.py](examples/expense_approvals.py): a base approval policy with a
  temporary override on top (`overrides | policy`).
- [examples/ticket_routing.py](examples/ticket_routing.py): the matching branch picks a
  pyflowstep `Flow` that assigns, prioritizes and tags the ticket.

Python 3.12+. Licensed GPL-3.0-only.
