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
- [x] 46 tests on Python 3.12 and 3.13, including integration with pyspecification, pyformula and pyflowstep; ruff and `mypy --strict` clean
- [ ] Measure branch coverage

## Phase 3 — JSON Schema
- [ ] `get_ruleset_json_schema(condition_schema, value_schema)` embedding both sub-schemas (needs `$id` handling in pyvocabulary)

## Phase 4 — Docs and examples
- [ ] `examples/`: pricing policy from an admin panel, expense approvals, ticket routing with pyflowstep
- [ ] README: money section (`parse_float=Decimal`, pyformula `literal=decimal_literal`)

## Phase 5 — Release
- [ ] Create the GitHub repository `aaltatan/pyruleset` and push
- [ ] CI on 3.12 and 3.13; publish after pyvocabulary is on PyPI
- [ ] Confirm the PyPI name `pyruleset` is free just before publishing
