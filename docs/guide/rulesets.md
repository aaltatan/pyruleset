# Rulesets

A ruleset is an `if`/`elif`/`else` chain written as data: branches tried in order, and a
fallback for when none matches.

## Branches and the fallback

`when(condition, value, label=...)` makes a branch. `otherwise(value)` makes the fallback.
Chain them with `|`:

```python
from pyruleset import Ruleset, otherwise, when

grade = (
    when(lambda score: score >= 90, lambda _: "A", label="excellent")
    | when(lambda score: score >= 75, lambda _: "B", label="good")
    | when(lambda score: score >= 50, lambda _: "C", label="pass")
    | otherwise(lambda _: "F")
)

assert isinstance(grade, Ruleset)
assert [grade(score) for score in (95, 80, 50, 10)] == ["A", "B", "C", "F"]
```

The first branch whose condition matches decides. Conditions after it are not evaluated,
and exactly one value is computed:

```python
calls = []


def track(name, result):
    def condition(_):
        calls.append(name)

        return result

    return condition


first = when(track("a", False), str) | when(track("b", True), str) | when(track("c", True), str) | otherwise(str)

first(1)

assert calls == ["a", "b"]
```

## Conditions

A condition is any callable that takes the subject. Its result only needs to be truthy, so
`len`, `bool` or a pyspecification `Predicate` all work:

```python
size = when(len, lambda items: f"{len(items)} items") | otherwise(lambda _: "empty")

assert (size([1, 2]), size([])) == ("2 items", "empty")
```

## Values are callables

Values are called with the subject too, so a branch can compute its result from it. A
constant must be wrapped, otherwise the ruleset fails when it is built, not when a rare
branch is first reached:

```python
from pyruleset import InvalidRulesetError

try:
    otherwise(0)
except InvalidRulesetError as error:
    assert str(error) == "The value of otherwise() must be callable, received 0. Wrap a constant: lambda _: 0"

zero = otherwise(lambda _: 0)
```

`when` checks both its condition and its value the same way.

## A missing fallback is a type error

A chain without `otherwise` is a `PartialRuleset`. It composes, but it has no `__call__`:
a type checker flags the call, and at run time it raises instead of returning `None`.

```python
from pyruleset import PartialRuleset

partial = when(lambda n: n > 0, lambda _: "positive", label="positive")

assert isinstance(partial, PartialRuleset)
assert repr(partial) == "PartialRuleset(positive)"
assert not callable(partial)

try:
    partial(5)
except TypeError as error:
    assert "not callable" in str(error)
```

A `Ruleset` is closed the other way: it has no `|`, so nothing can be added after its
fallback by accident. To put branches in front of it, see
[Composing and overrides](composing.md).

## Labels and `repr`

A branch shows as its label, else as its condition's name (a pyspecification predicate
prints itself, a function uses `__name__`). The fallback is always `otherwise`:

```python
def is_negative(n: int) -> bool:
    return n < 0


sign = when(is_negative, lambda _: -1) | when(lambda n: n == 0, lambda _: 0, label="zero") | otherwise(lambda _: 1)

assert repr(sign) == "Ruleset(is_negative | zero | otherwise)"
```

Give lambdas a label: unlabelled, they show as `<lambda>`.
