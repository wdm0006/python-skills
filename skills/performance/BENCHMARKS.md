# Benchmarking & Regression Testing

Deep dive on measuring performance repeatably and preventing regressions in CI. A benchmark you don't compare against a baseline is just a number.

## Contents

- [pytest-benchmark](#pytest-benchmark)
- [Groups & parametrization](#groups--parametrization)
- [Comparing runs](#comparing-runs)
- [Guarding against regressions in CI](#guarding-against-regressions-in-ci)
- [timeit for micro-benchmarks](#timeit-for-micro-benchmarks)
- [airspeed velocity (asv)](#airspeed-velocity-asv)

## pytest-benchmark

```bash
uv add --dev pytest-benchmark
```

The `benchmark` fixture calls the target repeatedly, discards warmup, and reports a statistical distribution (min/mean/median/stddev/ops) rather than a single timing.

```python
def test_encode(benchmark):
    result = benchmark(encode, 37.7749, -122.4194)
    assert len(result) == 12  # correctness still asserted
```

Pass arguments through the fixture, not via a lambda, so setup stays out of the timed region:

```python
def test_encode_kwargs(benchmark):
    result = benchmark(encode, lat=37.7749, lon=-122.4194)
```

Use `pedantic` mode when you need explicit control over rounds, iterations, or per-round setup (e.g. a fresh input each round):

```python
def test_decode_pedantic(benchmark):
    benchmark.pedantic(decode, args=("9q8yyk8ytpxr",), rounds=100, iterations=10)
```

Run only benchmarks (normal test runs skip the timing overhead by default):

```bash
uv run pytest tests/ --benchmark-only     # run just benchmarks
uv run pytest tests/ --benchmark-skip     # skip them in the normal suite
```

Reading the table: `Min` is the most stable single figure (least contended by the OS), `Mean`/`Median` show typical cost, `StdDev` flags a noisy measurement, and `OPS` (operations/sec) is the throughput view. Prefer `Min` or `Median` over `Mean` when the machine is noisy.

## Groups & parametrization

Group related benchmarks so pytest-benchmark prints a side-by-side comparison and relative multipliers within the group:

```python
import pytest

@pytest.mark.benchmark(group="encode")
def test_encode_v1(benchmark):
    benchmark(encode_v1, 37.7749, -122.4194)

@pytest.mark.benchmark(group="encode")
def test_encode_v2(benchmark):
    benchmark(encode_v2, 37.7749, -122.4194)
```

Parametrize to see how cost scales with input size:

```python
import pytest

@pytest.mark.parametrize("n", [10, 100, 1000])
def test_bulk_encode(benchmark, n):
    points = [(37.7749, -122.4194)] * n
    benchmark(bulk_encode, points)
```

`--benchmark-group-by` regroups the report by `group`, `param`, `func`, or a combination (e.g. `--benchmark-group-by=param`).

## Comparing runs

Persist results, then diff a later run against them.

```bash
# Save this run under a named baseline (also autosaves to .benchmarks/)
uv run pytest tests/ --benchmark-only --benchmark-save=baseline

# Later, compare the current run against the most recent saved run
uv run pytest tests/ --benchmark-only --benchmark-compare

# Compare against a specific saved run by name or number
uv run pytest tests/ --benchmark-only --benchmark-compare=baseline
```

Inspect saved runs directly without re-running:

```bash
uv run pytest-benchmark list                 # list stored runs
uv run pytest-benchmark compare 0001 0002    # diff two stored runs
```

Saved runs live under `.benchmarks/` as JSON, keyed by machine and commit — commit these or store them as CI artifacts to build history.

## Guarding against regressions in CI

Make the build fail when a benchmark slows past a threshold. `--benchmark-compare-fail` takes a column and a tolerance; `min:5%` means fail if the minimum is more than 5% slower than the baseline.

```bash
uv run pytest tests/ --benchmark-only \
  --benchmark-compare \
  --benchmark-compare-fail=min:5%
```

Absolute thresholds work too (`mean:0.001` fails if mean regresses by more than 1ms). Typical CI flow:

```bash
# 1. On the base branch / main, save a baseline (restored from cache or artifact)
uv run pytest tests/ --benchmark-only --benchmark-save=main

# 2. On the PR, run and fail on a >10% median regression vs that baseline
uv run pytest tests/ --benchmark-only \
  --benchmark-compare=main \
  --benchmark-compare-fail=median:10%
```

Practical notes: pin the runner (benchmarks are meaningless across heterogeneous CI hardware), keep the tolerance loose enough to absorb runner noise (5–10%), and cache/restore `.benchmarks/` between jobs so the baseline persists. Use `--benchmark-disable-gc` for steadier numbers.

## timeit for micro-benchmarks

For a one-off snippet where a full pytest benchmark is overkill, `timeit` is the stdlib answer. It disables the GC and loops enough times to get a stable figure.

```bash
# Auto-picks loop count; -s is setup that runs once and isn't timed
uv run python -m timeit -s "from mymod import encode" "encode(37.7749, -122.4194)"
```

In code, `repeat` gives several samples — take the minimum, since higher numbers are just interference:

```python
import timeit

samples = timeit.repeat(
    stmt="encode(37.7749, -122.4194)",
    setup="from mymod import encode",
    repeat=5,
    number=10000,
)
print(min(samples) / 10000)  # seconds per call
```

Keep setup in the `setup` argument so import and construction costs stay out of the timed loop. Use timeit for comparing two implementations of a tiny expression; use pytest-benchmark when you want assertions, grouping, and regression tracking.

## airspeed velocity (asv)

For tracking performance across your commit history over time (not just pass/fail in one CI run), asv runs a benchmark suite against many git commits and publishes an interactive HTML dashboard of trends — the standard tool for library-wide performance history.

```bash
uv add --dev asv
uv run asv run                 # benchmark the current commit
uv run asv run HASH1..HASH2    # benchmark a range of commits
uv run asv continuous main HEAD  # compare two commits, flag regressions
uv run asv publish             # build the trend dashboard
uv run asv preview             # serve it locally
```

Benchmarks live in a `benchmarks/` directory as timing (`time_*`), memory (`mem_*`/`peakmem_*`), or tracking (`track_*`) methods on classes. Reach for asv when you want a long-run performance graph across releases; pytest-benchmark remains the better fit for per-PR regression gating.
