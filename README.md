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

price(order)          # Decimal('142.5000')
price.explain(order)  # 'bulk 5%'
price                 # Ruleset(gold 20% | silver 10% | bulk 5% | otherwise)
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

Python 3.12+. Licensed GPL-3.0-only.
