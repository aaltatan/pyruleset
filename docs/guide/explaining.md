# Deciding and explaining

A ruleset can say which branch decided, not only what the result is. That is what support
screens and audit logs need: "this order got the bulk discount".

```python
from dataclasses import dataclass
from decimal import Decimal

from pyruleset import otherwise, when


@dataclass(frozen=True)
class Order:
    tier: str
    subtotal: Decimal
    items: int


def gold(order: Order) -> bool:
    return order.tier == "gold"


def bulk(order: Order) -> bool:
    return order.items >= 10


price = (
    when(gold, lambda o: o.subtotal * Decimal("0.80"), label="gold 20%")
    | when(bulk, lambda o: o.subtotal * Decimal("0.95"))
    | otherwise(lambda o: o.subtotal)
)

order = Order("regular", Decimal("150.00"), 12)
```

## `explain(subject)`

Returns the name of the branch that decides: its label, else its condition's name, else
`"otherwise"` (the constant `FALLBACK_LABEL`).

```python
from pyruleset import FALLBACK_LABEL

assert price.explain(Order("gold", Decimal("100.00"), 1)) == "gold 20%"
assert price.explain(order) == "bulk"
assert price.explain(Order("regular", Decimal("60.00"), 1)) == FALLBACK_LABEL == "otherwise"
```

`explain` evaluates conditions only. It never computes the value, so it is cheap to log
next to the result:

```python
result = price(order)

log = f"{order.tier} order: {result} ({price.explain(order)})"

assert log == "regular order: 142.5000 (bulk)"
```

## `decide(subject)`

Returns the deciding object itself: a `Branch`, or an `Otherwise` when no branch matches.
Use it when you need more than the name, such as the value function or the label:

```python
from pyruleset import Branch, Otherwise

decided = price.decide(order)

assert isinstance(decided, Branch)
assert decided.condition is bulk
assert decided.label is None
assert str(decided) == "bulk"
assert decided.value(order) == Decimal("142.5000")

assert isinstance(price.decide(Order("regular", Decimal("60.00"), 1)), Otherwise)
```

Calling the ruleset is exactly `ruleset.decide(subject).value(subject)`.

## Inspecting a ruleset

`branches` and `fallback` are plain attributes, so a ruleset can be listed, for example in
an admin screen:

```python
assert [str(branch) for branch in price.branches] == ["gold 20%", "bulk"]
assert price.fallback(order) == Decimal("150.00")
```

For a one-line summary that shows each branch with its value, see `describe` in
[Rulesets inside values](nested.md#naming-the-ruleset).
