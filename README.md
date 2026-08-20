# Developer Skills for Claude Code

A growing, multi-language set of opinionated, checklist-driven Claude Code skills for professional software development. It began as a Python library-development toolkit (based on the guide at [mcginniscommawill.com](https://mcginniscommawill.com/guides/python-library-development/)) and now also covers Go, Swift/Apple apps, Rust, Scala, and browser extensions. Install only the languages and bundles that make sense for you.

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

# Swift / Apple platforms — Xcode build & CI, signing, Keychain, CloudKit/SwiftData, TestFlight releases
/plugin install swift-apps@dev-skills

# Swift releases — TestFlight and App Store delivery
/plugin install shipping-swift-apps@dev-skills

# Rust — Cargo layout, fmt/clippy/test gate, MSRV, crates.io publishing
/plugin install rust-crates@dev-skills

# Scala — sbt build, scalafmt/scalafix gates, cross-building, Maven Central
/plugin install scala-projects@dev-skills

# Browser extensions — Manifest V3 service workers, chrome.storage safety, Jest chrome mocks
/plugin install browser-extensions@dev-skills
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

# LLM-backed Python features
/plugin install python-llm-features@dev-skills
```

Or install a language-agnostic bundle:

```
# Resumable batch and synchronization jobs
/plugin install resumable-sync-jobs@dev-skills

# Verify third-party libraries, APIs, build backends, and scraped documents
/plugin install verifying-external-behavior@dev-skills

# Build and verify release artifacts
/plugin install shipping-build-artifacts@dev-skills

# Reproduce CI failures locally
/plugin install reproducing-ci-locally@dev-skills

# Keep user-facing facts consistent across product surfaces
/plugin install shipping-across-surfaces@dev-skills

# Compute and report statistics, scores, and flags honestly
/plugin install reporting-derived-metrics@dev-skills
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
| **building-python-web-apps** | Opinionated reference architecture for production web apps — FastAPI, async SQLAlchemy/Postgres, centralized bcrypt password limits, fail-closed distributed auth rate limiting, Stripe billing, Jinja or SPA frontends, and Dockerized deployment via Terraform | Production web app patterns |
| **building-python-mcp-servers** | Robust Python MCP servers with FastMCP — tool design, error contracts, event-loop-safe blocking work, CLI/subprocess wrapping, single-file vs packaged distribution, testing, and prompt-injection awareness | [Guide to Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) |
| **building-llm-backed-features** | Application features on top of an LLM API — prompt surfaces that drift apart, filtered evaluator sets that cannot silently become clean passes, config wiring validated at boot, live-model tests kept out of CI, stochastic accuracy evaluation, and output that doesn't over-claim | [Guide to Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) |

### Go

| Skill | Description |
|-------|-------------|
| **building-go-projects** | Go project setup with a CI gate that actually gates — module-path correctness, golangci-lint config matched to the installed major, deterministic gofmt, pinned toolchain, meaningful test/lint jobs, injectable git/gh runners, and safe outbound HTTP |

### Swift / Apple Platforms

| Skill | Description |
|-------|-------------|
| **building-swift-apps** | Native Swift/SwiftUI apps for macOS/iOS — unsigned CI builds (`CODE_SIGNING_ALLOWED=NO`), the hand-maintained pbxproj, SwiftPM-vs-app-target test boundaries, SourceKit false positives, gitignored base xcconfig, Keychain vs UserDefaults + OAuth state/PKCE, CloudKit/SwiftData constraints, and deterministic dates/RNG |
| **shipping-swift-apps** | Releasing to TestFlight and the App Store — one App Store Connect API key for both fastlane and `xcodebuild`, metadata/pricing lanes that can't submit a build, headless `archive` + `-exportArchive destination=upload`, build numbers read from the API instead of guessed, closed pre-release trains, `SKIP_INSTALL` for bundled helper apps, per-destination archives for multiplatform targets, and keeping `.p8`/`.env` credentials ignored |

### Rust

| Skill | Description |
|-------|-------------|
| **building-rust-crates** | Rust crate setup, testing, and publishing — Cargo layout, a fmt/clippy(`-D warnings`)/test CI gate, MSRV pinning, feature-flag hygiene, no-`unwrap`-in-libraries, and crates.io publishing with cargo-release |

### Scala

| Skill | Description |
|-------|-------------|
| **building-scala-projects** | Scala project setup, testing, and publishing — sbt build layout, scalafmt/scalafix gates, Scala 2-vs-3 cross-building, real (non-no-op) test jobs, and Maven Central publishing via sbt-ci-release |

### JavaScript / Browser Extensions

| Skill | Description |
|-------|-------------|
| **building-browser-extensions** | Manifest V3 extensions — service-worker message channels and `chrome.*` side effects that survive teardown (`return true` + awaited responses), tests that gate the final side effect instead of an upstream promise, `??`-based numeric settings reads (`0` is a valid hour), lost-update-safe `chrome.storage` writes over defaults, JS-side settings validation (inert HTML `min`/`max`), and a Jest chrome mock that can actually fail |

### Common (language-agnostic)

| Skill | Description | Based On |
|-------|-------------|----------|
| **rendering-untrusted-content** | Render stored/authored/imported content into HTML without shipping XSS — enumerating autoescape bypasses (`\|safe`, `Markup`, `innerHTML`), sanitizing Markdown output with an allowlist (Markdown preserves raw HTML by design), keeping table-cell `style` so alignment survives, escaping on both the server and the DOM, and sanitization tests that assert on the rendered prose rather than the JSON-LD copy | — |
| **keeping-git-repos-clean** | Prevent, detect, and remediate committed secrets and dev artifacts — .gitignore, `git rm --cached`, history scrubbing, credential rotation. Bundled into every language's plugin. | [Guide to Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) |
| **running-github-actions-efficiently** | Build GitHub Actions workflows that gate the intended work — focused triggers, pinned toolchains, explicit permissions, reproducible local commands, and jobs that fail when their checks fail | — |
| **verifying-external-behavior** | Confirm what a third-party library, remote API, build backend, or scraped document actually does before depending on it — throwaway probes that run in seconds, permissive clients that forward a misspelled selector instead of rejecting it, status codes that differ between the collection and item forms of a resource, summary response shapes that make a "we already have it" fast path always-false, fakes that only prove your code calls the fake, and dry-runs that skip the step that fails | — |
| **shipping-build-artifacts** | Make the build step a real gate on what you distribute — build scripts that warn and exit 0 on a missing input, size checks with only an upper bound, hand-maintained file lists that drift from the entrypoints they must cover, committed bundles that go stale when only the source changes, GNU-only shell that aborts on the other OS, and verification that runs against the source tree instead of the artifact | — |
| **running-resumable-sync-jobs** | Batch/sync jobs that fail honestly — exit codes that report partial failure, checkpoints safe to resume, per-item tolerance vs. fatal abort, unknown-vs-coerced-`0` in aggregated output, bounded per-page retries, dry-runs that mutate in-memory state identically, and compensating reserved quota | — |
| **reproducing-ci-locally** | Make the local check agree with the runner — deriving the command, paths, marker expression and `env:` from the workflow file rather than the Makefile, running each gate step separately because the first failure hides the rest, pinning the linter version CI resolves (an unpinned formatter that widens file coverage reddens every open PR), building the interpreter and extras the runner builds, fixing divergence in shared config rather than in the YAML, and confirming a run is green instead of explaining a red job away | — |
| **reporting-derived-metrics** | Compute statistics, scores, and flags from samples that may be too small to support them — undefined dispersion returned as `0.0` and tripping the minimum threshold it is compared against (the least data producing the strongest verdict), `None` vs `0`/`-1`/`NaN` as the sentinel, threshold blocks gated on whether the value was measured, report sentences that narrate findings from absent data, nullability as a public API change, `is None` vs truthiness when `[]`/`0` are real results, and broad excepts that disguise a metric bug as a normal-shaped result | — |
| **shipping-across-surfaces** | Land a change everywhere the same fact is stated — enumerating the surface inventory (landing copy, structured data, docs, `llms.txt`, changelog plus the version badge repeated in every page's nav, sitemap, README, descriptions embedded in code, and untyped frontend consumers of typed responses), generating a surface instead of restating it, drift tests that compare against the live registry rather than a second hand-written list, never hand-maintaining a snapshot of a surface another codebase owns, paired producer/consumer PRs for format changes, and keeping overloaded product words apart | — |

## Plugin Bundles

### Per-language

- **python-library-complete** — all Python skills, plus the web-app architecture and MCP-server skills and git hygiene, for comprehensive Python development.
- **go-projects** — `building-go-projects` + `keeping-git-repos-clean`.
- **swift-apps** — `building-swift-apps` + `shipping-swift-apps` + `keeping-git-repos-clean`.
- **shipping-swift-apps** — TestFlight/App Store releases on their own (App Store Connect API key auth, fastlane metadata lanes, headless archive and upload, build-number and version-train rules) for when the build side is already sorted.
- **rust-crates** — `building-rust-crates` + `keeping-git-repos-clean`.
- **scala-projects** — `building-scala-projects` + `keeping-git-repos-clean`.
- **browser-extensions** — `building-browser-extensions` + `shipping-build-artifacts` + `rendering-untrusted-content` + `keeping-git-repos-clean`.

### Narrower Python bundles

- **python-library-foundations** — project setup, code quality, testing strategy.
- **python-library-distribution** — packaging, release management, CLI development, build-artifact shipping.
- **python-library-quality** — security audit, performance, API design, untrusted-content rendering, external-behavior verification, git hygiene.
- **python-web-app** — web-app architecture (FastAPI, async SQLAlchemy, Stripe, Docker/Terraform deployment) + untrusted-content rendering.
- **python-mcp-servers** — MCP servers (FastMCP tool design, error contracts, event-loop-safe blocking work, packaging, testing, prompt-injection awareness).
- **python-llm-features** — LLM-backed features (prompt surfaces, structured outputs, context budgeting, model config wiring, accuracy evaluation).

### Language-agnostic

- **resumable-sync-jobs** — batch/sync jobs, cron tasks, importers, and paginated fetchers (partial-failure exit codes, resumable checkpoints, bounded retries, quota compensation).
- **verifying-external-behavior** — integrating a dependency, endpoint, or build backend (probe the exact call, inspect outbound parameters, validate fakes against the real service, skip the dry-run shortcut).
- **shipping-build-artifacts** — build/package scripts, `dist/` copy steps, committed compiled assets, and release workflows that upload a zip or installer (fail on missing inputs, bound size both ways, rebuild-and-diff committed bundles, verify the artifact before publishing).
- **reproducing-ci-locally** — running the CI gate on your machine so it agrees with the runner (workflow-derived commands and markers, short-circuiting gate steps, pinned linter versions, the runner's interpreter and extras, confirming green).
- **reporting-derived-metrics** — scoring and analysis pipelines, z-score/outlier checks, quality and anomaly flags, and metrics rollups (unmeasurable is not zero, gate the threshold on whether the value was measured, never narrate a finding from absent data).
- **shipping-across-surfaces** — landing a user-facing change everywhere the same fact is stated (surface inventory, typed-response/untyped-consumer contract tests, generated instead of restated surfaces, drift tests against the live registry, cross-repo format contracts and direction of ownership, overloaded product terms).

Every language bundle includes **keeping-git-repos-clean** — committed-secret and dev-artifact hygiene applies regardless of language.

## Usage

Once installed, Claude will automatically use these skills when you ask about:

- Setting up a new project (Python, Go, Rust, Scala) or a Swift/Xcode app
- Wiring a CI pipeline whose gate actually gates
- Adding tests, publishing packages, or reviewing code quality
- Shipping an Xcode app to TestFlight or the App Store
- Security scanning and keeping secrets out of git
- Architecting a Python web app or building a Python MCP server
- And more...

## Contributing

Contributions are welcome! Please open an issue or PR on [GitHub](https://github.com/wdm0006/python-skills).

## License

MIT License - see [LICENSE](LICENSE) for details.
