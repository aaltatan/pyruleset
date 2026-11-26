# Composing and overrides

Policies change: a campaign this month, a stand-in while someone is on leave. pyruleset
handles that by putting new branches **in front of** an unchanged base policy.

## What `|` accepts

| Left | Right | Result |
| --- | --- | --- |
| `PartialRuleset` | `PartialRuleset` | `PartialRuleset` with both sets of branches |
| `PartialRuleset` | `otherwise(value)` | `Ruleset` |
| `PartialRuleset` | `Ruleset` | `Ruleset`: the partial's branches first, then the ruleset's, with its fallback |
| `Ruleset` | anything | not supported: a ruleset is closed |

## Overrides on top of a base policy

```python
from pyruleset import otherwise, when

approver = (
    when(lambda amount: amount >= 10_000, lambda _: "CFO", label="large")
    | when(lambda amount: amount >= 500, lambda _: "manager", label="medium")
    | otherwise(lambda _: "auto-approved")
)

cfo_on_leave = when(lambda amount: amount >= 10_000, lambda _: "CEO", label="CFO on leave")

this_month = cfo_on_leave | approver

assert repr(this_month) == "Ruleset(CFO on leave | large | medium | otherwise)"
assert (approver(25_000), this_month(25_000)) == ("CFO", "CEO")
assert this_month(800) == "manager"
```

`approver` is unchanged: every operator returns a new object. When the override ends, use
`approver` again.

## Building a ruleset from parts

Partial rulesets compose with each other, so branches can be grouped by topic and joined
later:

```python
fraud = when(lambda amount: amount < 0, lambda _: "fraud team", label="negative")
large = when(lambda amount: amount >= 10_000, lambda _: "CFO", label="large")

policy = fraud | large | otherwise(lambda _: "manager")

assert repr(policy) == "Ruleset(negative | large | otherwise)"
assert policy(-5) == "fraud team"
```

## First match only

A ruleset picks exactly one value. There is no "all matches" mode, on purpose: each ruleset
stays easy to read and to explain. To stack several decisions, give each part its own
ruleset and combine the results in a plain function:

```python
from decimal import Decimal

discount = when(lambda items: items >= 10, lambda _: Decimal("5.00"), label="bulk") | otherwise(lambda _: Decimal("0"))
shipping = when(lambda items: items >= 10, lambda _: Decimal("0.00"), label="free shipping") | otherwise(lambda _: Decimal("5.00"))


def extras(items: int) -> Decimal:
    return shipping(items) - discount(items)


assert extras(12) == Decimal("-5.00")
assert [discount.explain(1), shipping.explain(1)] == ["otherwise", "otherwise"]
```

Progressive brackets, such as tax bands, are not a ruleset either: they are a sum of
clamped terms, one per band.
