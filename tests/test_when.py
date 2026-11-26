from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator
from pyformula import Formula, FormulaCompiler, FormulaNotFoundError, decimal_literal
from pyformula import get_formula_json_schema as formula_schema
from pyspecification import RuleDoesNotExistError, get_expression_json_schema

from pyruleset import (
    InvalidRulesetDefinitionError,
    WhenCompiler,
    get_ruleset_json_schema,
    get_when_json_schema,
)
from tests.conftest import ORDERS, subtotal

GOLD_20 = {
    "when": {
        "branches": [
            {
                "when": {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": False},
                "then": {"operator": "multiply", "expressions": ["subtotal", 0.2]},
                "label": "gold 20%",
            }
        ],
        "otherwise": 0,
    }
}


@pytest.fixture
def compiler(condition_compiler):
    return WhenCompiler(
        condition_compiler,
        lambda names: FormulaCompiler({"subtotal": subtotal, **names}, literal=decimal_literal),
        wrap=Formula,
    )


@pytest.fixture
def validator(rules):
    predicate = get_expression_json_schema(rules)
    formula = formula_schema({"subtotal": subtotal}, nodes=[get_when_json_schema(predicate)])
    schema = get_ruleset_json_schema(predicate, formula)
    Draft202012Validator.check_schema(schema)

    return Draft202012Validator(schema)


class TestWhenCompiler:
    def test_a_formula_without_when_compiles_as_usual(self, compiler):
        formula = compiler.compile({"operator": "multiply", "expressions": ["subtotal", 0.5]})

        assert formula(ORDERS["gold"]) == Decimal("60.000")

    def test_a_when_node_is_a_value_inside_a_formula(self, compiler):
        discount = compiler.compile({"operator": "subtract", "expressions": ["subtotal", GOLD_20]})

        assert discount(ORDERS["gold"]) == Decimal("96.000")
        assert discount(ORDERS["plain"]) == Decimal("60.00")

    def test_a_when_node_alone(self, compiler):
        assert compiler.compile(GOLD_20)(ORDERS["gold"]) == Decimal("24.000")

    def test_when_nodes_nest_inside_branches(self, compiler):
        nested = {"when": {"branches": [], "otherwise": {"round": GOLD_20, "ndigits": 0}}}

        assert compiler.compile(nested)(ORDERS["gold"]) == Decimal(24)

    def test_the_name_shows_each_branch_and_its_value(self, compiler):
        formula = compiler.compile({"operator": "add", "expressions": [GOLD_20, 1]})

        assert str(formula) == "(when(gold 20% -> (subtotal * 0.2) | otherwise -> 0) + 1)"

    def test_without_wrap_the_ruleset_itself_is_the_value(self, condition_compiler):
        compiler = WhenCompiler(
            condition_compiler,
            lambda names: FormulaCompiler({"subtotal": subtotal, **names}, literal=decimal_literal),
        )

        assert compiler.compile(GOLD_20)(ORDERS["gold"]) == Decimal("24.000")

    def test_errors_inside_a_when_node_say_where(self, compiler):
        broken = {
            "operator": "add",
            "expressions": [
                1,
                {
                    "when": {
                        "branches": [
                            {
                                "when": {
                                    "name": "tier__eqq",
                                    "args": [],
                                    "kwargs": {},
                                    "inverse": False,
                                },
                                "then": 1,
                            }
                        ],
                        "otherwise": 0,
                    }
                },
            ],
        }

        with pytest.raises(RuleDoesNotExistError) as raised:
            compiler.compile(broken)

        assert raised.value.__notes__ == ["at $.expressions[1].when.branches[0].when"]

    def test_errors_in_a_nested_value_say_where(self, compiler):
        broken = {"when": {"branches": [], "otherwise": {"floor": "subtotall"}}}

        with pytest.raises(FormulaNotFoundError) as raised:
            compiler.compile(broken)

        assert raised.value.__notes__ == ["at $.when.otherwise.floor"]

    def test_a_malformed_ruleset_is_reported(self, compiler):
        with pytest.raises(InvalidRulesetDefinitionError, match="missing 'otherwise'"):
            compiler.compile({"when": {"branches": []}})


class TestWhenJsonSchema:
    def test_root_and_inner_rulesets_are_marked(self, validator):
        schema = validator.schema
        when = get_when_json_schema({"type": "boolean"})

        assert schema["x-kind"] == "ruleset"
        assert when["properties"]["when"]["x-kind"] == "ruleset"

    @pytest.mark.parametrize(
        "then",
        [
            GOLD_20,
            {"operator": "add", "expressions": ["subtotal", GOLD_20]},
            {"when": {"branches": [], "otherwise": {"round": GOLD_20, "ndigits": 2}}},
        ],
    )
    def test_when_nodes_are_valid_values(self, validator, then):
        ruleset = {
            "branches": [{"when": GOLD_20["when"]["branches"][0]["when"], "then": then}],
            "otherwise": then,
        }

        assert list(validator.iter_errors(ruleset)) == []

    @pytest.mark.parametrize(
        "then",
        [
            {"when": {"branches": []}},
            {"when": {"branches": [], "otherwise": "subtotall"}},
            {"when": {"branches": [{"when": {"name": "tier__eqq"}, "then": 1}], "otherwise": 0}},
            {"when": {"branches": [], "otherwise": 0}, "label": "x"},
        ],
    )
    def test_invalid_when_nodes_are_rejected(self, validator, then):
        assert not validator.is_valid({"otherwise": then})

    def test_a_formula_root_with_when_nodes(self, rules):
        predicate = get_expression_json_schema(rules)
        schema = formula_schema({"subtotal": subtotal}, nodes=[get_when_json_schema(predicate)])
        validator = Draft202012Validator(schema)

        assert validator.is_valid({"operator": "add", "expressions": [GOLD_20, 1]})
        assert not validator.is_valid({"operator": "add", "expressions": [{"when": 1}, 1]})

    def test_input_schema_is_not_changed(self, rules):
        predicate = get_expression_json_schema(rules)
        before = repr(predicate)

        get_when_json_schema(predicate)

        assert repr(predicate) == before
