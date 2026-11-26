# Exceptions

```text
Exception
└── PyrulesetError
    ├── InvalidRulesetDefinitionError (also ValueError)
    └── InvalidRulesetError           (also TypeError)
```

| Exception | Raised by | When |
| --- | --- | --- |
| `PyrulesetError` | — | base class; catch it to catch every pyruleset error |
| `InvalidRulesetDefinitionError` | `RulesetCompiler.compile`, `WhenCompiler.compile` | a definition has the wrong shape |
| `InvalidRulesetError` | `when`, `otherwise` | a condition or value is not callable |

```python
from pyruleset import (
    InvalidRulesetDefinitionError,
    InvalidRulesetError,
    PyrulesetError,
    RulesetCompiler,
    otherwise,
    when,
)

try:
    when(lambda n: n > 0, "positive")
except InvalidRulesetError as error:
    assert isinstance(error, (PyrulesetError, TypeError))
    assert str(error) == "The value of when() must be callable, received 'positive'. Wrap a constant: lambda _: 'positive'"


class Field:
    def compile(self, name):
        return lambda subject: subject[name]


try:
    RulesetCompiler(Field(), Field()).compile({"branches": [1], "otherwise": "price"})
except InvalidRulesetDefinitionError as error:
    assert isinstance(error, (PyrulesetError, ValueError))
    assert str(error) == "Invalid ruleset at $.branches[0]: expected an object, received 1"
```

## Errors from injected compilers

pyruleset does not wrap them. An error raised by your condition or value compiler (for
example pyspecification's `RuleDoesNotExistError`) keeps its type, and pyruleset adds one
note with the full JSON path, read from `error.__notes__`:

```python
class Strict:
    def compile(self, name):
        if name != "price":
            msg = f"Unknown field {name!r}"
            raise KeyError(msg)

        return lambda subject: subject[name]


try:
    RulesetCompiler(Strict(), Strict()).compile({"branches": [{"when": "vip", "then": "price"}], "otherwise": "price"})
except KeyError as error:
    assert error.__notes__ == ["at $.branches[0].when"]
```

Calling a ruleset raises whatever its conditions and values raise, unchanged.
