# Reference

- [API](api.md): every public name of `pyruleset`.
- [Definition format](definition-format.md): the JSON shape `RulesetCompiler` and
  `WhenCompiler` accept.
- [Exceptions](exceptions.md): the exception hierarchy and when each one is raised.

Everything is importable from the package root:

```python
import pyruleset

assert sorted(pyruleset.__all__) == [
    "Branch",
    "BranchDict",
    "Compiler",
    "Condition",
    "FALLBACK_LABEL",
    "InvalidRulesetDefinitionError",
    "InvalidRulesetError",
    "Otherwise",
    "PartialRuleset",
    "PyrulesetError",
    "Ruleset",
    "RulesetCompiler",
    "RulesetDict",
    "Value",
    "WhenCompiler",
    "Wrap",
    "describe",
    "get_ruleset_json_schema",
    "get_when_json_schema",
    "is_when_node",
    "otherwise",
    "when",
]
```
