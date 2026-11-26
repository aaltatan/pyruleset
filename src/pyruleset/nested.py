"""Rulesets inside values: a `{"when": <ruleset>}` node anywhere in a value definition.

A formula like "salary minus the discount the ruleset decides" holds a ruleset
where a number would go:

```json
{"operator": "subtract", "expressions": ["salary", {"when": {"branches": [...], "otherwise": 0}}]}
```

`WhenCompiler` compiles each `when` node with `RulesetCompiler`, gives it a
generated name (`__when_0`), and hands the value compiler the tree with the name in
its place. pyruleset still knows nothing about formulas: the value compiler is
built by a function you pass, e.g. one that makes a pyformula `FormulaCompiler`.
"""

from collections.abc import Callable, Mapping
from typing import Any, Protocol, cast

from pyvocabulary import index_path, key_path, located

from .compilers import Compiler, RulesetCompiler
from .ruleset import FALLBACK_LABEL, Condition, Ruleset, Value


class Wrap[T, V](Protocol):
    """Turns a compiled ruleset into a value the value compiler accepts, e.g. pyformula's `Formula`."""  # noqa: E501

    def __call__(self, value: Value[T, V], /, *, name: str) -> Value[T, V]: ...


class WhenCompiler[T, V]:
    """Compile value definitions that may hold `{"when": <ruleset>}` nodes at any depth.

    Args:
        conditions: Compiles each branch's `when`, e.g. pyspecification's `PredicateCompiler`.
        values: Builds the value compiler from the generated names, each standing for
            one `when` node, e.g. `lambda names: FormulaCompiler({**variables, **names})`.
        wrap: Turns each compiled ruleset into a value, called as `wrap(ruleset, name=...)`
            with a name that shows its branches, e.g. `Formula`. Defaults to the ruleset itself.

    `then` and `otherwise` inside a `when` node are compiled by this compiler again,
    so nodes nest. Errors keep their type and get the full JSON path as a note.

    Example:
    ```python
    >>> class Field:
    ...     def __init__(self, names):
    ...         self.names = names
    ...     def compile(self, name):
    ...         return self.names.get(name) or (lambda subject: subject[name])
    >>> compiler = WhenCompiler(Field({}), Field)
    >>> price = compiler.compile(
    ...     {"when": {"branches": [{"when": "vip", "then": "vip_price"}], "otherwise": "price"}}
    ... )
    >>> price({"vip": False, "vip_price": 80, "price": 100})
    100

    ```

    """

    __slots__ = ("_conditions", "_values", "_wrap")

    def __init__(
        self,
        conditions: Compiler[Condition[T]],
        values: Callable[[Mapping[str, Value[T, V]]], Compiler[Value[T, V]]],
        /,
        *,
        wrap: Wrap[T, V] | None = None,
    ) -> None:
        self._conditions = conditions
        self._values = values
        self._wrap: Wrap[T, V] = wrap or _unwrapped

    def compile(self, definition: Any, /) -> Value[T, V]:
        """Compile `definition`, replacing each `when` node by a compiled ruleset.

        Raises:
            InvalidRulesetDefinitionError: If a `when` node is not a ruleset.

        """
        names: dict[str, Value[T, V]] = {}
        lifted = self._lift(definition, names, "$")

        return self._values(names).compile(lifted)

    def _lift(self, node: Any, names: dict[str, Value[T, V]], path: str) -> Any:
        if is_when_node(node):
            with located(key_path(path, "when"), Exception):
                ruleset = RulesetCompiler(self._conditions, self).compile(node["when"])

            name = f"__when_{len(names)}"
            names[name] = self._wrap(ruleset, name=describe(ruleset))

            return name

        if isinstance(node, Mapping):
            items = cast("Mapping[str, Any]", node).items()

            return {key: self._lift(value, names, key_path(path, key)) for key, value in items}

        if isinstance(node, list):
            items = cast("list[Any]", node)

            return [self._lift(item, names, index_path(path, i)) for i, item in enumerate(items)]

        return node


def is_when_node(node: object, /) -> bool:
    """Whether `node` is a `{"when": ...}` node, the only key of its object.

    Example:
    ```python
    >>> is_when_node({"when": {}}), is_when_node({"when": {}, "then": 1}), is_when_node(1)
    (True, False, False)

    ```

    """
    return isinstance(node, Mapping) and list(cast("Mapping[str, Any]", node)) == ["when"]


def describe(ruleset: Ruleset[Any, Any], /) -> str:
    """Show each branch with the value it gives, e.g. for a formula's trace.

    Example:
    ```python
    >>> from pyruleset import otherwise, when
    >>> class Value:
    ...     def __init__(self, text):
    ...         self.text = text
    ...     def __call__(self, subject):
    ...         return 0
    ...     def __str__(self):
    ...         return self.text
    >>> describe(when(bool, Value("(amount * 2)"), label="big") | otherwise(Value("0")))
    'when(big -> (amount * 2) | otherwise -> 0)'

    ```

    """
    branches = [f"{branch} -> {branch.value}" for branch in ruleset.branches]

    return f"when({' | '.join([*branches, f'{FALLBACK_LABEL} -> {ruleset.fallback}'])})"


def _unwrapped[T, V](value: Value[T, V], /, *, name: str) -> Value[T, V]:  # noqa: ARG001
    return value
