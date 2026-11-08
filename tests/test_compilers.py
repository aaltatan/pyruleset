import json
from decimal import Decimal

import pytest
from pyspecification import RuleDoesNotExistError

from pyruleset import InvalidRulesetDefinitionError, RulesetCompiler

POLICY = """
{
  "branches": [
    {"label": "gold 20%",
     "when": {"name": "tier__eq", "args": ["gold"], "kwargs": {}, "inverse": false},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.80]}},
    {"label": "silver",
     "when": {"operator": "all", "expressions": [
        {"name": "tier__eq", "args": ["silver"], "kwargs": {}, "inverse": false},
        {"name": "subtotal__ge", "args": [200], "kwargs": {}, "inverse": false}]},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.90]}},
    {"label": "bulk 5%",
     "when": {"name": "items__ge", "args": [10], "kwargs": {}, "inverse": false},
     "then": {"operator": "multiply", "expressions": ["subtotal", 0.95]}},
    {"label": "welcome coupon",
     "when": {"name": "coupon__eq", "args": ["WELCOME"], "kwargs": {}, "inverse": false},
     "then": {"operator": "subtract", "expressions": ["subtotal", 10]}}
  ],
  "otherwise": "subtotal"
}
"""


@pytest.fixture
def compiler(condition_compiler, value_compiler):
    return RulesetCompiler(condition_compiler, value_compiler)


@pytest.fixture
def policy():
    return json.loads(POLICY, parse_float=Decimal)


class TestCompiling:
    def test_compiled_ruleset_matches_the_python_one(self, compiler, policy, price_ruleset, orders):
        compiled = compiler.compile(policy)

        assert repr(compiled) == repr(price_ruleset)
        assert all(compiled(order) == price_ruleset(order) for order in orders.values())

    def test_labels_are_optional(self, compiler, policy, orders):
        del policy["branches"][0]["label"]
        assert compiler.compile(policy).explain(orders["gold"]) == "tier__eq"

    def test_branches_are_optional(self, compiler, orders):
        assert compiler.compile({"otherwise": "subtotal"})(orders["gold"]) == Decimal("120.00")

    def test_parse_float_decimal_keeps_money_exact(self, compiler, policy, orders):
        assert str(compiler.compile(policy)(orders["gold"])) == "96.0000"

    def test_json_floats_leak_into_money(self, compiler, orders):
        # Documents the pitfall pyformula's `literal=` hook is meant to remove.
        leaky = compiler.compile(json.loads(POLICY))
        assert leaky(orders["gold"]) != Decimal("96.0000")


class TestErrors:
    def test_unknown_rule_keeps_its_type_and_gets_the_full_path(self, compiler, policy):
        policy["branches"][2]["when"]["name"] = "itemz__ge"

        with pytest.raises(RuleDoesNotExistError, match="Available rules") as info:
            compiler.compile(policy)

        assert info.value.__notes__ == ["at $.branches[2].when"]

    def test_nested_rule_error_gets_the_full_nested_path(self, compiler, policy):
        policy["branches"][1]["when"]["expressions"][1]["name"] = "subtotal__gee"

        with pytest.raises(RuleDoesNotExistError) as info:
            compiler.compile(policy)

        assert info.value.__notes__ == ["at $.branches[1].when.expressions[1]"]

    def test_unknown_formula_gets_the_path(self, compiler, policy):
        policy["branches"][0]["then"]["expressions"][0] = "subtotall"

        with pytest.raises(Exception, match="subtotall") as info:
            compiler.compile(policy)

        assert info.value.__notes__ == ["at $.branches[0].then.expressions[0]"]

    def test_bad_fallback_gets_the_path(self, compiler, policy):
        policy["otherwise"] = "nope"

        with pytest.raises(Exception, match="nope") as info:
            compiler.compile(policy)

        assert info.value.__notes__ == ["at $.otherwise"]

    @pytest.mark.parametrize(
        ("definition", "message"),
        [
            ([], r"at \$: expected an object"),
            ({"branches": []}, r"at \$: missing 'otherwise'"),
            ({"otherwise": "x", "fallback": "y"}, r"unknown 'fallback'. Allowed keys: branches"),
            ({"otherwise": "x", "branches": {}}, r"at \$.branches: expected a list"),
            ({"otherwise": "x", "branches": [1]}, r"at \$.branches\[0\]: expected an object"),
            ({"otherwise": "x", "branches": [{"when": "a"}]}, r"\[0\]: missing 'then'"),
            (
                {"otherwise": "x", "branches": [{"when": "a", "then": "b", "if": 1}]},
                r"unknown 'if'",
            ),
            (
                {"otherwise": "x", "branches": [{"when": "a", "then": "b", "label": 3}]},
                r"\[0\].label: expected a string",
            ),
        ],
    )
    def test_malformed_definitions(self, compiler, definition, message):
        with pytest.raises(InvalidRulesetDefinitionError, match=message):
            compiler.compile(definition)

    def test_invalid_definition_is_a_value_error(self, compiler):
        with pytest.raises(ValueError, match="missing"):
            compiler.compile({})
