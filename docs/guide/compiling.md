# Compiling from JSON

A policy that admins edit lives in a database as JSON. `RulesetCompiler` turns that JSON
into a `Ruleset`.

## The shape

```json
{
  "branches": [
    {"when": "<condition>", "then": "<value>", "label": "optional name"}
  ],
  "otherwise": "<value>"
}
```

`branches` is optional, `otherwise` is required. The full format is in the
[Definition format](../reference/definition-format.md) reference.

## Injected compilers

pyruleset does not know the languages inside `when` and `then`. It delegates them to two
compilers you pass in: anything with a `compile(definition)` method (the `Compiler`
protocol). In real projects those are pyspecification's `PredicateCompiler` and pyformula's
`FormulaCompiler` ([With the family](family.md)); here are two tiny ones:

```python
from pyruleset import RulesetCompiler


class Field:
    """Compile a field name into a function that reads it."""

    def compile(self, name):
        if not isinstance(name, str):
            msg = f"expected a field name, received {name!r}"
            raise TypeError(msg)

        return lambda subject: subject[name]


compiler = RulesetCompiler(Field(), Field())

price = compiler.compile(
    {
        "branches": [{"when": "vip", "then": "vip_price", "label": "vip"}],
        "otherwise": "price",
    }
)

assert repr(price) == "Ruleset(vip | otherwise)"
assert price({"vip": True, "vip_price": 80, "price": 100}) == 80
assert price({"vip": False, "vip_price": 80, "price": 100}) == 100
```

The first argument compiles conditions, the second compiles values (`then` and
`otherwise`).

## Errors are reported on compile

The whole definition is checked when it is compiled, before any subject is evaluated. So a
typo is rejected when the admin saves, not when a customer checks out.

A wrong shape raises `InvalidRulesetDefinitionError` (also a `ValueError`) with its JSON
path:

```python
from pyruleset import InvalidRulesetDefinitionError


def error_of(definition) -> str:
    try:
        compiler.compile(definition)
    except InvalidRulesetDefinitionError as error:
        return str(error)

    raise AssertionError


assert error_of({"branches": []}) == "Invalid ruleset at $: missing 'otherwise'"
assert error_of({"branches": {}, "otherwise": "price"}) == "Invalid ruleset at $.branches: expected a list, received {}"
assert error_of({"branches": [{"when": "vip"}], "otherwise": "price"}) == "Invalid ruleset at $.branches[0]: missing 'then'"
assert error_of({"branches": [{"when": "vip", "then": "x", "label": 1}], "otherwise": "price"}) == (
    "Invalid branch at $.branches[0].label: expected a string, received 1"
)
assert error_of({"otherwise": "price", "default": 0}) == (
    "Invalid ruleset at $: unknown 'default'. Allowed keys: branches, otherwise"
)
```

Errors raised by your compilers keep their own type. pyruleset only adds a note with the
full JSON path:

```python
try:
    compiler.compile({"branches": [{"when": "vip", "then": 80}], "otherwise": "price"})
except TypeError as error:
    assert str(error) == "expected a field name, received 80"
    assert error.__notes__ == ["at $.branches[0].then"]
```

With pyspecification or pyformula as the inner compilers, the note carries their nested
path too, e.g. `at $.branches[1].when.expressions[0]`.

## Money

`json.loads` turns `0.80` into a binary float, which then leaks into every `Decimal` it
touches. Keep money exact in one of two ways:

- Parse with `json.loads(text, parse_float=Decimal)`, so every JSON number with a decimal
  point is a `Decimal` before it reaches the compiler.
- Or, with pyformula, build the value compiler with
  `FormulaCompiler(variables, literal=decimal_literal)`, which converts each number literal
  through `str`, whoever parsed the JSON.

```python
import json
from decimal import Decimal

assert json.loads('{"rate": 0.80}', parse_float=Decimal) == {"rate": Decimal("0.80")}
```
