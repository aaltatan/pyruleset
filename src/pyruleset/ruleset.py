"""Conditional values: the first branch whose condition matches decides.

```python
price = (
    when(is_gold(), subtotal * Decimal("0.80"), label="gold 20%")
    | when(items__ge(10), subtotal * Decimal("0.95"), label="bulk 5%")
    | otherwise(subtotal)
)
```

A chain without `otherwise` is a `PartialRuleset`: it composes, but it has no
`__call__`, so a missing fallback is a type error instead of a `None` at run time.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, overload

type Condition[T] = Callable[[T], Any]
type Value[T, V] = Callable[[T], V]

FALLBACK_LABEL = "otherwise"


@dataclass(frozen=True, slots=True)
class Branch[T, V]:
    """One `when(condition, value)` pair, optionally labelled for `explain` and `repr`."""

    condition: Condition[T]
    value: Value[T, V]
    label: str | None = None

    def __str__(self) -> str:
        return self.label or _name_of(self.condition)


@dataclass(frozen=True, slots=True)
class Otherwise[T, V]:
    """The fallback that closes a ruleset. Build it with `otherwise(value)`."""

    value: Value[T, V]


@dataclass(frozen=True, slots=True)
class Ruleset[T, V]:
    """Branches tried in order, then a fallback. Calling it returns the decided value.

    Example:
    ```python
    >>> sign = (
    ...     when(lambda n: n < 0, lambda _: "negative", label="below zero")
    ...     | when(lambda n: n == 0, lambda _: "zero", label="zero")
    ...     | otherwise(lambda _: "positive")
    ... )
    >>> sign
    Ruleset(below zero | zero | otherwise)
    >>> [sign(n) for n in (-2, 0, 5)]
    ['negative', 'zero', 'positive']
    >>> sign.explain(-2), sign.explain(5)
    ('below zero', 'otherwise')

    ```

    """

    branches: tuple[Branch[T, V], ...]
    fallback: Value[T, V]

    def __call__(self, subject: T, /) -> V:
        return self.decide(subject).value(subject)

    def decide(self, subject: T, /) -> "Branch[T, V] | Otherwise[T, V]":
        """Return the branch that decides for `subject`, or the fallback."""
        return next(
            (branch for branch in self.branches if branch.condition(subject)),
            Otherwise(self.fallback),
        )

    def explain(self, subject: T, /) -> str:
        """Name the branch that decides for `subject`, e.g. for an audit log."""
        match self.decide(subject):
            case Branch() as branch:
                return str(branch)
            case _:
                return FALLBACK_LABEL

    def __repr__(self) -> str:
        return f"Ruleset({' | '.join([*map(str, self.branches), FALLBACK_LABEL])})"


@dataclass(frozen=True, slots=True)
class PartialRuleset[T, V]:
    """Branches without a fallback. It composes with `|`, but it cannot be called.

    Example:
    ```python
    >>> overrides = when(lambda n: n == 13, lambda _: "unlucky", label="13")
    >>> overrides
    PartialRuleset(13)
    >>> callable(overrides)
    False
    >>> base = when(lambda n: n % 2 == 0, lambda _: "even", label="even") | otherwise(
    ...     lambda _: "odd"
    ... )
    >>> combined = overrides | base
    >>> combined, combined(13), combined(4)
    (Ruleset(13 | even | otherwise), 'unlucky', 'even')

    ```

    """

    branches: tuple[Branch[T, V], ...]

    @overload
    def __or__(self, other: "PartialRuleset[T, V]", /) -> "PartialRuleset[T, V]": ...
    @overload
    def __or__(self, other: Otherwise[T, V] | Ruleset[T, V], /) -> Ruleset[T, V]: ...
    def __or__(
        self,
        other: "PartialRuleset[T, V] | Otherwise[T, V] | Ruleset[T, V]",
        /,
    ) -> "PartialRuleset[T, V] | Ruleset[T, V]":
        match other:
            case PartialRuleset(branches=branches):
                return PartialRuleset((*self.branches, *branches))
            case Otherwise(value=value):
                return Ruleset(self.branches, value)
            case Ruleset(branches=branches, fallback=fallback):
                return Ruleset((*self.branches, *branches), fallback)
            case _:
                return NotImplemented

    def __repr__(self) -> str:
        return f"PartialRuleset({' | '.join(map(str, self.branches))})"


def when[T, V](
    condition: Condition[T],
    value: Value[T, V],
    /,
    *,
    label: str | None = None,
) -> PartialRuleset[T, V]:
    """Start a ruleset, or one more branch to chain with `|`.

    Args:
        condition: Decides whether this branch applies, e.g. a pyspecification `Predicate`.
        value: Computes the result, e.g. a pyformula `Formula` or a pyflowstep `Flow`.
        label: Names the branch in `explain` and `repr`. Defaults to the condition's name.

    """
    return PartialRuleset((Branch(condition, value, label),))


def otherwise[T, V](value: Value[T, V], /) -> Otherwise[T, V]:
    """Close a ruleset with the value used when no branch matches.

    Example:
    ```python
    >>> (when(bool, str.upper) | otherwise(str.lower))("Hi")
    'HI'

    ```

    """
    return Otherwise(value)


def _name_of(function: Callable[..., Any]) -> str:
    # Predicates and formulas print their own name; plain functions use `__name__`.
    if type(function).__str__ is not object.__str__:
        return str(function)
    return getattr(function, "__name__", repr(function))
