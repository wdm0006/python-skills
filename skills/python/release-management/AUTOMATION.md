# Release Automation

This is the canonical PyPI release pipeline for the skill set. Other skills
(packaging, project setup) point here instead of carrying their own copy.

## Contents
- Version bump script
- The canonical publish workflow (trusted publishing)
- TestPyPI dry run
- End-to-end release runbook

## Version bump script

`scripts/bump_version.py` updates the version in `pyproject.toml`, the package
`__init__.py`, and (optionally) inserts a dated heading into `CHANGELOG.md`.

```bash
uv run python scripts/bump_version.py patch              # 1.2.3 -> 1.2.4
uv run python scripts/bump_version.py minor --changelog  # 1.2.3 -> 1.3.0 + changelog
uv run python scripts/bump_version.py 2.0.0              # set an explicit version
uv run python scripts/bump_version.py minor --dry-run    # preview, write nothing
```

It refuses to set a version lower than the current one unless `--allow-downgrade`
is passed, so a fat-fingered release can't quietly ship backwards.

## The canonical publish workflow (trusted publishing)

One tag-triggered workflow builds the distribution with `uv`, creates a GitHub
release, and publishes to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/)
— no API token stored in the repo. Configure the PyPI project's trusted publisher
to point at this workflow first.

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    environment: release          # gate with required reviewers if desired
    permissions:
      contents: write             # create the GitHub release
      id-token: write             # OIDC token for trusted publishing
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build             # writes sdist + wheel to dist/
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/*
          generate_release_notes: true
      - uses: pypa/gh-action-pypi-publish@release/v1
```

`pypa/gh-action-pypi-publish@release/v1` is a rolling tag the PyPA maintains — pin
the other actions to a major version and let this one float.

## TestPyPI dry run

Validate the exact artifacts against TestPyPI before a real release by pushing a
pre-release tag (e.g. `v1.3.0rc1`) to a variant of the job, or run it locally:

```bash
uv build
uvx twine check dist/*                                   # metadata sanity
uvx twine upload --repository testpypi dist/*            # needs a TestPyPI token
```

## End-to-end release runbook

```
- [ ] All tests green on main
- [ ] uv run python scripts/bump_version.py <part> --changelog
- [ ] Review the CHANGELOG heading and move Unreleased entries under it
- [ ] git commit -am "Release vX.Y.Z"
- [ ] git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push origin main --tags
- [ ] Workflow builds, creates the GitHub release, and publishes to PyPI
- [ ] Verify: uv run --with <package>==X.Y.Z python -c "import <package>"
```
