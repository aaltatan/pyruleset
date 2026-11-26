# API

`T` is the type of the subject a ruleset is called with, `V` the type of the value it
returns.

## Building rulesets

### `when`

```py
when(condition: Condition[T], value: Value[T, V], /, *, label: str | None = None) -> PartialRuleset[T, V]
```

Start a ruleset, or one more branch to chain with `|`. `label` names the branch in
`explain` and `repr`; it defaults to the condition's name.

Raises `InvalidRulesetError` if `condition` or `value` is not callable.

Guide: [Rulesets](../guide/rulesets.md).

### `otherwise`

```py
otherwise(value: Value[T, V], /) -> Otherwise[T, V]
```

Close a ruleset with the value used when no branch matches.

Raises `InvalidRulesetError` if `value` is not callable, e.g. `otherwise(0)`; write
`otherwise(lambda _: 0)`.

### `Ruleset[T, V]`

```py
Ruleset(branches: tuple[Branch[T, V], ...], fallback: Value[T, V])
```

Branches tried in order, then a fallback. A frozen dataclass; usually built with `when`,
`|` and `otherwise`.

| Member | Description |
| --- | --- |
| `ruleset(subject) -> V` | the value of the first matching branch, else of the fallback |
| `decide(subject) -> Branch[T, V] \| Otherwise[T, V]` | the branch that decides, or `Otherwise(fallback)` |
| `explain(subject) -> str` | the deciding branch's name, or `"otherwise"` |
| `branches`, `fallback` | the attributes |
| `repr(ruleset)` | `Ruleset(gold 20% \| bulk 5% \| otherwise)` |

A `Ruleset` has no `|`: put branches in front of it with `partial | ruleset`.

Guide: [Deciding and explaining](../guide/explaining.md).

### `PartialRuleset[T, V]`

```py
PartialRuleset(branches: tuple[Branch[T, V], ...])
```

Branches without a fallback. Not callable.

| Member | Description |
| --- | --- |
| `partial \| partial` | `PartialRuleset` with both sets of branches |
| `partial \| otherwise(value)` | `Ruleset` |
| `partial \| ruleset` | `Ruleset` with the partial's branches first |
| `repr(partial)` | `PartialRuleset(gold \| bulk)` |

Guide: [Composing and overrides](../guide/composing.md).

### `Branch[T, V]`

```py
Branch(condition: Condition[T], value: Value[T, V], label: str | None = None)
```

One `when` pair. `str(branch)` is its label, else the condition's name: `str()` of the
condition when it defines `__str__` (as pyspecification predicates do), else its
`__name__`.

### `Otherwise[T, V]`

```py
Otherwise(value: Value[T, V])
```

The fallback. `otherwise()` returns one, and `decide` returns one when no branch matches.

### `FALLBACK_LABEL`

```py
FALLBACK_LABEL = "otherwise"
```

What `explain` returns, and `repr` shows, for the fallback.

### `Condition[T]`, `Value[T, V]`

```py
type Condition[T] = Callable[[T], Any]
type Value[T, V] = Callable[[T], V]
```

A condition matches when its result is truthy.

## Compiling from JSON

### `RulesetCompiler[T, V]`

```py
RulesetCompiler(conditions: Compiler[Condition[T]], values: Compiler[Value[T, V]], /)
```

| Member | Description |
| --- | --- |
| `compile(definition: RulesetDict \| Mapping[str, Any], /) -> Ruleset[T, V]` | compile a [definition](definition-format.md) |

`conditions` compiles each branch's `when`, `values` each `then` and the `otherwise`.

Raises `InvalidRulesetDefinitionError` for a wrong shape. Errors from the injected
compilers keep their type and get a note `at <JSON path>`.

Guide: [Compiling from JSON](../guide/compiling.md).

### `Compiler[F]`

```py
class Compiler[F](Protocol):
    def compile(self, definition: Any, /) -> F: ...
```

Anything with a `compile` method, e.g. pyspecification's `PredicateCompiler` or pyformula's
`FormulaCompiler`.

### `RulesetDict`, `BranchDict`

```py
class BranchDict(TypedDict):
    when: Any
    then: Any
    label: NotRequired[str | None]


class RulesetDict(TypedDict):
    branches: list[BranchDict]
    otherwise: Any
```

The JSON shape, for type hints. At run time `branches` may be left out.

## Rulesets inside values

### `WhenCompiler[T, V]`

```py
WhenCompiler(
    conditions: Compiler[Condition[T]],
    values: Callable[[Mapping[str, Value[T, V]]], Compiler[Value[T, V]]],
    /,
    *,
    wrap: Wrap[T, V] | None = None,
)
```

| Member | Description |
| --- | --- |
| `compile(definition: Any, /) -> Value[T, V]` | compile a value definition, replacing each `{"when": <ruleset>}` node |

- `conditions` compiles each branch's `when`.
- `values` builds the value compiler from the generated names (`__when_0`, ...), each
  standing for one compiled node, e.g. `lambda names: FormulaCompiler({**variables, **names})`.
- `wrap` turns each compiled ruleset into a value, called as
  `wrap(ruleset, name=describe(ruleset))`, e.g. pyformula's `Formula`. Defaults to the
  ruleset itself.

`then` and `otherwise` inside a node are compiled by the same `WhenCompiler`, so nodes nest.

Raises `InvalidRulesetDefinitionError` if a node is not a ruleset.

Guide: [Rulesets inside values](../guide/nested.md).

### `Wrap[T, V]`

```py
class Wrap[T, V](Protocol):
    def __call__(self, value: Value[T, V], /, *, name: str) -> Value[T, V]: ...
```

### `is_when_node`

```py
is_when_node(node: object, /) -> bool
```

Whether `node` is a mapping whose only key is `"when"`.

### `describe`

```py
describe(ruleset: Ruleset[Any, Any], /) -> str
```

Each branch with the `str()` of its value, e.g.
`when(gold -> (subtotal * 0.2) | otherwise -> 0)`.

## JSON Schema

### `get_ruleset_json_schema`

```py
get_ruleset_json_schema(condition_schema: Mapping[str, Any], value_schema: Mapping[str, Any], /) -> dict[str, Any]
```

The JSON Schema (Draft 2020-12) of a ruleset definition. The two schemas describe one
`when` and one `then`/`otherwise`; they are embedded in `$defs` under the `$id`s
`urn:pyruleset:condition` and `urn:pyruleset:value`. The root has `x-kind: "ruleset"`.

### `get_when_json_schema`

```py
get_when_json_schema(condition_schema: Mapping[str, Any], /) -> dict[str, Any]
```

The JSON Schema of a `{"when": <ruleset>}` node, to add to a value schema. `then` and
`otherwise` are `{"$ref": "#"}`. The condition schema is embedded under
`urn:pyruleset:when-condition`.

Guide: [JSON Schema](../guide/json-schema.md).

## Exceptions

`PyrulesetError`, `InvalidRulesetDefinitionError`, `InvalidRulesetError`: see
[Exceptions](exceptions.md).
