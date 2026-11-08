from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import pytest
from pyformula import Formula, FormulaCompiler, variable
from pyspecification import Predicate, PredicateCompiler, object_rule

from pyruleset import otherwise, when

type Tier = Literal["regular", "silver", "gold"]


@dataclass(frozen=True, slots=True)
class Order:
    number: str
    tier: Tier
    subtotal: Decimal
    items: int
    coupon: str | None = None


@object_rule()
def tier__eq(order: Order, tier: Tier) -> bool:
    return order.tier == tier


@object_rule()
def subtotal__ge(order: Order, amount: int) -> bool:
    return order.subtotal >= amount


@object_rule()
def items__ge(order: Order, count: int) -> bool:
    return order.items >= count


@object_rule()
def coupon__eq(order: Order, code: str) -> bool:
    return order.coupon == code


@variable()
def subtotal(order: Order) -> Decimal:
    return order.subtotal


ORDERS = {
    "gold": Order("A-1", "gold", Decimal("120.00"), 2),
    "silver_big": Order("A-2", "silver", Decimal("250.00"), 3),
    "silver_bulk": Order("A-3", "silver", Decimal("150.00"), 12),
    "coupon": Order("A-4", "regular", Decimal("60.00"), 1, coupon="WELCOME"),
    "plain": Order("A-5", "regular", Decimal("60.00"), 1),
}


@pytest.fixture
def orders() -> dict[str, Order]:
    return ORDERS


@pytest.fixture
def price_ruleset():
    return (
        when(tier__eq("gold"), subtotal * Decimal("0.80"), label="gold 20%")
        | when(tier__eq("silver") & subtotal__ge(200), subtotal * Decimal("0.90"), label="silver")
        | when(items__ge(10), subtotal * Decimal("0.95"), label="bulk 5%")
        | when(coupon__eq("WELCOME"), subtotal - 10, label="welcome coupon")
        | otherwise(subtotal)
    )


@pytest.fixture
def condition_compiler() -> PredicateCompiler[Order, bool]:
    rules = {
        "tier__eq": tier__eq,
        "subtotal__ge": subtotal__ge,
        "items__ge": items__ge,
        "coupon__eq": coupon__eq,
    }
    return PredicateCompiler[Order, bool](
        rules,
        lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
    )


@pytest.fixture
def value_compiler() -> FormulaCompiler[Order]:
    return FormulaCompiler[Order]({"subtotal": subtotal})


@pytest.fixture
def subtotal_formula() -> Formula[Order]:
    return subtotal
