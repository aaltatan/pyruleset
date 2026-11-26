# Definition format

The JSON shape `RulesetCompiler.compile` accepts, and that `get_ruleset_json_schema`
describes.

## Ruleset

```json
{
  "branches": [<branch>, ...],
  "otherwise": <value>
}
```

| Key | Required | Type | Meaning |
| --- | --- | --- | --- |
| `branches` | no (default `[]`) | array of branches | tried in order |
| `otherwise` | yes | a value definition | used when no branch matches |

No other key is allowed.

## Branch

```json
{"when": <condition>, "then": <value>, "label": "optional name"}
```

| Key | Required | Type | Meaning |
| --- | --- | --- | --- |
| `when` | yes | a condition definition | passed to the condition compiler |
| `then` | yes | a value definition | passed to the value compiler |
| `label` | no | string or `null` | the branch's name in `explain` and `repr` |

No other key is allowed.

## Conditions and values

pyruleset does not read them: each `when` goes to the condition compiler, each `then` and
the `otherwise` to the value compiler. With pyspecification and pyformula:

```json
{
  "branches": [
    {"label": "gold 20%",
     "when": {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": false},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.80]}}
  ],
  "otherwise": "subtotal"
}
```

## `when` nodes

With `WhenCompiler`, any value definition may contain, at any depth, a node whose only key
is `when` and whose content is a ruleset:

```json
{"operator": "subtract", "expressions": ["subtotal", {"when": {"branches": [], "otherwise": 0}}]}
```

Its `then` and `otherwise` may hold `when` nodes again.

## Error messages

Shape errors raise `InvalidRulesetDefinitionError` with the JSON path:

| Problem | Message |
| --- | --- |
| not an object | `Invalid ruleset at $.branches[0]: expected an object, received 1` |
| missing key | `Invalid ruleset at $: missing 'otherwise'` |
| unknown key | `Invalid ruleset at $: unknown 'default'. Allowed keys: branches, otherwise` |
| `branches` not a list | `Invalid ruleset at $.branches: expected a list, received {}` |
| `label` not a string | `Invalid branch at $.branches[0].label: expected a string, received 1` |

Errors from the injected compilers keep their own type and get a note with the JSON path,
such as `at $.branches[1].when`.
