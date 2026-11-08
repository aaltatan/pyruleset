"""Who approves an expense: a base policy, plus temporary overrides on top.

`overrides | policy` puts the overrides' branches first, so the base policy
stays untouched and the override is easy to remove later.

Run with: uv run python examples/expense_approvals.py
"""

from dataclasses import dataclass
from decimal import Decimal

from pyspecification import object_rule

from pyruleset import otherwise, when


@dataclass(frozen=True, slots=True)
class Expense:
    amount: Decimal
    category: str
    department: str


@object_rule()
def amount__ge(expense: Expense, amount: int) -> bool:
    return expense.amount >= amount


@object_rule()
def category__eq(expense: Expense, category: str) -> bool:
    return expense.category == category


def department_head(expense: Expense) -> str:
    return f"head of {expense.department}"


policy = (
    when(amount__ge(10_000), lambda _: "CFO", label="large")
    | when(category__eq("travel") & amount__ge(1_000), lambda _: "travel desk", label="travel")
    | when(amount__ge(500), department_head, label="medium")
    | otherwise(lambda _: "auto-approved")
)

# While the CFO is on leave, large expenses go to the CEO instead.
cfo_on_leave = when(amount__ge(10_000), lambda _: "CEO", label="CFO on leave")
this_month = cfo_on_leave | policy

print(policy)
print(this_month)
for expense in (
    Expense(Decimal(25_000), "equipment", "IT"),
    Expense(Decimal(1_200), "travel", "sales"),
    Expense(Decimal(800), "software", "IT"),
    Expense(Decimal(40), "office", "HR"),
):
    print(f"{expense.amount:>7} {expense.category:<10} -> {this_month(expense)}")

big = Expense(Decimal(25_000), "equipment", "IT")
assert (policy(big), this_month(big)) == ("CFO", "CEO")
assert this_month.explain(big) == "CFO on leave"
assert this_month(Expense(Decimal(800), "software", "IT")) == "head of IT"
