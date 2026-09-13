---
name: reporting-derived-metrics
description: Compute statistics, scores, and flags from samples that may be too small to support them — undefined dispersion returned as 0.0 and tripping a minimum threshold, sentinel choice (None vs 0 vs NaN), threshold blocks gated on "was this measured", reports that narrate findings from absent data, nullability as a public API change, `is None` vs truthiness, broad excepts that turn a metric bug into a normal-shaped result, and heavy-tailed samples where the mean points the opposite way to the median. Use when writing or reviewing a scoring/analysis pipeline, a z-score or outlier check, a quality or anomaly flag, a metrics rollup, a benchmark or cohort comparison, or any function that reduces a list of observations to one number a threshold or a report reads.
---

# Reporting Derived Metrics

A derived metric is a number computed from a sample and then compared against a
threshold to produce a flag, a score, or a sentence a user reads as a finding.
The bugs are almost never in the arithmetic. They are at the two ends: what the
function returns when the sample is too small to support the statistic, and what
the flag layer does with that value.

## An undefined statistic is not zero

Dispersion — standard deviation, variance, coefficient of variation, burstiness,
mean gap between events — needs at least two observations. Ratios and rates need
a non-zero denominator. The reflex on the short-sample branch is `return 0.0`,
and that is the worst available answer, because `0` is a real and *extreme* point
on the same scale the threshold lives on.

Two shapes, both of which turn "no data" into a confident verdict:

- A **minimum threshold** (`variation < 2.5 → suspicious`) is tripped by `0.0`
  every single time. Any one-segment input is flagged, with a reason string that
  quotes a measurement that never happened: `low variation (0.00 < 2.5)`.
- A **z-score against a baseline** (`mean 7.1`, `sd 2.4`) scores `0.0` at
  `z = -2.96` — a hard outlier. The feature is reported as anomalous precisely
  when it was not measurable.

Note the direction: the *least* data produces the *strongest* verdict. Make
unmeasurable its own value.

```python
# Bad — 0.0 is indistinguishable from "genuinely no variation at all"
def dispersion(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)

# Good — the caller is forced to decide what "not measurable" means
def dispersion(values: list[float]) -> float | None:
    """Sample standard deviation, or None if fewer than two observations."""
    if len(values) < 2:
        return None
    return statistics.stdev(values)
```

Prefer `None` over the alternatives. `-1` is in-band for anything that can go
negative. `NaN` is worse than `0.0` in a subtle way: every comparison against it
is `False`, so it silently produces the mirror bug — a metric that can never trip
any threshold and never explains why.

## The threshold block needs its own "was this measured" gate

Returning `None` only relocates the bug unless every consumer is updated in the
same change. `None < 2.5` raises `TypeError`; `(value or 0) < 2.5` faithfully
reconstructs the original bug. Gate explicitly:

```python
measured = variation is not None

if measured and variation < cfg.variation_min:
    flags["suspicious"] = True
    reasons.append(f"low variation ({variation:.2f} < {cfg.variation_min})")
elif not measured:
    reasons.append("variation requires at least two scored segments")
```

Loops that walk a dict of features must **skip** the unmeasured ones, not
substitute for them:

```python
for name, value in features.items():
    if value is None:
        continue                     # absent from z_scores and from flags
    z_scores[name] = (value - baseline[name].mean) / baseline[name].sd
```

Substituting the baseline mean is the tempting alternative and it is wrong for
the same reason `0.0` was: it invents a perfectly average observation and reports
it as one you took.

## Don't narrate findings from data you don't have

The failure mode that survives longest is the report sentence. When every
per-segment score fails, the aggregate is `None`, and a flag block written as an
`if/elif` chain will still reach a branch like:

> Low variation (0.00 < 2.5) but acceptable score.

The score was not acceptable. It was absent. Two rules:

- **Every sentence in a report must name a value that was actually measured.**
  If a branch can be reached with its subject unmeasured, it is not a finding,
  it is a template.
- **An empty `reasons` list is itself a claim.** A result with no reasons reads
  as "nothing wrong". When a metric could not be computed, say so explicitly
  ("requires at least two scored segments") rather than emitting nothing.

