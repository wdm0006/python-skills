# Python Library Development Skills

A comprehensive set of Claude Code skills for professional Python library development, based on the guide at [mcginniscommawill.com](https://mcginniscommawill.com/guides/python-library-development/).

## Installation

### Step 1: Add the Marketplace

First, add this repository as a plugin marketplace in Claude Code:

```
/plugin marketplace add wdm0006/python-skills
```

### Step 2: Install a Plugin Bundle

Install the complete skill set (recommended):

```
/plugin install python-library-complete@wdm0006-python-skills
```

Or install specific bundles based on your needs:

```
# Core skills for starting projects
/plugin install python-library-foundations@wdm0006-python-skills

# Skills for packaging and releasing
/plugin install python-library-distribution@wdm0006-python-skills

# Quality-focused skills (security, performance, API design)
/plugin install python-library-quality@wdm0006-python-skills
```

### Alternative: Local Installation

For project-specific installation, clone this repository and copy the skills you need:

```bash
# Clone the repository
git clone https://github.com/wdm0006/python-skills.git

# Copy skills to your project's .claude/skills/ directory
mkdir -p .claude/skills
cp -r python-skills/skills/* .claude/skills/
```

Or for global installation (available in all projects):

```bash
# Copy to your personal Claude skills directory
mkdir -p ~/.claude/skills
cp -r python-skills/skills/* ~/.claude/skills/
```

### Verifying Installation

After installation, you can verify the skills are loaded by running:

```
/plugin list
```

> **Note:** Skills require Claude Code Pro, Max, Team, or Enterprise. Free tier users do not have access to Skills.

## Available Skills

| Skill | Description |
|-------|-------------|
| **setting-up-python-libraries** | Project setup with pyproject.toml, uv, ruff, pytest, pre-commit, GitHub Actions |
| **improving-python-code-quality** | Ruff linting, mypy type checking, Pythonic idioms, refactoring |
| **testing-python-libraries** | Pytest test suites, fixtures, parametrization, Hypothesis property-based testing |
| **auditing-python-security** | Security audits with Bandit, pip-audit, Semgrep, detect-secrets |
| **designing-python-apis** | API design principles, deprecation, breaking changes, error handling |
| **documenting-python-libraries** | Google-style docstrings, Sphinx setup, ReadTheDocs configuration |
| **packaging-python-libraries** | pyproject.toml, PyPI publishing, trusted publishing, wheel building |
| **managing-python-releases** | Semantic versioning, changelogs, release automation, deprecation workflows |
| **optimizing-python-performance** | Profiling, memory analysis, benchmarking, optimization strategies |
| **building-python-clis** | Click/Typer CLIs, command groups, shell completion, CLI testing |
| **building-python-communities** | CONTRIBUTING.md, issue templates, PR templates, GitHub automation |
| **reviewing-python-libraries** | Comprehensive library reviews across all quality dimensions |

## Plugin Bundles

### python-library-complete
All 12 skills for comprehensive Python library development.

### python-library-foundations
Core skills for starting projects:
- Project setup
- Code quality
- Testing strategy

### python-library-distribution
Skills for packaging and releasing:
- Packaging
- Release management
- CLI development

### python-library-quality
Quality-focused skills:
- Security audit
- Performance
- API design

## Usage

Once installed, Claude will automatically use these skills when you ask about:

- Setting up a new Python library
- Adding tests to your project
- Publishing to PyPI
- Reviewing code quality
- Security scanning
- Writing documentation
- And more...

## Contributing

Contributions are welcome! Please open an issue or PR on [GitHub](https://github.com/wdm0006/python-skills).

## License

MIT License - see [LICENSE](LICENSE) for details.
