"""Exceptions raised by pyruleset.

Errors raised by the injected condition and value compilers keep their own type
(e.g. pyspecification's `RuleDoesNotExistError`); pyruleset only adds a note
with their full JSON path, e.g. `at $.branches[1].when.expressions[0]`.
"""


class PyrulesetError(Exception):
    """Base class for every exception raised by pyruleset."""


class InvalidRulesetDefinitionError(PyrulesetError, ValueError):
    """Raised when a ruleset definition does not have the expected shape."""
