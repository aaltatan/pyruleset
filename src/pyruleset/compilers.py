"""Compile a ruleset from JSON: `{"branches": [{"when": ..., "then": ...}], "otherwise": ...}`.

pyruleset does not know the expression languages inside `when` and `then`. Both
are delegated to injected compilers, e.g. pyspecification's `PredicateCompiler`
for conditions and pyformula's `FormulaCompiler` for values.
"""

from collections.abc import Mapping
from typing import Any, NotRequired, Protocol, TypedDict

from pyvocabulary import index_path, key_path, located

from .exceptions import InvalidRulesetDefinitionError
from .ruleset import Branch, Condition, Ruleset, Value

_BRANCH_KEYS = {"when", "then", "label"}
_RULESET_KEYS = {"branches", "otherwise"}


class BranchDict(TypedDict):
    when: Any
    then: Any
    label: NotRequired[str]


class RulesetDict(TypedDict):
    branches: list[BranchDict]
    otherwise: Any


class Compiler[F](Protocol):
    """Anything with a `compile(definition) -> F` method."""

    def compile(self, definition: Any, /) -> F: ...


class RulesetCompiler[T, V]:
    """Compile ruleset definitions, delegating `when` and `then` to injected compilers.

    Every problem is reported here, before any subject is evaluated. Errors from
    the injected compilers keep their type and get a note with the full JSON path.

    Example:
    ```python
    >>> class Field:
    ...     def compile(self, name):
    ...         return lambda subject: subject[name]
    >>> compiler = RulesetCompiler(Field(), Field())
    >>> ruleset = compiler.compile({
    ...     "branches": [{"when": "vip", "then": "vip_price", "label": "vip"}],
    ...     "otherwise": "price",
    ... })
    >>> ruleset
    Ruleset(vip | otherwise)
    >>> ruleset({"vip": True, "vip_price": 80, "price": 100})
    80

    ```

    """

    __slots__ = ("_conditions", "_values")

    def __init__(
        self, conditions: Compiler[Condition[T]], values: Compiler[Value[T, V]], /
    ) -> None:
        self._conditions = conditions
        self._values = values

    def compile(self, definition: RulesetDict | Mapping[str, Any], /) -> Ruleset[T, V]:
        """Compile `definition` into a `Ruleset`.

        Raises:
            InvalidRulesetDefinitionError: If the definition has the wrong shape.

        """
        _check_keys(definition, required={"otherwise"}, allowed=_RULESET_KEYS, path="$")
        branches = definition.get("branches", [])
        if not isinstance(branches, list):
            msg = f"Invalid ruleset at $.branches: expected a list, received {branches!r}"
            raise InvalidRulesetDefinitionError(msg)

        path = key_path("$", "branches")
        compiled = tuple(
            self._compile_branch(branch, index_path(path, index))
            for index, branch in enumerate(branches)
        )
        with located(key_path("$", "otherwise"), Exception):
            fallback = self._values.compile(definition["otherwise"])

        return Ruleset(compiled, fallback)

    def _compile_branch(self, branch: Any, path: str) -> Branch[T, V]:
        _check_keys(branch, required={"when", "then"}, allowed=_BRANCH_KEYS, path=path)

        label = branch.get("label")
        if label is not None and not isinstance(label, str):
            msg = f"Invalid branch at {path}.label: expected a string, received {label!r}"
            raise InvalidRulesetDefinitionError(msg)

        with located(key_path(path, "when"), Exception):
            condition = self._conditions.compile(branch["when"])
        with located(key_path(path, "then"), Exception):
            value = self._values.compile(branch["then"])

        return Branch(condition, value, label)


def _check_keys(item: Any, *, required: set[str], allowed: set[str], path: str) -> None:
    if not isinstance(item, Mapping):
        msg = f"Invalid ruleset at {path}: expected an object, received {item!r}"
        raise InvalidRulesetDefinitionError(msg)

    if missing := sorted(required - item.keys()):
        msg = f"Invalid ruleset at {path}: missing {', '.join(map(repr, missing))}"
        raise InvalidRulesetDefinitionError(msg)

    if unknown := sorted(item.keys() - allowed):
        msg = (
            f"Invalid ruleset at {path}: unknown {', '.join(map(repr, unknown))}. "
            f"Allowed keys: {', '.join(sorted(allowed))}"
        )
        raise InvalidRulesetDefinitionError(msg)