## When the distribution defeats the summary

Everything above is about a sample too small to support a statistic. This is the
other axis: `n` is large, the statistic is well defined, and the *summary* still
misleads — because one observation carries it.

Reducing a heavy-tailed sample to a mean is how a comparison ends up pointing the
wrong way. Two cohorts, ~100 items each, several per-item features — and several
of the comparisons do not survive the swap from mean to median:

| feature     | mean A / mean B | median A / median B | mean says      | median says   |
| ----------- | --------------- | ------------------- | -------------- | ------------- |
| perplexity  | 333.9 / 96.2    | 42.5 / 80.1         | 3.5x higher    | 1.9x *lower*  |
| burstiness  | 837.2 / 24.6    | 99.4 / 58.3         | 34x higher     | 1.7x higher   |

The first row reverses outright; the second keeps its direction but collapses
from a decisive-looking 34x to a marginal 1.7x.

One degenerate item — a single value ~600x the cohort median — is enough to carry
the mean of a 100-item cohort past the other one. Write "A scores higher than B"
from that mean and the sentence is backwards for almost every item in the sample.

Four rules, plus two things that are expensive to learn the hard way:

- **Report `n`, median, and mean together**, always. Not one of them.
- **When the mean and the median disagree in direction, the disagreement *is* the
  finding.** It says the feature is outlier-driven. Do not resolve it by picking
  the summary that matches your hypothesis, and do not average it away — say the
  cohorts do not separate robustly on that feature.
- **A mean-based effect size is not a robustness claim.** Cohen's *d* is
  `(mean₁ − mean₂) / pooled_sd`; it inherits the exact sensitivity that produced
  the flip and reverses with it. If you need an effect size on a heavy-tailed
  feature, use a rank-based one (Mann–Whitney *U* / rank-biserial correlation) or
  a median difference with a bootstrap confidence interval.
- **Look at `max` and the top few values before you report anything**, and state
  whether you trimmed. "Mean excluding the top 1%" is a defensible figure;
  a mean whose provenance is one unexamined outlier is not.

```python
# Bad — one line, one number, and it can be the opposite of the typical case.
print(f"{feature}: A={statistics.mean(a):.2f} B={statistics.mean(b):.2f}")

# Good — n, both summaries, and the tail that decides which one to trust.
for label, xs in (("A", a), ("B", b)):
    top = sorted(xs, reverse=True)[:3]
    print(f"{feature} {label}: n={len(xs)} median={statistics.median(xs):.2f} "
          f"mean={statistics.mean(xs):.2f} top3={top}")
```

**The summary is only over the rows that actually loaded.** A streaming read that
aborts partway (a CSV field exceeding the parser's default field-size limit, a
truncated download) leaves a plausible-looking partial result, and pre-converted
copies of a large dataset frequently cover only a prefix of the groups while
still advertising a row count. Assert the expected row count — and the expected
number of distinct groups — before summarizing anything.

**A separation computed from hand-authored inputs measures your thresholds
against your own assumptions.** Feature dictionaries written to look "typical of
A" and "typical of B", fed to the same threshold function that classifies them,
produce a result that cannot fail. Accuracy claims need labeled real data; see
**building-llm-backed-features** for evaluation-set design.

## Nullability is a public API change, not an implementation detail

The moment a metric can be `None`, the field is `float | null` for everyone
downstream. That is a versioned surface: the response schema, the serializer, the
docs table, the renderer that calls `f"{value:.2f}"`, the rollup that calls
`sum()` over the column, and every consumer's tests. Land them together — see
**shipping-across-surfaces**. Picking the nullable type up front, before anything
consumes the field, is much cheaper than widening it later.

## Check `is None`, never truthiness

Once "unavailable" is representable, the availability check has to be exact.
`[]` from a genuinely empty collection, `0` from a real count, and `0.0` from a
real measurement are all successful results:

```python
# Bad — fires the "data unavailable" warning on a healthy zero
if not referrers:
    incomplete.append(repo)

# Good
if referrers is None:
    incomplete.append(repo)
```

