# Recipes

Complete, runnable programs for common jobs. Each one is self-contained and is also in the
repository's [`examples/`](https://github.com/aaltatan/pyruleset/tree/main/examples)
folder.

## A pricing policy edited in an admin panel

The panel stores the policy as JSON. Compiling it on save rejects mistakes with their exact
location, and `explain` gives the audit log the branch that priced each order.

Uses pyspecification for conditions and pyformula for values.

```python
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
```

Output:

```text
gold      2 items    96.0000  (gold 20%)
regular  12 items   142.5000  (bulk 5%)
regular   1 items      60.00  (otherwise)
rejected: Rule 'itemz__ge' does not exist. Available rules: tier__eq, items__ge ['at $.branches[1].when']
```

## Expense approvals with a temporary override

Who approves an expense: a base policy, plus a "CFO on leave" override on top.
`overrides | policy` puts the override's branches first, so the base policy stays untouched
and the override is easy to remove later.

```python
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
```

Output:

```text
Ruleset(large | travel | medium | otherwise)
Ruleset(CFO on leave | large | travel | medium | otherwise)
  25000 equipment  -> CEO
   1200 travel     -> travel desk
    800 software   -> head of IT
     40 office     -> auto-approved
```

## Ticket routing with flows

Each branch's value is a pyflowstep `Flow` (`Ticket -> Ticket`), so calling the ruleset
both picks the route and applies it: assign, prioritize, tag.

```python
from dataclasses import dataclass, replace

from pyflowstep import step
from pyspecification import object_rule

from pyruleset import otherwise, when


@dataclass(frozen=True, slots=True)
class Ticket:
    subject: str
    plan: str
    team: str = "unassigned"
    priority: str = "normal"
    tags: tuple[str, ...] = ()


@object_rule()
def plan__eq(ticket: Ticket, plan: str) -> bool:
    return ticket.plan == plan


@object_rule()
def subject__contains(ticket: Ticket, word: str) -> bool:
    return word in ticket.subject.lower()


@step
def assign(ticket: Ticket, team: str) -> Ticket:
    return replace(ticket, team=team)


@step
def prioritize(ticket: Ticket, priority: str) -> Ticket:
    return replace(ticket, priority=priority)


@step
def tag(ticket: Ticket, label: str) -> Ticket:
    return replace(ticket, tags=(*ticket.tags, label))


route = (
    when(subject__contains("outage"), assign("on-call") >> prioritize("urgent"), label="outage")
    | when(plan__eq("enterprise"), assign("enterprise") >> tag("sla"), label="enterprise")
    | when(subject__contains("invoice"), assign("billing"), label="billing")
    | otherwise(assign("support"))
)

for ticket in (
    Ticket("Outage in EU region", "free"),
    Ticket("Need SSO help", "enterprise"),
    Ticket("Wrong invoice amount", "pro"),
    Ticket("How do I export?", "pro"),
):
    routed = route(ticket)
    print(f"{ticket.subject:<22} -> {routed.team:<10} {routed.priority:<6} [{route.explain(ticket)}]")

assert route(Ticket("Outage in EU region", "free")) == Ticket(
    "Outage in EU region", "free", team="on-call", priority="urgent"
)
assert route(Ticket("Need SSO help", "enterprise")).tags == ("sla",)
assert route.explain(Ticket("How do I export?", "pro")) == "otherwise"
```

Output:

```text
Outage in EU region    -> on-call    urgent [outage]
Need SSO help          -> enterprise normal [enterprise]
Wrong invoice amount   -> billing    normal [billing]
How do I export?       -> support    normal [otherwise]
```
