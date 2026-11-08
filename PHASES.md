# PHASES

## Phase 0 — Scaffold
- [x] `uv init --lib`, Python 3.12, `uv_build`, ruff `ALL`, pytest with doctests, branch coverage config
- [x] CLAUDE.md, PHASES.md, README.md, LICENSE
- [x] Name chosen: `pydecision` is taken on PyPI, so the package is `pyruleset`

## Phase 1 — Core 0.1
- [x] `when`, `otherwise`, `Branch`, `Otherwise`, `PartialRuleset`, `Ruleset`
- [x] `label=` on `when`; `explain()` returns the label; `decide()` returns the branch
- [x] `partial | ruleset` for overrides on top of a base policy
- [x] Readable `repr`: `Ruleset(gold 20% | bulk 5% | otherwise)`

## Phase 2 — Compiler
- [x] `RulesetCompiler(conditions, values)` with injected `Compiler` protocols
- [x] Shape validation with `InvalidRulesetDefinitionError`
- [x] Full JSON paths on errors from injected compilers (via `pyvocabulary.located`)
- [x] 46 tests on Python 3.12 and 3.13, including integration with pyspecification, pyformula and pyflowstep; ruff and pyright strict clean
- [x] Measure branch coverage: 100% lines and branches (114 statements, 20 branches)

## Phase 3 — JSON Schema
- [x] `get_ruleset_json_schema(condition_schema, value_schema)` embedding both sub-schemas, each under its own `$id` (`urn:pyruleset:condition`, `urn:pyruleset:value`) so their internal `#/$defs` refs resolve; validated with `jsonschema` (dev only). Kept in pyruleset, not pyvocabulary: one use, one line

## Phase 4 — Docs and examples
- [x] `examples/`: pricing policy from an admin panel, expense approvals, ticket routing with pyflowstep (each asserts its results; `tests/test_examples.py` runs them)
- [x] README: money section (`parse_float=Decimal`, pyformula 0.2+ `literal=decimal_literal`), JSON Schema section, examples list

## Phase 5 — Release
- [x] Create the GitHub repository `aaltatan/pyruleset` and push
- [x] Publish 0.1.0 on PyPI (after pyvocabulary 0.1.0); README installs with `pip install pyruleset`
- [ ] CI on 3.12 and 3.13
