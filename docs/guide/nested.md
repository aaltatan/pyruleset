# Rulesets inside values

Sometimes a ruleset is only part of a value: "the salary minus whatever discount the
ruleset decides". In JSON that is a `{"when": <ruleset>}` node where a value would go, at
any depth:

```json
{"operator": "subtract", "expressions": ["salary", {"when": {"branches": [], "otherwise": 0}}]}
```

## `WhenCompiler`

`WhenCompiler` compiles value definitions that may hold such nodes:

1. Each `{"when": ...}` node is compiled with `RulesetCompiler`.
2. It is replaced in the tree by a generated name: `__when_0`, `__when_1`, ...
3. The value compiler is built from those names, by a function you pass, and compiles the
   rewritten tree.

pyruleset still knows nothing about your value language: you decide how a name becomes a
value. With pyformula that is
`lambda names: FormulaCompiler({**variables, **names})`; see
[With the family](family.md#rulesets-inside-formulas).

Here, a tiny value language where a string is a field and a list is a sum:

```python
from pyruleset import WhenCompiler


class Field:
    def compile(self, name):
        return lambda subject: subject[name]


class Sum:
    def __init__(self, names):
        self.names = names

    def compile(self, definition):
        if isinstance(definition, list):
            parts = [self.compile(item) for item in definition]

            return lambda subject: sum(part(subject) for part in parts)

        if isinstance(definition, int):
            return lambda _: definition

        return self.names.get(definition) or (lambda subject: subject[definition])


values = WhenCompiler(Field(), Sum)

total = values.compile(
    ["price", {"when": {"branches": [{"when": "express", "then": 15, "label": "express"}], "otherwise": 0}}]
)

assert total({"price": 100, "express": True}) == 115
assert total({"price": 100, "express": False}) == 100
```

`then` and `otherwise` inside a node are compiled by the `WhenCompiler` again, so nodes
nest:

```python
nested = values.compile(
    {
        "when": {
            "branches": [
                {
                    "when": "express",
                    "then": {"when": {"branches": [{"when": "heavy", "then": 30}], "otherwise": 15}},
                }
            ],
            "otherwise": 0,
        }
    }
)

assert nested({"express": True, "heavy": True}) == 30
assert nested({"express": True, "heavy": False}) == 15
assert nested({"express": False, "heavy": True}) == 0
```

## `is_when_node`

A node is a `when` node only when `"when"` is the **only** key of its object, so a
ruleset branch (`{"when": ..., "then": ...}`) is never mistaken for one:

```python
from pyruleset import is_when_node

assert is_when_node({"when": {}})
assert not is_when_node({"when": {}, "then": 1})
assert not is_when_node(1)
```

## Naming the ruleset

`describe(ruleset)` shows each branch with the value it gives. It uses `str()` of each
value, so it reads well when values print themselves, as pyformula formulas do:

```python
from pyruleset import describe, otherwise, when


class Named:
    def __init__(self, text):
        self.text = text

    def __call__(self, subject):
        return 0

    def __str__(self):
        return self.text


ruleset = when(bool, Named("(amount * 2)"), label="big") | otherwise(Named("0"))

assert describe(ruleset) == "when(big -> (amount * 2) | otherwise -> 0)"
```

`wrap` uses it: `WhenCompiler(..., wrap=wrap)` calls `wrap(ruleset, name=describe(ruleset))`
for each node, so the value compiler gets a value that prints like the definition. With
pyformula, `wrap=Formula` makes each ruleset a `Formula`, and the whole formula prints as
`(subtotal - when(gold -> (subtotal * 0.2) | otherwise -> 0))`. Without `wrap`, the ruleset
itself is used.

```python
seen = []


def wrap(value, /, *, name):
    seen.append(name)

    return value


WhenCompiler(Field(), Sum, wrap=wrap).compile({"when": {"branches": [{"when": "vip", "then": 5, "label": "vip"}], "otherwise": 0}})

assert len(seen) == 1
assert seen[0].startswith("when(vip -> ")
```

## Errors

Errors keep their type and get the full JSON path as a note, including the path to the
node:

```python
from pyruleset import InvalidRulesetDefinitionError

try:
    values.compile(["price", {"when": {"branches": []}}])
except InvalidRulesetDefinitionError as error:
    assert str(error) == "Invalid ruleset at $: missing 'otherwise'"
    assert error.__notes__ == ["at $[1].when"]
```
