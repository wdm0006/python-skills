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

### Pin the linter version and don't trust the capped issue list

- `version: latest` on the action only tracks the newest release of the major
  the *action* supports. A workflow on an old action major silently keeps
  installing an end-of-life linter, and the resolved version appears only in the
  run log (`gh run view <id> --log | grep -i golangci`), never in the workflow.
  Pin an explicit `version: vX.Y.Z` and commit a `.golangci.yml` that names the
  enabled linters (`default: none` + explicit `enable`), so the gate is recorded.
- golangci-lint caps repeats of one finding (`max-same-issues`, default 3), so a
  red run that lists three `errcheck` hits may have dozens. Run `errcheck ./...`
  (or set `issues.max-same-issues: 0` while fixing) and clear them all, or the
  rest resurface next run. Bare calls to `(T, error)` functions in `_test.go`
  benchmarks are the usual bulk.
- A branch cut before a lint fix landed on the base fails lint on a clean,
  unrelated diff. Compare with a two-dot diff against the remote base
  (`git diff origin/main`), then rebase rather than re-fixing the file.
- staticcheck SA4026: Go's `-0.0` literal is *positive* zero. For a negative-zero
  test input use `math.Copysign(0, -1)`.

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

## Dry-run must simulate state transitions, not skip them

A dry-run should suppress external writes, not the in-memory changes used to
decide what would be written. Gating a preparatory state transition on
`!dryRun` makes the preview compute from stale state and under-report the real
operation:

```go
// BAD — dry-run previews incremental work, while the real rebuild clears state
// first and performs the full operation.
if opts.Rebuild && !opts.DryRun {
    state.ClearProcessed()
    rewriteHistory()
}
work := plan(state)
```

Split simulation from side effects. Apply the same in-memory transition in both
modes, and gate only persistence or destructive external operations:

```go
if opts.Rebuild {
    state.ClearProcessed() // changes planning only; safe in memory
    if !opts.DryRun {
        rewriteHistory()
    }
}

work := plan(state)
if !opts.DryRun {
    execute(work)
    save(state)
}
```

Test preview fidelity by starting from identical state and comparing the planned
items from dry-run with the items attempted by a real run using a recording fake.
Also assert that dry-run performed no filesystem, network, or subprocess writes.
Do not settle for testing only that it "didn't write": a quiet dry-run that
reports the wrong plan is still broken.

## Bound text without splitting UTF-8

Go string indexes and slices are byte-based. A limit such as `body[:500]` can
cut through a multi-byte code point, producing invalid UTF-8 that is later
replaced, rejected, or corrupted when sent as JSON. This commonly appears when
bounding API response bodies, changelog excerpts, or LLM context.

If the limit is a byte budget, retreat to the previous rune boundary:

```go
func truncateUTF8(s string, maxBytes int) string {
    if maxBytes <= 0 {
        return ""
    }
    if len(s) <= maxBytes {
        return s
    }

    end := maxBytes
    for end > 0 && !utf8.RuneStart(s[end]) {
        end--
    }
    return s[:end]
}
```

This assumes the input string is valid UTF-8; validate untrusted raw bytes at
the ingestion boundary. If the product requirement is a character limit rather
than a byte limit, truncate by runes instead. Keep one shared limiter for every
path that constructs the same kind of context so one caller cannot remain
unbounded while another truncates.

Test the boundary with multi-byte text, not only ASCII:

```go
func TestTruncateUTF8DoesNotSplitRune(t *testing.T) {
    got := truncateUTF8("abc🙂def", 5) // the emoji occupies bytes 3..6
    if got != "abc" || !utf8.ValidString(got) {
        t.Fatalf("got %q, want valid UTF-8 %q", got, "abc")
    }
}
```

## Numeric input: `ParseFloat` accepts NaN/Inf, and `switch` can't see NaN

`strconv.ParseFloat` happily returns `NaN`, `+Inf` and `-Inf` for the strings
`"NaN"`, `"inf"`, `"-Infinity"`, with a nil error. Finite inputs can also
overflow to `Inf` during arithmetic. Neither value survives `encoding/json`
(`json: unsupported value`), and some web frameworks swallow that error and send
an empty-body 200. Validate at both ends — the parsed value and the computed
result — and return an error rather than a non-finite number:

```go
func finite(x float64) (float64, error) {
    if math.IsNaN(x) || math.IsInf(x, 0) {
        return 0, fmt.Errorf("non-finite result: %v", x)
    }
    return x, nil
}
```

