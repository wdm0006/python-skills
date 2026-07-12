# Developer Skills for Claude Code

A growing, multi-language set of opinionated, checklist-driven Claude Code skills for professional software development. It began as a Python library-development toolkit (based on the guide at [mcginniscommawill.com](https://mcginniscommawill.com/guides/python-library-development/)) and now also covers Go, Swift/Apple apps, Rust, and Scala. Install only the languages and bundles that make sense for you.

> **Heads up — repo rename planned.** The GitHub repository is still named `wdm0006/python-skills` for now and may be renamed to reflect its polyglot scope. The marketplace-add command below uses that repo path and will change when the repo is renamed; the install slug is `@dev-skills`.

## Installation

### Step 1: Add the Marketplace

First, add this repository as a plugin marketplace in Claude Code:

```
/plugin marketplace add wdm0006/python-skills
```

### Step 2: Install the Bundles You Need

Install a per-language bundle:

```
# Python — complete library toolkit (setup, quality, testing, packaging, docs, and more)
/plugin install python-library-complete@dev-skills

# Go — project setup & a CI gate that actually gates
/plugin install go-projects@dev-skills

# Swift / Apple platforms — Xcode build & CI, signing, Keychain, CloudKit/SwiftData
/plugin install swift-apps@dev-skills

# Rust — Cargo layout, fmt/clippy/test gate, MSRV, crates.io publishing
/plugin install rust-crates@dev-skills

# Scala — sbt build, scalafmt/scalafix gates, cross-building, Maven Central
/plugin install scala-projects@dev-skills
```

Or install a narrower Python bundle:

```
# Core skills for starting Python projects
/plugin install python-library-foundations@dev-skills

# Packaging and releasing Python libraries
/plugin install python-library-distribution@dev-skills

# Quality-focused Python skills (security, performance, API design, git hygiene)
/plugin install python-library-quality@dev-skills

# Opinionated architecture for Python web apps
/plugin install python-web-app@dev-skills

# Python MCP servers for LLM clients (FastMCP)
/plugin install python-mcp-servers@dev-skills
```

### Alternative: Local Installation

For project-specific installation, clone this repository and copy the skills you need:

```bash
# Clone the repository
git clone https://github.com/wdm0006/python-skills.git

# Copy skills to your project's .claude/skills/ directory
mkdir -p .claude/skills
cp -r python-skills/skills/python/* .claude/skills/       # or skills/go/*, skills/swift/*, etc.
cp -r python-skills/skills/common/* .claude/skills/       # git hygiene applies to every language
```

Or for global installation (available in all projects):

```bash
# Copy to your personal Claude skills directory
mkdir -p ~/.claude/skills
cp -r python-skills/skills/*/* ~/.claude/skills/
```

### Verifying Installation

After installation, you can verify the skills are loaded by running:

```
/plugin list
```

> **Note:** Skills require Claude Code Pro, Max, Team, or Enterprise. Free tier users do not have access to Skills.

## Available Skills

### Python

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
| **building-python-web-apps** | Opinionated reference architecture for production web apps — FastAPI, async SQLAlchemy/Postgres, Stripe billing, Jinja or SPA frontends, and Dockerized deployment via Terraform | Production web app patterns |
| **building-python-mcp-servers** | Robust Python MCP servers with FastMCP — tool design, error contracts, CLI/subprocess wrapping, single-file vs packaged distribution, testing, and prompt-injection awareness | [Guide to Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) |

### Go

| Skill | Description |
|-------|-------------|
| **building-go-projects** | Go project setup with a CI gate that actually gates — module-path correctness, golangci-lint config matched to the installed major, deterministic gofmt, pinned toolchain, meaningful test/lint jobs, injectable git/gh runners, and safe outbound HTTP |

### Swift / Apple Platforms

| Skill | Description |
|-------|-------------|
| **building-swift-apps** | Native Swift/SwiftUI apps for macOS/iOS — unsigned CI builds (`CODE_SIGNING_ALLOWED=NO`), the hand-maintained pbxproj, SwiftPM-vs-app-target test boundaries, SourceKit false positives, gitignored base xcconfig, Keychain vs UserDefaults + OAuth state/PKCE, CloudKit/SwiftData constraints, and deterministic dates/RNG |

### Rust

| Skill | Description |
|-------|-------------|
| **building-rust-crates** | Rust crate setup, testing, and publishing — Cargo layout, a fmt/clippy(`-D warnings`)/test CI gate, MSRV pinning, feature-flag hygiene, no-`unwrap`-in-libraries, and crates.io publishing with cargo-release |

### Scala

| Skill | Description |
|-------|-------------|
| **building-scala-projects** | Scala project setup, testing, and publishing — sbt build layout, scalafmt/scalafix gates, Scala 2-vs-3 cross-building, real (non-no-op) test jobs, and Maven Central publishing via sbt-ci-release |

### Common (language-agnostic)

| Skill | Description | Based On |
|-------|-------------|----------|
| **keeping-git-repos-clean** | Prevent, detect, and remediate committed secrets and dev artifacts — .gitignore, `git rm --cached`, history scrubbing, credential rotation. Bundled into every language's plugin. | [Guide to Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) |

## Plugin Bundles

### Per-language

- **python-library-complete** — all Python skills, plus the web-app architecture and MCP-server skills and git hygiene, for comprehensive Python development.
- **go-projects** — `building-go-projects` + `keeping-git-repos-clean`.
- **swift-apps** — `building-swift-apps` + `keeping-git-repos-clean`.
- **rust-crates** — `building-rust-crates` + `keeping-git-repos-clean`.
- **scala-projects** — `building-scala-projects` + `keeping-git-repos-clean`.

### Narrower Python bundles

- **python-library-foundations** — project setup, code quality, testing strategy.
- **python-library-distribution** — packaging, release management, CLI development.
- **python-library-quality** — security audit, performance, API design, git hygiene.
- **python-web-app** — web-app architecture (FastAPI, async SQLAlchemy, Stripe, Docker/Terraform deployment).
- **python-mcp-servers** — MCP servers (FastMCP tool design, error contracts, packaging, testing, prompt-injection awareness).

Every language bundle includes **keeping-git-repos-clean** — committed-secret and dev-artifact hygiene applies regardless of language.

## Usage

Once installed, Claude will automatically use these skills when you ask about:

- Setting up a new project (Python, Go, Rust, Scala) or a Swift/Xcode app
- Wiring a CI pipeline whose gate actually gates
- Adding tests, publishing packages, or reviewing code quality
- Security scanning and keeping secrets out of git
- Architecting a Python web app or building a Python MCP server
- And more...

## Contributing

Contributions are welcome! Please open an issue or PR on [GitHub](https://github.com/wdm0006/python-skills).

## License

MIT License - see [LICENSE](LICENSE) for details.
