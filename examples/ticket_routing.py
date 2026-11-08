"""Route support tickets: the matching branch decides which pyflowstep flow runs.

Each value is a `Flow` (`Ticket -> Ticket`), so calling the ruleset both picks
the route and applies it.

Run with: uv run python examples/ticket_routing.py
"""

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
    print(
        f"{ticket.subject:<22} -> {routed.team:<10} {routed.priority:<6} [{route.explain(ticket)}]"
    )

assert route(Ticket("Outage in EU region", "free")) == Ticket(
    "Outage in EU region", "free", team="on-call", priority="urgent"
)
assert route(Ticket("Need SSO help", "enterprise")).tags == ("sla",)
assert route.explain(Ticket("How do I export?", "pro")) == "otherwise"
