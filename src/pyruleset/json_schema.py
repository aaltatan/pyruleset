"""The JSON Schema of a ruleset definition, as accepted by `RulesetCompiler.compile`.

pyruleset does not know the languages inside `when` and `then`, so their schemas
are passed in, e.g. pyspecification's `get_expression_json_schema(rules)`.
"""

from collections.abc import Mapping
from typing import Any

from pyvocabulary import JSON_SCHEMA_DIALECT

CONDITION_SCHEMA_ID = "urn:pyruleset:condition"
VALUE_SCHEMA_ID = "urn:pyruleset:value"


def get_ruleset_json_schema(
    condition_schema: Mapping[str, Any],
    value_schema: Mapping[str, Any],
    /,
) -> dict[str, Any]:
    """Return the JSON Schema of `{"branches": [{"when", "then", "label"}], "otherwise"}`.

    Each sub-schema is embedded under its own `$id`, so the `#/$defs/...` refs it
    uses internally keep pointing into itself rather than into the ruleset schema.

    Args:
        condition_schema: The schema of one `when`, e.g. a pyspecification expression.
        value_schema: The schema of one `then` and of `otherwise`.

    Example:
    ```python
    >>> schema = get_ruleset_json_schema({"type": "string"}, {"type": "number"})
    >>> schema["required"], schema["properties"]["otherwise"]
    (['otherwise'], {'$ref': 'urn:pyruleset:value'})
    >>> schema["$defs"]["value"]
    {'type': 'number', '$id': 'urn:pyruleset:value'}

    ```

    """
    branch = {
        "type": "object",
        "properties": {
            "when": {"$ref": CONDITION_SCHEMA_ID},
            "then": {"$ref": VALUE_SCHEMA_ID},
            "label": {"type": "string"},
        },
        "required": ["when", "then"],
        "additionalProperties": False,
    }
    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "type": "object",
        "properties": {
            "branches": {"type": "array", "items": {"$ref": "#/$defs/branch"}},
            "otherwise": {"$ref": VALUE_SCHEMA_ID},
        },
        "required": ["otherwise"],
        "additionalProperties": False,
        "$defs": {
            "branch": branch,
            "condition": {**condition_schema, "$id": CONDITION_SCHEMA_ID},
            "value": {**value_schema, "$id": VALUE_SCHEMA_ID},
        },
    }
