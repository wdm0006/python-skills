---
name: building-python-communities
description: Builds and manages open source Python library communities including CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue/PR templates, contributor recognition, and GitHub automation. Use when setting up community infrastructure, improving contributor experience, or managing project governance.
---

# Python Library Community Management

## Essential Files

### CONTRIBUTING.md

```markdown
# Contributing

## Development Setup

git clone https://github.com/user/package.git
cd package
pip install -e ".[dev]"
pre-commit install
pytest

## Making Changes

1. Create a branch: `git checkout -b feature/name`
2. Make changes, add tests
3. Run: `make test && make lint`
4. Commit and open a PR

## Commit Messages

- `Add:` new feature
- `Fix:` bug fix
- `Update:` enhancement
- `Docs:` documentation
```

### CODE_OF_CONDUCT.md

Use [Contributor Covenant](https://www.contributor-covenant.org/) - the standard for open source.

## Issue Templates

**.github/ISSUE_TEMPLATE/bug_report.md:**
```markdown
---
name: Bug Report
labels: 'bug'
---
## Description
## To Reproduce
## Expected vs Actual Behavior
## Environment (OS, Python version, package version)
## Minimal Reproducible Example
```

**.github/ISSUE_TEMPLATE/feature_request.md:**
```markdown
---
name: Feature Request
labels: 'enhancement'
---
## Problem Statement
## Proposed Solution
## Example Usage
```

## PR Template

**.github/PULL_REQUEST_TEMPLATE.md:**
```markdown
## Description
## Related Issue (Fixes #)
## Checklist
- [ ] Tests added
- [ ] Documentation updated
- [ ] CHANGELOG entry added
```

## GitHub Actions Automation

```yaml
# .github/workflows/welcome.yml
on:
  pull_request_target:
    types: [opened]
jobs:
  welcome:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/first-interaction@v1
        with:
          pr-message: "Thanks for your first PR! 🎉"
```

## Labels

- `good first issue` - Newcomer-friendly
- `help wanted` - Extra attention needed
- `bug`, `enhancement`, `documentation`

For detailed templates, see:
- **[TEMPLATES.md](TEMPLATES.md)** - Full issue/PR templates
- **[GOVERNANCE.md](GOVERNANCE.md)** - Project governance guide

## Checklist

```
Initial Setup:
- [ ] CONTRIBUTING.md
- [ ] CODE_OF_CONDUCT.md
- [ ] Issue templates
- [ ] PR template
- [ ] Labels defined

Ongoing:
- [ ] Respond to issues within 48h
- [ ] Review PRs within 1 week
- [ ] Maintain good first issues
- [ ] Recognize contributors
```
