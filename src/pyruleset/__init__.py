"""pyruleset: conditional values that are composable and definable as JSON.

Pick a value by the first condition that matches. Conditions are any
`T -> bool` callable (a pyspecification `Predicate` fits), values any
`T -> V` callable (a pyformula `Formula` or a pyflowstep `Flow` fits).
"""

from .compilers import BranchDict, Compiler, RulesetCompiler, RulesetDict
from .exceptions import InvalidRulesetDefinitionError, PyrulesetError
from .json_schema import get_ruleset_json_schema
from .ruleset import (
    FALLBACK_LABEL,
    Branch,
    Condition,
    Otherwise,
    PartialRuleset,
    Ruleset,
    Value,
    otherwise,
    when,
)

__all__ = [
    "FALLBACK_LABEL",
    "Branch",
    "BranchDict",
    "Compiler",
    "Condition",
    "InvalidRulesetDefinitionError",
    "Otherwise",
    "PartialRuleset",
    "PyrulesetError",
    "Ruleset",
    "RulesetCompiler",
    "RulesetDict",
    "Value",
    "get_ruleset_json_schema",
    "otherwise",
    "when",
]
