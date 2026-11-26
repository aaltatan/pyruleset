"""The JSON Schema of a ruleset definition, as accepted by `RulesetCompiler.compile`.

pyruleset does not know the languages inside `when` and `then`, so their schemas
are passed in, e.g. pyspecification's `get_expression_json_schema(rules)`.
"""

from collections.abc import Mapping
from typing import Any

from pyvocabulary import JSON_SCHEMA_DIALECT

CONDITION_SCHEMA_ID = "urn:pyruleset:condition"
VALUE_SCHEMA_ID = "urn:pyruleset:value"
WHEN_CONDITION_SCHEMA_ID = "urn:pyruleset:when-condition"


def get_ruleset_json_schema(
    condition_schema: Mapping[str, Any],
    value_schema: Mapping[str, Any],
    /,
) -> dict[str, Any]:
    """Return the JSON Schema of `{"branches": [{"when", "then", "label"}], "otherwise"}`.

    Each sub-schema is embedded under its own `$id`, so the `#/$defs/...` refs it
    uses internally keep pointing into itself rather than into the ruleset schema.
    The root has `x-kind: "ruleset"`.

    Args:
        condition_schema: The schema of one `when`, e.g. a pyspecification expression.
        value_schema: The schema of one `then` and of `otherwise`.

    Example:
    ```python
    >>> schema = get_ruleset_json_schema({"type": "string"}, {"type": "number"})
    >>> schema["x-kind"], schema["required"], schema["properties"]["otherwise"]
    ('ruleset', ['otherwise'], {'$ref': 'urn:pyruleset:value'})
    >>> schema["$defs"]["value"]
    {'type': 'number', '$id': 'urn:pyruleset:value'}

    ```

    """
    return {
        "$schema": JSON_SCHEMA_DIALECT,
        **_ruleset({"$ref": CONDITION_SCHEMA_ID}, {"$ref": VALUE_SCHEMA_ID}),
        "$defs": {
            "condition": {**condition_schema, "$id": CONDITION_SCHEMA_ID},
            "value": {**value_schema, "$id": VALUE_SCHEMA_ID},
        },
    }


def get_when_json_schema(condition_schema: Mapping[str, Any], /) -> dict[str, Any]:
    """Return the JSON Schema of a `{"when": <ruleset>}` node, as `WhenCompiler` accepts it.

    Add it to a value schema as one more shape, e.g. pyformula's
    `get_formula_json_schema(variables, nodes=[get_when_json_schema(predicates)])`.
    Its `then` and `otherwise` are `{"$ref": "#"}`: a value of the schema it is added to.
    The ruleset inside has `x-kind: "ruleset"`.

    Example:
    ```python
    >>> node = get_when_json_schema({"type": "boolean"})
    >>> node["required"], node["properties"]["when"]["x-kind"]
    (['when'], 'ruleset')
    >>> node["properties"]["when"]["properties"]["otherwise"]
    {'$ref': '#'}

    ```

    """
    return {
        "type": "object",
        "properties": {"when": _ruleset({"$ref": WHEN_CONDITION_SCHEMA_ID}, {"$ref": "#"})},
        "required": ["when"],
        "additionalProperties": False,
        "$defs": {"when-condition": {**condition_schema, "$id": WHEN_CONDITION_SCHEMA_ID}},
    }


def _ruleset(condition: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    branch = {
        "type": "object",
        "properties": {"when": condition, "then": value, "label": {"type": "string"}},
        "required": ["when", "then"],
        "additionalProperties": False,
    }
    return {
        "x-kind": "ruleset",
        "type": "object",
        "properties": {"branches": {"type": "array", "items": branch}, "otherwise": value},
        "required": ["otherwise"],
        "additionalProperties": False,
    }
