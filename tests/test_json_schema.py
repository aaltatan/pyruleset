import json

import pytest
from jsonschema import Draft202012Validator
from pyspecification import get_expression_json_schema

from pyruleset import get_ruleset_json_schema
from tests.test_compilers import POLICY

# pyformula has no JSON Schema yet; this one has its own `#/$defs` refs, like pyspecification's.
FORMULA_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$defs": {
        "formula": {
            "anyOf": [
                {"enum": ["subtotal"], "type": "string"},
                {"type": "number"},
                {
                    "type": "object",
                    "properties": {
                        "operator": {"enum": ["add", "subtract", "multiply", "divide"]},
                        "expressions": {"type": "array", "items": {"$ref": "#/$defs/formula"}},
                    },
                    "required": ["operator", "expressions"],
                    "additionalProperties": False,
                },
            ]
        }
    },
    "$ref": "#/$defs/formula",
}


@pytest.fixture
def validator(rules):
    schema = get_ruleset_json_schema(get_expression_json_schema(rules), FORMULA_SCHEMA)
    return Draft202012Validator(schema)


@pytest.fixture
def policy():
    return json.loads(POLICY)


def errors(validator, definition):
    return [error.message for error in validator.iter_errors(definition)]


class TestRulesetJsonSchema:
    def test_schema_is_a_valid_2020_12_schema(self, validator):
        Draft202012Validator.check_schema(validator.schema)

    def test_policy_that_compiles_is_valid(self, validator, policy):
        assert errors(validator, policy) == []

    def test_branches_are_optional(self, validator):
        assert errors(validator, {"otherwise": 0}) == []

    def test_embedded_schemas_resolve_their_own_refs(self, validator, policy):
        policy["branches"][1]["when"]["expressions"][1]["name"] = "subtotal__gee"
        policy["branches"][0]["then"]["expressions"][0] = "subtotall"

        assert len(errors(validator, policy)) == 2

    def test_unknown_rule_in_when_is_invalid(self, validator, policy):
        policy["branches"][2]["when"]["name"] = "itemz__ge"
        assert errors(validator, policy)

    def test_invalid_fallback_is_invalid(self, validator, policy):
        policy["otherwise"] = "nope"
        assert errors(validator, policy)

    @pytest.mark.parametrize(
        "definition",
        [
            {"branches": []},
            {"otherwise": 0, "fallback": 1},
            {"otherwise": 0, "branches": {}},
            {"otherwise": 0, "branches": [{"then": 1}]},
            {"otherwise": 0, "branches": [{"when": {}, "then": 1, "if": 1}]},
        ],
    )
    def test_malformed_shapes_are_invalid(self, validator, definition):
        assert errors(validator, definition)

    def test_label_must_be_a_string(self, validator, policy):
        policy["branches"][0]["label"] = 3
        assert "3 is not of type 'string'" in errors(validator, policy)

    def test_input_schemas_are_not_changed(self, rules):
        condition = get_expression_json_schema(rules)
        before = json.dumps(condition)
        get_ruleset_json_schema(condition, FORMULA_SCHEMA)
        assert json.dumps(condition) == before
        assert "$id" not in FORMULA_SCHEMA
