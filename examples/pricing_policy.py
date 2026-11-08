"""A pricing policy that admins edit in a panel and the shop evaluates.

The panel stores the policy as JSON. Compiling it on save rejects mistakes with
their exact location, and `explain` gives the audit log the branch that priced
each order.

Run with: uv run python examples/pricing_policy.py
"""

import json
from dataclasses import dataclass
from decimal import Decimal

from pyformula import FormulaCompiler, variable
from pyspecification import Predicate, PredicateCompiler, RuleDoesNotExistError, object_rule

from pyruleset import RulesetCompiler


@dataclass(frozen=True, slots=True)
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


compiler = RulesetCompiler(
    PredicateCompiler[Order, bool](
        {"tier__eq": tier__eq, "items__ge": items__ge},
        lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
    ),
    FormulaCompiler[Order]({"subtotal": subtotal}),
)

# What the admin panel saved.
STORED_POLICY = """
{
  "branches": [
    {"label": "gold 20%",
     "when": {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": false},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.80]}},
    {"label": "bulk 5%",
     "when": {"name": "items__ge", "args": [10], "kwargs": {}, "inverse": false},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.95]}}
  ],
  "otherwise": "subtotal"
}
"""

# `parse_float=Decimal` keeps 0.80 exact; plain floats would leak into money.
price = compiler.compile(json.loads(STORED_POLICY, parse_float=Decimal))

for order in (
    Order("gold", Decimal("120.00"), 2),
    Order("regular", Decimal("150.00"), 12),
    Order("regular", Decimal("60.00"), 1),
):
    print(f"{order.tier:<8} {order.items:>2} items  {price(order):>9}  ({price.explain(order)})")

assert price(Order("gold", Decimal("120.00"), 2)) == Decimal("96.0000")
assert price.explain(Order("regular", Decimal("60.00"), 1)) == "otherwise"

# A typo is rejected when the admin saves, not when a customer checks out.
typo = json.loads(STORED_POLICY.replace("items__ge", "itemz__ge"), parse_float=Decimal)
try:
    compiler.compile(typo)
except RuleDoesNotExistError as error:
    print(f"rejected: {error} {error.__notes__}")
    assert error.__notes__ == ["at $.branches[1].when"]
else:
    msg = "the typo should have been rejected"
    raise AssertionError(msg)
