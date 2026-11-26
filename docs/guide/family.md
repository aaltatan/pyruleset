# With the family

pyruleset needs only callables, but it fits three packages by the same author:

- [pyspecification](https://aaltatan.github.io/pyspecification/) predicates as **conditions**,
- [pyformula](https://aaltatan.github.io/pyformula/) formulas as **values**,
- [pyflowstep](https://aaltatan.github.io/pyflowstep/) flows as values that **run a procedure**.

None of them is a dependency of pyruleset; install the ones you use.

## Predicates and formulas

```python
from dataclasses import dataclass
from decimal import Decimal

from pyformula import variable
from pyspecification import object_rule

from pyruleset import otherwise, when


@dataclass(frozen=True)
class Order:
    tier: str
    subtotal: Decimal
    items: int


@object_rule()
def tier__eq(order: Order, tier: str) -> bool:
    return order.tier == tier


@object_rule()
def items__ge(order: Order, count: int) -> bool:
    return order.items >= count


@variable()
def subtotal(order: Order) -> Decimal:
    return order.subtotal


price = (
    when(tier__eq("gold"), subtotal * Decimal("0.80"), label="gold 20%")
    | when(items__ge(10), subtotal * Decimal("0.95"), label="bulk 5%")
    | otherwise(subtotal)
)

order = Order("regular", Decimal("150.00"), 12)

assert repr(price) == "Ruleset(gold 20% | bulk 5% | otherwise)"
assert price(order) == Decimal("142.5000")
assert price.explain(order) == "bulk 5%"
```

Predicates name themselves, so unlabelled branches still explain well:

```python
unlabelled = when(items__ge(10), subtotal) | otherwise(subtotal)

assert unlabelled.explain(order) == "items__ge"
```

Predicates combine with `&`, `|` and `~` before they become a condition:

```python
vip_bulk = when(tier__eq("gold") & items__ge(10), subtotal * Decimal("0.70"), label="gold bulk") | price

assert vip_bulk(Order("gold", Decimal("100.00"), 10)) == Decimal("70.00")
```

!!! note "Add rulesets in a function, not with `+`"

    pyformula's `+` does not accept a `Ruleset`: it treats it as a constant and raises
    `TypeError`. To add the results of two rulesets, write a plain function
    (`price(order) + shipping(order)`), or put the ruleset inside a formula from JSON with
    [`WhenCompiler`](#rulesets-inside-formulas).

## Flows as values

A pyflowstep `Flow` turns the ruleset into "pick a procedure and run it":

```python
from pyflowstep import step


@step
def add(total: int, amount: int) -> int:
    return total + amount


bonus = when(lambda n: n >= 100, add(10) >> add(5), label="big") | otherwise(add(0))

assert (bonus(100), bonus(7)) == (115, 7)
```

## From JSON

`PredicateCompiler` compiles conditions and `FormulaCompiler` compiles values:

```python
import json

from pyformula import FormulaCompiler
from pyspecification import Predicate, PredicateCompiler, RuleDoesNotExistError

from pyruleset import RulesetCompiler

rules = {"tier__eq": tier__eq, "items__ge": items__ge}

compiler = RulesetCompiler(
    PredicateCompiler(
        rules,
        lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
    ),
    FormulaCompiler({"subtotal": subtotal}),
)

stored = """
{
  "branches": [
    {"label": "gold 20%",
     "when": {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": false},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.80]}}
  ],
  "otherwise": "subtotal"
}
"""

policy = compiler.compile(json.loads(stored, parse_float=Decimal))

assert repr(policy) == "Ruleset(gold 20% | otherwise)"
assert policy(Order("gold", Decimal("120.00"), 2)) == Decimal("96.0000")
```

A typo keeps pyspecification's own error type, with the JSON path as a note:

```python
typo = json.loads(stored.replace("tier__eq", "tier__is"), parse_float=Decimal)

try:
    compiler.compile(typo)
except RuleDoesNotExistError as error:
    assert error.__notes__ == ["at $.branches[0].when"]
```

## JSON Schema

```python
from jsonschema import Draft202012Validator
from pyspecification import get_expression_json_schema

from pyruleset import get_ruleset_json_schema

formula_schema = {"anyOf": [{"const": "subtotal"}, {"type": "number"}, {"type": "object"}]}

schema = get_ruleset_json_schema(get_expression_json_schema(rules), formula_schema)

validator = Draft202012Validator(schema)

assert validator.is_valid(json.loads(stored))
assert not validator.is_valid(json.loads(stored.replace("tier__eq", "tier__is")))
```

## Rulesets inside formulas

`WhenCompiler` with pyformula: the value compiler gets the generated names as variables,
and `wrap=Formula` makes each ruleset a formula named after its branches.

```python
from pyformula import Formula, decimal_literal, get_formula_json_schema

from pyruleset import WhenCompiler, get_when_json_schema

values = WhenCompiler(
    PredicateCompiler(
        rules,
        lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
    ),
    lambda names: FormulaCompiler({"subtotal": subtotal, **names}, literal=decimal_literal),
    wrap=Formula,
)

gold = {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": False}

discounted = values.compile(
    {
        "operator": "subtract",
        "expressions": [
            "subtotal",
            {
                "when": {
                    "branches": [
                        {
                            "label": "gold",
                            "when": gold,
                            "then": {"operator": "multiply", "expressions": ["subtotal", 0.2]},
                        }
                    ],
                    "otherwise": 0,
                }
            },
        ],
    }
)

assert str(discounted) == "(subtotal - when(gold -> (subtotal * 0.2) | otherwise -> 0))"
assert discounted(Order("gold", Decimal("120.00"), 2)) == Decimal("96.000")
```

Its schema is pyformula's, with the `when` node added:

```python
predicates = get_expression_json_schema(rules)

formulas = get_formula_json_schema({"subtotal": subtotal}, nodes=[get_when_json_schema(predicates)])

nested = Draft202012Validator(get_ruleset_json_schema(predicates, formulas))

assert nested.is_valid({"otherwise": {"when": {"branches": [], "otherwise": "subtotal"}}})
```
