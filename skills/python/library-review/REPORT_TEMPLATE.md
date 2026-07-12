# Review Report Template

The complete report, expanding the short template in SKILL.md. Fill in every bracketed placeholder. Rate each dimension 1-5 stars using the scale below and back the score with concrete evidence (command output, file paths, line references). Delete any guidance lines before delivering.

Star scale: 5 stars exemplary, 4 solid with minor gaps, 3 workable with notable gaps, 2 weak and needs work, 1 absent or broken. Render scores as filled/empty star glyphs in the tables below.

## Contents

- [Metadata](#metadata)
- [Summary](#summary)
- [Dimension Scores](#dimension-scores)
- [Detailed Findings](#detailed-findings)
- [Recommendations](#recommendations)
- [Verdict](#verdict)

## Metadata

- **Package:** [name]
- **Version reviewed:** [version / git SHA]
- **Repository:** [url]
- **Reviewed on:** [date]
- **Supported Python:** [requires-python range]
- **License:** [license id]

## Summary

[Two or three sentences: what the library does, its overall health, and the single most important thing to fix.]

## Dimension Scores

| Dimension | Score | One-line rationale |
|-----------|-------|--------------------|
| Structure | [stars] | [rationale] |
| Packaging | [stars] | [rationale] |
| Code Quality | [stars] | [rationale] |
| Testing | [stars] | [rationale] |
| Security | [stars] | [rationale] |
| Documentation | [stars] | [rationale] |
| API Design | [stars] | [rationale] |
| CI/CD | [stars] | [rationale] |

## Detailed Findings

For each dimension, record the score, what passed, what failed, and the evidence you gathered (the command run and its result).

### Structure — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Evidence:** [e.g. `ls src/` output, `py.typed` present/absent]

### Packaging — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Evidence:** [e.g. `uv build` result, `uv run twine check dist/*` output]

### Code Quality — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Evidence:** [e.g. `uv run mypy src/`, `uv run ruff check src/` output]

### Testing — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Coverage:** [N]% (bar is 85%) — `uv run pytest --cov=package --cov-fail-under=85`
- **Evidence:** [pass/fail counts, missing-line summary]

### Security — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Evidence:** [e.g. `uv run bandit -r src/`, `uv run pip-audit` output]

### Documentation — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Evidence:** [README sections present, changelog freshness, example run result]

### API Design — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Evidence:** [public surface review, naming consistency, versioning notes]

### CI/CD — [stars]

- **Passed:** [items]
- **Gaps:** [items]
- **Evidence:** [workflow files, matrix, current default-branch status]

## Recommendations

Prioritized and actionable. Each item names the dimension, the fix, and the expected outcome.

### High

1. [Blocking issue — what to do and why it matters]

### Medium

1. [Important but non-blocking improvement]

### Low

1. [Polish or nice-to-have]

## Verdict

**Overall rating:** [Excellent / Good / Needs Work / Significant Issues]

[One paragraph tying the scores together: is the library safe to depend on today, what must change before the next major release, and the top one or two priorities.]
