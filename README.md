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

| Skill | Description | Based On |
|-------|-------------|----------|
| **setting-up-python-libraries** | Project setup with pyproject.toml, uv, ruff, pytest, pre-commit, GitHub Actions | [Defining Library Scope](https://mcginniscommawill.com/posts/2025-01-17-defining-library-scope/), [Dependency Management](https://mcginniscommawill.com/posts/2025-01-21-dependency-management/), [Licensing](https://mcginniscommawill.com/posts/2025-01-24-licensing-your-project/), [pyproject.toml Explained](https://mcginniscommawill.com/posts/2025-01-26-pyproject-toml-explained/) |
| **improving-python-code-quality** | Ruff linting, mypy type checking, Pythonic idioms, refactoring | [Linting & Formatting with Ruff](https://mcginniscommawill.com/posts/2025-01-30-linting-formatting-ruff/), [Understanding McCabe Complexity](https://mcginniscommawill.com/posts/2025-04-24-understanding-mccabe-complexity/), [Adding Type Hints](https://mcginniscommawill.com/posts/2025-04-03-pygeohash-type-hints/) |
| **testing-python-libraries** | Pytest test suites, fixtures, parametrization, Hypothesis property-based testing | [Testing with Pytest](https://mcginniscommawill.com/posts/2025-02-04-testing-pytest-intro/), [Testing Coverage](https://mcginniscommawill.com/posts/2025-02-09-testing-coverage/), [Testing with Tox](https://mcginniscommawill.com/posts/2025-02-13-testing-tox/), [Testing with Mocking](https://mcginniscommawill.com/posts/2025-02-16-testing-mocking/) |
| **auditing-python-security** | Security audits with Bandit, pip-audit, Semgrep, detect-secrets | [Avoiding Injection Flaws](https://mcginniscommawill.com/posts/2025-01-18-avoiding-injection-flaws/), [Intro to Bandit](https://mcginniscommawill.com/posts/2025-01-25-intro-to-bandit/), [Dependency Security](https://mcginniscommawill.com/posts/2025-01-27-dependency-security-pip-audit/), [Handling Sensitive Data](https://mcginniscommawill.com/posts/2025-01-29-handling-sensitive-data/), [Secure Coding Practices](https://mcginniscommawill.com/posts/2025-02-02-secure-coding-practices/) |
| **designing-python-apis** | API design principles, deprecation, breaking changes, error handling | [The Art of API Design](https://mcginniscommawill.com/posts/2025-02-03-art-of-api-design/), [Designing for Developer Joy](https://mcginniscommawill.com/posts/2025-02-06-designing-for-developer-joy/) |
| **documenting-python-libraries** | Google-style docstrings, Sphinx setup, ReadTheDocs configuration | [Writing Effective Docstrings](https://mcginniscommawill.com/posts/2025-03-06-writing-effective-docstrings/), [Getting Started with Sphinx](https://mcginniscommawill.com/posts/2025-03-15-getting-started-sphinx/), [Automating Docs Deployment](https://mcginniscommawill.com/posts/2025-03-23-automating-docs-deployment/), [Documenting Your Library's API](https://mcginniscommawill.com/posts/2025-03-30-documenting-library-api/) |
| **packaging-python-libraries** | pyproject.toml, PyPI publishing, trusted publishing, wheel building | [pyproject.toml Explained](https://mcginniscommawill.com/posts/2025-01-26-pyproject-toml-explained/), [Publishing PyGeohash](https://mcginniscommawill.com/posts/2025-04-06-pygeohash-publishing/) |
| **managing-python-releases** | Semantic versioning, changelogs, release automation, deprecation workflows | [Semantic Versioning](https://mcginniscommawill.com/posts/2025-01-28-semantic-versioning/) |
| **optimizing-python-performance** | Profiling, memory analysis, benchmarking, optimization strategies | [Performance Benchmarking](https://mcginniscommawill.com/posts/2025-02-22-testing-benchmark/), [Profiling with PyInstrument](https://mcginniscommawill.com/posts/2025-02-25-testing-profiling-pyinstrument/), [Memory Profiling with Memray](https://mcginniscommawill.com/posts/2025-03-01-testing-profiling-memray/) |
| **building-python-clis** | Click/Typer CLIs, command groups, shell completion, CLI testing | [Guide to Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) |
| **building-python-communities** | CONTRIBUTING.md, issue templates, PR templates, GitHub automation | [Building Engaging Community](https://mcginniscommawill.com/posts/2025-01-22-building-engaging-community/), [Inner Source Introduction](https://mcginniscommawill.com/posts/2025-02-11-inner-source-introduction/), [From Silos to Shared Libraries](https://mcginniscommawill.com/posts/2025-02-18-silos-to-shared-libraries/) |
| **reviewing-python-libraries** | Comprehensive library reviews across all quality dimensions | [Guide to Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) |

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
