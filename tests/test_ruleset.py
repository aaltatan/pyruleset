from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest
from pyflowstep import step

from pyruleset import Branch, Otherwise, PartialRuleset, Ruleset, otherwise, when
from tests.conftest import subtotal, tier__eq


def is_negative(number: int) -> bool:
    return number < 0


def negate(number: int) -> int:
    return -number


def identity(number: int) -> int:
    return number


class TestDeciding:
    def test_first_matching_branch_wins(self, price_ruleset, orders):
        assert price_ruleset(orders["gold"]) == Decimal("96.0000")
        assert price_ruleset(orders["silver_big"]) == Decimal("225.0000")

    def test_later_branch_matches_when_earlier_fail(self, price_ruleset, orders):
        assert price_ruleset(orders["silver_bulk"]) == Decimal("142.5000")
        assert price_ruleset(orders["coupon"]) == Decimal("50.00")

    def test_fallback_when_no_branch_matches(self, price_ruleset, orders):
        assert price_ruleset(orders["plain"]) == Decimal("60.00")

    def test_conditions_after_the_match_are_not_evaluated(self):
        calls: list[str] = []

        def recording(name: str, *, result: bool):
            def condition(_: int) -> bool:
                calls.append(name)
                return result

            return condition

        ruleset = (
            when(recording("first", result=True), identity)
            | when(recording("second", result=True), identity)
            | otherwise(identity)
        )

        ruleset(1)

        assert calls == ["first"]

    def test_values_can_be_any_callable(self):
        ruleset = when(is_negative, lambda _: "negative") | otherwise(lambda _: "other")
        assert [ruleset(n) for n in (-1, 1)] == ["negative", "other"]

    def test_truthy_condition_results_count_as_matches(self):
        ruleset = when(lambda items: items, len) | otherwise(lambda _: -1)
        assert ruleset([1, 2]) == 2
        assert ruleset([]) == -1

    def test_a_flow_can_be_the_value(self):
        @step
        def add(total: int, amount: int) -> int:
            return total + amount

        ruleset = when(is_negative, add(100) >> add(1)) | otherwise(add(0))

        assert ruleset(-5) == 96
        assert ruleset(5) == 5


class TestExplain:
    def test_explain_returns_the_label(self, price_ruleset, orders):
        assert price_ruleset.explain(orders["silver_bulk"]) == "bulk 5%"

    def test_explain_returns_otherwise_for_the_fallback(self, price_ruleset, orders):
        assert price_ruleset.explain(orders["plain"]) == "otherwise"

    def test_explain_without_label_uses_the_condition_name(self):
        ruleset = when(is_negative, negate) | otherwise(identity)
        assert ruleset.explain(-1) == "is_negative"

    def test_explain_uses_the_predicate_name(self, orders):
        ruleset = when(tier__eq("gold"), subtotal) | otherwise(subtotal)
        assert ruleset.explain(orders["gold"]) == "tier__eq"

    def test_decide_returns_the_branch(self):
        ruleset = when(is_negative, negate, label="negative") | otherwise(identity)
        assert ruleset.decide(-1) == Branch(is_negative, negate, "negative")
        assert ruleset.decide(1) == Otherwise(identity)


class TestComposition:
    def test_when_returns_a_partial_ruleset(self):
        assert isinstance(when(is_negative, negate), PartialRuleset)

    def test_partial_ruleset_is_not_callable(self):
        assert not callable(when(is_negative, negate))

    def test_partial_or_partial_keeps_order(self):
        combined = when(is_negative, negate, label="a") | when(bool, identity, label="b")
        assert repr(combined) == "PartialRuleset(a | b)"

    def test_partial_or_otherwise_returns_a_ruleset(self):
        assert isinstance(when(is_negative, negate) | otherwise(identity), Ruleset)

    def test_partial_or_ruleset_puts_overrides_first(self):
        base = when(is_negative, negate, label="negative") | otherwise(identity)
        overrides = when(lambda n: n == 13, lambda _: 0, label="thirteen")

        combined = overrides | base

        assert repr(combined) == "Ruleset(thirteen | negative | otherwise)"
        assert (combined(13), combined(-2), combined(3)) == (0, 2, 3)

    def test_composition_returns_new_objects(self):
        first = when(is_negative, negate)
        second = first | when(bool, identity)
        assert first.branches != second.branches
        assert len(first.branches) == 1

    def test_or_with_something_else_is_a_type_error(self):
        with pytest.raises(TypeError):
            when(is_negative, negate) | 1  # type: ignore[operator]

    def test_ruleset_has_no_or(self):
        ruleset = when(is_negative, negate) | otherwise(identity)
        with pytest.raises(TypeError):
            ruleset | otherwise(identity)  # type: ignore[operator]

    def test_rulesets_are_immutable(self):
        ruleset = when(is_negative, negate) | otherwise(identity)
        with pytest.raises(FrozenInstanceError):
            ruleset.fallback = negate  # type: ignore[misc]
        assert replace(ruleset, fallback=negate)(5) == -5


class TestRepr:
    def test_repr_lists_labels_and_otherwise(self, price_ruleset):
        assert repr(price_ruleset) == (
            "Ruleset(gold 20% | silver | bulk 5% | welcome coupon | otherwise)"
        )

    def test_repr_of_a_lambda_condition(self):
        assert repr(when(lambda n: n, identity)) == "PartialRuleset(<lambda>)"

    def test_repr_of_a_callable_without_name(self):
        class Positive:
            def __call__(self, number: int) -> bool:
                return number > 0

        assert repr(when(Positive(), identity)).startswith("PartialRuleset(<")