The truthiness version is especially quiet because it usually ships green: test
fixtures that pass an empty list to represent "nothing to report" start
triggering the unavailable path, and nothing asserts that they don't. The same
applies to `payload.get("count", 0)`, which turns a missing key into a confident
zero.

## Recheck the guards a new gate makes redundant

Adding the `measured` gate changes what the surrounding conditions can be. A
measured dispersion implies at least two finite per-segment scores, which implies
the aggregate is finite — so an `isfinite(aggregate)` check added *inside* the
gated branch is inert code. Inert defensive checks are not free: they cost review
attention and advertise a failure mode that cannot occur. After adding a gate,
ask which existing conditions it now implies, and delete those.

The converse also holds: **a `None` check is not a type check.** A non-numeric
value still reaches `(value - mean)` and raises `TypeError`. If arbitrary values
can reach the metric layer, validate the type at the boundary rather than adding
guards one exception at a time.

## A broad `except` turns a metric bug into a normal-shaped result

Analysis entry points are often wrapped so a caller never sees a traceback:

```python
except Exception as e:
    return {"error": f"Analysis failed: {e}", "features": {}, "flags": {"suspicious": False}}
```

This shape is genuinely useful — it keeps a protocol boundary well-behaved — and
it is exactly why these bugs live for months. A `KeyError` from a mis-wired
config key, a `TypeError` from an unguarded feature value, and a real analysis
all return the same shape with default flags. Any test that asserts only on the
result's *shape* stays green through all three.

So: assert `"error" not in result` in every test that exercises the metric path,
and log the swallowed exception with a traceback rather than only folding its
`str()` into the payload.

## Testing

- **Fixture with a single observation**, plus a separate one with zero. Assert
  three things, not one: the metric is `None`, the flag is `False`, and the
  reason string explains why it was not measurable.
- **Choose fixture values where the buggy and fixed versions disagree.** Any
  two-or-more-observation sample returns the same number either way, so a
  "normal" fixture cannot see this bug at all.
- **Mutate in both directions.** Restore `return 0.0` — the single-observation
  flag test must fail. Separately, delete the `measured` gate while keeping the
  `None` return — the same test must fail again, for a different reason. One
  regression test that only catches one of the two leaves the other shippable.
- **Know which assertion each mutation trips.** Deleting the `None`-skip in a
  z-score loop fails the test on `"error" not in result` (the `TypeError` was
  swallowed into the error shape), not on the flag assertion. That is still a
  useful mutation signal, but read it as "the guard is load-bearing at a
  different layer" rather than assuming the flag logic is covered.
- **Test the all-inputs-failed path** end to end and assert that no reason
  mentions an acceptable or in-range value.

## Checklist

- [ ] Every statistic requiring N observations returns `None` below N, not `0.0`
- [ ] Sentinel is `None` — not `0`, `-1`, or `NaN` (which never trips anything)
- [ ] Threshold blocks gate on "measured"; unmeasured can never set a flag
- [ ] Feature loops skip `None` rather than substituting a mean or a default
- [ ] Every reason/finding string names a value that was actually measured
- [ ] Unmeasurable emits an explicit reason; `reasons == []` never means "absent"
- [ ] Nullable metric landed across schema, serializer, renderer, rollup, docs
- [ ] Availability checked with `is None`; `[]`/`0`/`0.0` treated as real results
- [ ] Guards made redundant by a new gate deleted; type validated at the boundary
- [ ] Every cross-sample comparison reports `n`, median and mean; a mean/median
      disagreement is reported as the finding, not resolved silently
- [ ] Effect sizes on heavy-tailed features are rank-based, and the row count the
      summary covers was asserted before summarizing
- [ ] Metric tests assert `"error" not in result`, not just the result's shape
- [ ] Single- and zero-observation fixtures assert value, flag, and reason
- [ ] Mutation-tested both ways: restore the `0.0` return, and drop the gate

Related: **running-resumable-sync-jobs** for the same unknown-vs-zero distinction
in fetched and aggregated data, **building-llm-backed-features** for why an empty
evaluator set is not a clean pass, and **testing-python-libraries** for proving a
regression test can actually fail.
