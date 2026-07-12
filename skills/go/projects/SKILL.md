---
name: building-go-projects
description: Sets up and maintains Go projects with a CI gate that actually gates — module-path correctness, golangci-lint config that matches the installed major version, deterministic gofmt, a pinned toolchain, and meaningful test/lint jobs. Use when creating a Go module, wiring GitHub Actions for Go, debugging a golangci-lint or gofmt CI failure on an unrelated PR, or reviewing a Go CLI that shells out to git/gh.
---

# Go Project Setup & CI

Go's CI is deceptively easy to get *green* and hard to get *correct*. The traps
below all share one failure mode: a job that reports success while proving
nothing, or a config that breaks on a PR that never touched it. Each rule here
comes from a real green-but-wrong (or red-on-unrelated-PR) gate.

## Module path must match the repo URL

`go.mod`'s `module` line and every internal import must use the path users
actually `go install`/`go get`. A stale owner or renamed repo compiles and tests
locally but breaks `go install github.com/<owner>/<repo>@latest` for everyone.

```
module github.com/owner/project   // MUST equal the canonical repo URL
```

When you rename it, rename every internal import ref too (`grep -rl old/path`).
It's a mechanical string rename; `go build`/`go vet`/`gofmt` stay clean after.

## Pin the toolchain — `GOTOOLCHAIN=auto` makes a version matrix lie

With the default `GOTOOLCHAIN=auto`, Go silently downloads and switches to the
version in `go.mod`'s `go` directive whenever the installed toolchain is older.
So a CI matrix of `['1.21','1.22','1.23']` against `go 1.24.2` in `go.mod` runs
**1.24.2 in every cell** — the matrix tests nothing it claims to.

Keep them consistent: the `go` directive, the `setup-go` version(s), and the
matrix must agree.

```yaml
# ci.yml — matrix versions must be >= the go.mod directive
strategy:
  matrix:
    go: ['1.24', '1.25']
steps:
  - uses: actions/setup-go@v5
    with: { go-version: '${{ matrix.go }}' }
```

**gofmt runs under the `setup-go` SDK version, not the runtime toolchain.** Even
if `go build`/`go test` auto-upgrade via `GOTOOLCHAIN`, `gofmt` uses whatever
`setup-go` installed. Bumping `setup-go` can change gofmt's output (e.g. newer
gofmt realigns single-line declarations), turning a formatting check red on a PR
that changed no code. Run `gofmt` locally under the *same* version CI installs,
commit the reformat once, and pin `setup-go` so it doesn't drift again.

## golangci-lint: the config's `version` key must match the installed major

golangci-lint's `lint` job fails at the `config verify` step — before a single
line is linted — when `.golangci.yml` doesn't match the installed major version.
The rule of thumb:

- **v1** (installed by `golangci-lint-action@v6`): **no** top-level `version:`
  key. Use `disable-all` / `exclude-use-default`. v1's schema rejects `version`
  as an unknown property.
- **v2** (installed by `golangci-lint-action@v8`): `version: "2"` (a quoted
  string), `linters.default: none`, `enable: [...]`. v1-only keys like
  `disable-all` fail verify.

A config with `version: 2` (numeric) plus v1-only keys fails verify on **both**
majors. Pick a lane and keep the action version and config in lockstep:

```yaml
# v2 lane
- uses: golangci/golangci-lint-action@v8
```
```yaml
# .golangci.yml (v2)
version: "2"
linters:
  default: none
  enable: [govet]
run:
  timeout: 5m   # v2 removed the --timeout CLI flag; set it HERE, not in args:
```

Do **not** pass `args: --timeout=...` to the v2 action — the flag was removed and
the job errors. Put the timeout under `run.timeout` in the config instead.

## A test job with no tests is a no-op gate

`go test -race ./...` exits 0 when there are zero `*_test.go` files. A repo can
advertise a race-detector CI job and have it prove nothing. Green here means
"nothing failed," not "behavior is verified."

Add real tests for the pure functions first — parsers, mappers, aggregators,
state counters are trivially unit-testable and give the gate teeth. If a `test`
job is the only quality gate, confirm it actually executes assertions, not just
that it's green.

## Deterministic output: never range a map into serialized output

Ranging a Go `map` yields keys in randomized order. Building a slice, JSON file,
or any committed/compared artifact by ranging a map produces a different byte
order every run — churny, unreviewable diffs (especially painful in a repo whose
value *is* clean history). Sort before emitting:

```go
keys := make([]string, 0, len(m))
for k := range m { keys = append(keys, k) }
sort.Strings(keys)
for _, k := range keys { /* emit m[k] in stable order */ }
```

## Shelling out to git/gh: inject a runner, don't string-match stderr

CLIs that wrap `git`/`gh` by exec'ing them and classifying failures with
`strings.Contains(stderr, "404")` / `"auth login"` are brittle (tool output
wording changes between versions) and effectively untestable — there's no seam
to inject a fake. Define a small runner interface so tests can supply canned
output and error paths:

```go
type Runner interface {
    Run(ctx context.Context, name string, args ...string) (stdout, stderr string, err error)
}
```

Depend on `Runner`, not `os/exec` directly. Prefer structured output where the
tool offers it (`gh api`, `--json`) over scraping human-readable stderr.

## Outbound HTTP: always set a timeout and User-Agent

Scrapers/clients built on the default `http.Get` have **no timeout** (a hung
peer hangs the process forever) and no `User-Agent` (some services throttle or
block that). Use an explicit client:

```go
client := &http.Client{Timeout: 15 * time.Second}
req, _ := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
req.Header.Set("User-Agent", "project/1.0 (+https://github.com/owner/project)")
resp, err := client.Do(req)
```

Regex/markup-based scraping is inherently fragile — a timeout + UA is the
minimum robustness; treat parse failures as errors, not silent empties.

## Checklist

```
Go project health:
- [ ] go.mod module path == canonical repo URL; internal imports match
- [ ] go directive, setup-go version(s), and CI matrix all consistent
- [ ] gofmt run under the same version setup-go installs (reformat committed once)
- [ ] .golangci.yml version key matches the installed golangci-lint major (v1: none; v2: "2")
- [ ] golangci-lint-action version paired with the config lane; timeout in run.timeout, not args
- [ ] test job actually has *_test.go files with assertions (race gate isn't a no-op)
- [ ] no map ranged directly into serialized/committed output (sort first)
- [ ] git/gh wrappers depend on an injectable Runner, not os/exec + stderr string-matching
- [ ] outbound HTTP sets Timeout and User-Agent
```