`NaN != NaN`, so `switch p { case 0: … case 1: … }` silently falls through for a
NaN exponent into whatever the default/tail path is. Guard with `math.IsNaN`
*before* any switch or early return (including an empty-input early return, or
an invalid parameter is accepted whenever the data happens to be empty).

Related numeric traps:

- Summing squares overflows long before the true result does; prefer `math.Hypot`
  or scale by the max magnitude, then rescale. General-power accumulation
  underflows to `0` the same way. Assert these with *relative* error — a fixed
  absolute tolerance accepts a wrong zero.
- Validate **every** element of an auxiliary slice (weights, variances), not just
  the prefix a `for i := range vec` loop reaches; otherwise whether the caller
  gets an error depends on the length of an unrelated vector.
- `-0.0` in Go source is *positive* zero (and trips staticcheck SA4026). Build a
  negative zero with `math.Copysign(0, -1)`.
- If `+` must survive a query parameter, remember `url.Query()` decodes it to a
  space; test explicit-sign parsing at the parser level, not through the handler.

## Mutation-testing a Go guard: the build can fail instead of the test

To prove a test catches a deleted guard, you mutate the guard and expect a
`--- FAIL`. In Go the mutation can instead break the *build*: neutering
`if math.IsNaN(x) { … }` to `if false { … }` can leave the `math` import unused,
and `go test` reports `imported and not used` with no test failures at all. A
`grep -c -- '--- FAIL'` then reads 0, which looks like a surviving mutant. Keep
the identifiers referenced — `if false && math.IsNaN(x) {` — and check that the
output contains a FAIL line, not just that the count changed.


## Linters that cap their own output

golangci-lint reports at most 3 identical issues by default
(`max-same-issues: 3`), so a red run listing three `errcheck` hits can hide
dozens. Before fixing "the 3 shown", run `errcheck ./...` (or set
`issues.max-same-issues: 0` temporarily) and fix them all, or the rest resurface
one run at a time. Benchmarks and tests count: calling a `(T, error)` function as
a bare statement in `*_bench_test.go` fails `errcheck` — use `_, err := f()` and
`b.Fatal`. A branch cut before a lint fix landed on the base fails on files its
own diff never touched; diff two-dot against the base tip and rebase rather than
re-fixing.

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

Three details that bite in practice:

- **A UA is not cosmetic.** Some hosts answer the default `Go-http-client` agent
  with a 403, so the failure looks like an auth or outage problem. Send a
  descriptive one.
- **Pin `Accept-Language` when a parser matches display text.** A prose regex
  (`N items on …`) is only valid for the locale it was written against;
  without the header, a localized response parses to zero matches with no error.
  Set `req.Header.Set("Accept-Language", "en-US,en;q=0.9")`. Pinning narrows the
  hazard, it does not remove it — prefer a machine-readable attribute
  (`data-date`, a JSON endpoint) when the source offers one.
- **Hold the client in a package-level `var`** (`var httpClient = &http.Client{...}`)
  so tests can swap its transport for an `httptest` server and assert the headers
  and timeout were actually set.

Regex/markup-based scraping is inherently fragile — a timeout + UA is the
minimum robustness; treat parse failures as errors, not silent empties. If you
add a "parsed zero results" guard, test it against a *captured real page*: a
sanity check that looks for a total on one line (`([\d,]+) items`) never
fires when the live markup wraps that total across indented lines, so it only
ever triggers on hand-written fixtures.

## Checklist

```
Go project health:
- [ ] go.mod module path == canonical repo URL; internal imports match
- [ ] go directive, setup-go version(s), and CI matrix all consistent
- [ ] gofmt run under the same version setup-go installs (reformat committed once)
- [ ] .golangci.yml version key matches the installed golangci-lint major (v1: none; v2: "2")
- [ ] golangci-lint `version:` pinned to an explicit release; errcheck run uncapped before declaring lint clean
- [ ] golangci-lint-action version paired with the config lane; timeout in run.timeout, not args
- [ ] test job actually has *_test.go files with assertions (race gate isn't a no-op)
- [ ] no map ranged directly into serialized/committed output (sort first)
- [ ] dry-run applies planning-state transitions and suppresses only external writes
- [ ] bounded text is truncated on UTF-8 rune boundaries through one shared helper
- [ ] git/gh wrappers depend on an injectable Runner, not os/exec + stderr string-matching
- [ ] outbound HTTP sets Timeout and User-Agent (and Accept-Language if parsing display text)
```
