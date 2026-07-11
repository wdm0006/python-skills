# Community File Templates

Copy-pasteable templates for Python library community infrastructure. Drop each into the path shown in its heading.

## Contents

- [CONTRIBUTING.md](#contributingmd)
- [CODE_OF_CONDUCT.md](#code_of_conductmd)
- [Issue Forms](#issue-forms)
  - [bug_report.yml](#githubissue_templatebug_reportyml)
  - [feature_request.yml](#githubissue_templatefeature_requestyml)
  - [config.yml](#githubissue_templateconfigyml)
- [PULL_REQUEST_TEMPLATE.md](#pull_request_templatemd)
- [README Structure Checklist](#readme-structure-checklist)

## CONTRIBUTING.md

```markdown
# Contributing

Thanks for helping improve this project. This guide covers setup, workflow, and expectations.

## Development Setup

We use [uv](https://docs.astral.sh/uv/) for environment and dependency management.

    git clone https://github.com/user/package.git
    cd package
    uv sync --extra dev
    uv run pre-commit install
    uv run pytest

## Making Changes

1. Open (or comment on) an issue first for anything non-trivial.
2. Create a branch: `git checkout -b feature/short-name`
3. Make changes and add tests covering them.
4. Run the full check suite:

       uv run pytest
       uv run ruff check .
       uv run mypy src

5. Commit with a clear message and open a pull request.

## Commit Messages

Prefix the subject line:

- `Add:` new feature
- `Fix:` bug fix
- `Update:` enhancement to existing behavior
- `Docs:` documentation only
- `Test:` tests only
- `Refactor:` no behavior change

Keep the subject under 72 characters; explain the "why" in the body.

## Pull Requests

- One logical change per PR; keep them small and reviewable.
- Fill out the PR template checklist.
- Add a CHANGELOG entry.
- CI must pass before review.
- A maintainer reviews within one week; address feedback with follow-up commits.

## Reporting Bugs

Use the bug report issue form. Always include a minimal reproducible example
and your OS, Python version, and package version.

## Code of Conduct

Participation is governed by CODE_OF_CONDUCT.md. Report concerns to the address listed there.

## Questions

Open a Discussion or an issue with the `question` label. We aim to respond within 48 hours.
```

## CODE_OF_CONDUCT.md

Adopt the [Contributor Covenant](https://www.contributor-covenant.org/) rather than writing your own. It is the de facto standard, translated into many languages, and instantly recognizable to contributors.

Steps:

1. Download version 2.1 from the [Contributor Covenant site](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
2. Save it as `CODE_OF_CONDUCT.md` in the repo root.
3. Replace the `[INSERT CONTACT METHOD]` placeholder with a real, monitored address (a dedicated alias like `conduct@project.org` is best).
4. Reference it from CONTRIBUTING.md and the README.

Minimal header showing the required customization point:

```markdown
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone...

<!-- full text from contributor-covenant.org v2.1 -->

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the community leaders responsible for enforcement at
conduct@project.org. All complaints will be reviewed and investigated promptly
and fairly.
```

## Issue Forms

Issue forms (`.yml`) render structured, required fields in GitHub's UI and beat plain-Markdown templates for data quality. Place them in `.github/ISSUE_TEMPLATE/`.

### .github/ISSUE_TEMPLATE/bug_report.yml

```yaml
name: Bug Report
description: Report something that is broken or behaves incorrectly.
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: Thanks for reporting. Please search existing issues first.
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What went wrong?
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Minimal Reproducible Example
      description: The smallest code snippet that triggers the bug.
      render: python
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected vs Actual Behavior
    validations:
      required: true
  - type: input
    id: package-version
    attributes:
      label: Package version
    validations:
      required: true
  - type: input
    id: python-version
    attributes:
      label: Python version
    validations:
      required: true
  - type: input
    id: os
    attributes:
      label: Operating system
    validations:
      required: true
```

### .github/ISSUE_TEMPLATE/feature_request.yml

```yaml
name: Feature Request
description: Suggest a new capability or enhancement.
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem Statement
      description: What problem does this solve? What are you unable to do today?
    validations:
      required: true
  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
    validations:
      required: true
  - type: textarea
    id: example
    attributes:
      label: Example Usage
      description: Show how the API would look if this existed.
      render: python
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
```

### .github/ISSUE_TEMPLATE/config.yml

Disable blank issues and route non-bug questions elsewhere:

```yaml
blank_issues_enabled: false
contact_links:
  - name: Questions & Discussion
    url: https://github.com/user/package/discussions
    about: Ask usage questions and share ideas here.
```

## PULL_REQUEST_TEMPLATE.md

Place at `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## Description

<!-- What does this change and why? -->

## Related Issue

Fixes #

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## Checklist

- [ ] Tests added or updated
- [ ] Documentation updated
- [ ] CHANGELOG entry added
- [ ] `uv run pytest` passes locally
- [ ] `uv run ruff check .` passes locally
```

## README Structure Checklist

A strong library README moves top to bottom from "what and why" to "how" to "where next". Order matters: put the value proposition and install/quickstart above the fold.

```
- [ ] Project name + one-line description
- [ ] Badges (CI status, PyPI version, coverage, license)
- [ ] Why this exists (problem it solves, 2-3 sentences)
- [ ] Installation (uv add package / uv pip install package)
- [ ] Quickstart: a copy-pasteable, working example
- [ ] Key features (short bullet list)
- [ ] Link to full documentation
- [ ] Contributing pointer (link to CONTRIBUTING.md)
- [ ] License
- [ ] Acknowledgements / contributor recognition
```

Keep the quickstart runnable as-is; a broken first example is the fastest way to lose a new user.
