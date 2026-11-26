# JSON Schema

A JSON Schema of the definitions lets an admin form validate input before it is saved and
gives editors completion. pyruleset builds it around the schemas of your own condition and
value languages.

## `get_ruleset_json_schema`

```python
from pyruleset import get_ruleset_json_schema

condition_schema = {"type": "string"}
value_schema = {"type": "number"}

schema = get_ruleset_json_schema(condition_schema, value_schema)

assert schema["x-kind"] == "ruleset"
assert schema["required"] == ["otherwise"]
assert schema["properties"]["otherwise"] == {"$ref": "urn:pyruleset:value"}
assert schema["$defs"]["condition"] == {"type": "string", "$id": "urn:pyruleset:condition"}
assert schema["$defs"]["value"] == {"type": "number", "$id": "urn:pyruleset:value"}
```

Each sub-schema is embedded under its own `$id` (`urn:pyruleset:condition` and
`urn:pyruleset:value`), so the `#/$defs/...` refs inside it keep pointing into itself rather
than into the ruleset schema. A sub-schema whose root is a bare `$ref` (as pyspecification's
and pyformula's are) has that `$ref` moved into `allOf`, which means the same and keeps
validators such as Ajv from overflowing their stack.

The root has `x-kind: "ruleset"`, for editors that render rulesets specially.

## Validating

pyruleset does not depend on a validator; any Draft 2020-12 validator works, e.g.
`jsonschema`:

```python
from jsonschema import Draft202012Validator

validator = Draft202012Validator(schema)

assert validator.is_valid({"branches": [{"when": "vip", "then": 80, "label": "vip"}], "otherwise": 100})
assert validator.is_valid({"otherwise": 100})
assert not validator.is_valid({"branches": []})
assert not validator.is_valid({"branches": [{"when": "vip", "then": "eighty"}], "otherwise": 100})
assert not validator.is_valid({"otherwise": 100, "default": 0})
```

With pyspecification, the condition schema is `get_expression_json_schema(rules)`; with
pyformula, the value schema is `get_formula_json_schema(variables)`. See
[With the family](family.md#json-schema).

## `get_when_json_schema`

The schema of a `{"when": <ruleset>}` node, as [`WhenCompiler`](nested.md) accepts it. Add
it to a value schema as one more shape. Its `then` and `otherwise` are `{"$ref": "#"}`: a
value of the schema it is added to.

```python
from pyruleset import get_when_json_schema

node = get_when_json_schema({"type": "boolean"})

assert node["required"] == ["when"]
assert node["properties"]["when"]["x-kind"] == "ruleset"
assert node["properties"]["when"]["properties"]["otherwise"] == {"$ref": "#"}

amounts = {"anyOf": [{"type": "number"}, node], "$defs": node.pop("$defs")}

validator = Draft202012Validator(amounts)

assert validator.is_valid(5)
assert validator.is_valid({"when": {"branches": [{"when": True, "then": 5}], "otherwise": {"when": {"otherwise": 0}}}})
assert not validator.is_valid({"when": {"branches": [{"when": "yes", "then": 5}], "otherwise": 0}})
```

pyformula accepts it directly: `get_formula_json_schema(variables, nodes=[get_when_json_schema(predicates)])`.
