---
name: calibrating-thresholds-and-baselines
description: Check that a score-threshold-flag pipeline actually separates anything before you trust or tune it — reference constants that are hand-authored but formatted as measurements, a computed feature whose units do not match the constant it is compared against, per-class fire rates that expose a flag firing on nearly every item of both classes, rate features confounded by item length, confidence scores where one feature family contributes once per sub-feature, threshold sweeps hardcoded to one comparison direction and one statistic, and separating features that carry the decision from features that only populate a warning list. Use when writing or reviewing an anomaly detector, a quality or risk score, a fraud/abuse heuristic, a lint-style flag set, or any pipeline that z-scores features against stored baseline constants and emits flags.
---

# Calibrating Thresholds and Baselines

A scoring pipeline has three layers: features computed per item, reference
constants the features are compared against, and a flag/score layer that turns
the comparison into something a user reads. **reporting-derived-metrics** covers
the first layer — what a feature function returns when the sample is too thin to
support it. This skill covers the other two: where the constant came from, and
whether the flag it drives carries any information at all.

The failure mode is not a crash. It is a pipeline that runs clean, emits
confident-looking flags on every input, and nobody notices because no one ever
asked how often each flag fires per class.

## A committed baseline file is not a measurement

Baselines get checked in as JSON or a module constant and immediately start
reading as ground truth, because they have the shape of data:

```json
{
  "name": "general_prose",
  "created": "2023-09-04",
  "sample_size": 750,
  "features": {
    "avg_item_len": {"mean": 12.4, "sd": 5.1},
    "diversity":    {"mean": 0.61, "sd": 0.07},
    "rate_per_word":{"mean": 0.22, "sd": 0.05}
  }
}
```

Every number there is two significant figures, `sample_size` is a round 750, and
nothing in the repository produces the file. It was typed. Downstream, `z =
(value - 0.22) / 0.05` is reported to four decimals and quoted in an issue as
evidence.

Before trusting a stored baseline, ask four questions:

- **Is there a script in the tree that regenerates it?** If not, the constants
  are an author's estimate. Say so where they are defined, in a comment the next
  reader cannot miss.
- **What precision do they claim?** A `sd` of `0.05` quoted to two significant
  figures supports roughly one digit of z-score. Do not print `z = -3.5814`.
- **Is there a second copy?** Baselines are routinely duplicated as an in-code
  fallback next to the file they mirror. Two copies drift; make one import the
  other, or add a test that asserts they are equal.
- **What population is it supposed to describe**, and is it the population you
  are scoring? A baseline built from long-form documents applied to 150-word
  snippets is a different distribution, not a stricter one.

When you do regenerate a baseline from real data, commit the extraction script
alongside it and record the corpus, the filter, and the date in the file.

## The feature and the constant must be the same quantity

This is the highest-yield bug in the whole pipeline, and it does not look like a
bug — the arithmetic is correct end to end, the units just disagree.

```python
# Feature: marks per CHARACTER.
def mark_rate(text: str) -> float:
    return sum(c in MARKS for c in text) / len(text)

# Baseline: {"mean": 0.22, "sd": 0.05} — authored as marks per WORD.
z = (mark_rate(text) - baseline["mean"]) / baseline["sd"]
```

A per-character rate lands near `0.041` where a per-word rate lands near `0.219`.
The z-score is then about `-3.6` for essentially every input — against `-0.02` for
the quantity the constant actually describes — and the feature is reported as an
extreme outlier on 100% of items. The same defect arrives by a
second route — **length confounding** — where the units match but the
normalization does not: a per-item rate that falls as items get longer (distinct
values over total values, unique-token rates, any "new things per thing" measure)
compared against a constant derived from documents an order of magnitude longer
will sit far from the mean for reasons that have nothing to do with the property
being detected.

The shared tell is the same in both cases, and it is not a weird number — it is a
z-score that is **large and nearly constant across every input**. A feature that
genuinely discriminates has a z-score that moves. Before shipping any new
feature-plus-baseline pair, print the distribution of its z-score over a sample
of known-normal items and confirm it is centered near zero:

```python
zs = [z_score(feature(item), baseline) for item in known_normal_sample]
print(f"n={len(zs)} median={statistics.median(zs):+.2f} "
      f"min={min(zs):+.2f} max={max(zs):+.2f}")
# median well away from 0 with a narrow spread => units or population mismatch,
# not a detection.
```

## Per-class fire rates are the cheapest calibration probe you have

You do not need a tuned model, a new run, or a metrics framework to find a
worthless flag. If the pipeline persists per-item output, the fire rate of every
flag per class is a few lines over a file you already have:

```python
from collections import Counter

fires = {"known_normal": Counter(), "known_anomalous": Counter()}
for row in load_scored_items():          # one persisted record per item
    for name in row["warnings"] + row["errors"] + row["indicators"]:
        fires[row["label"]][name] += 1
```

Read the result as a table of `fired / total` per class, and apply one rule:

**A flag that fires on nearly every item of both classes carries zero
information, no matter how severe its name is.** `rate_per_word` at 487/500
normal and 463/500 anomalous is not a strict check; it is a constant, and its
presence in every report trains readers to ignore the whole list. The same is
true in reverse: a flag that fires 0/1000 has never been evidence for anything,
and its threshold has no support.

Two practical notes:

- **Read the persisted record's real shape, not the API's.** The serialized row
  and the public result object often nest differently — flags at the top level of
  the record but under a `flags` sub-dict in the response. A lookup against the
  wrong shape returns nothing and reads exactly like "no flags fired." Print one
  record's keys before writing the loop.
- **Surface these rates in the generated report.** If the fire rates only exist
  in an ad-hoc script, the next person tuning a threshold will not have them.

## Score composition: count each family once

A confidence score assembled by addition quietly weights whichever feature family
has the most members:

```python
# Bad — one anomalous category adds 0.1, but the *reason* is appended once,
# so eight anomalous categories silently contribute 0.8 under one label.
for category in categories:
    if is_anomalous(category):
        confidence += 0.1
if any(is_anomalous(c) for c in categories):
    indicators.append("category_anomalies")
```

The report then shows a single indicator next to a near-maximum score, and the
contribution is invisible to anyone reading it. Cap each family's contribution,
or emit one reason per increment so the arithmetic in the score matches the
narrative beside it. Log the per-indicator contributions when the score is built;
a score you cannot decompose cannot be tuned.

## Sweep every statistic a threshold reads, in both directions

A threshold sweep that hardcodes its comparison cannot evaluate half your
thresholds:

```python
# Bad — only expresses "high is anomalous".
def sweep(scores, labels, thresholds):
    return [(t, confusion(scores, labels, lambda s: s >= t)) for t in thresholds]

# Good — direction is an input, because some statistics are low-is-anomalous.
def sweep(scores, labels, thresholds, direction="high"):
    cmp = (operator.ge if direction == "high" else operator.le)
    return [(t, confusion(scores, labels, lambda s: cmp(s, t))) for t in thresholds]
```

And sweep **every statistic a threshold reads**, not only the headline score. A
maximum-value cutoff that fires on 0 of 1000 items is usually reported as "the
threshold is too loose" — but with no sweep over that statistic there is no
evidence about whether *any* cutoff separates the classes on it. Those are very
different findings, and only one of them justifies changing the number.

## Know whether the feature carries the decision or only the warning list

Before fixing a miscalibrated feature, find out what consumes it. Pipelines
usually have two tiers: a set of named indicators that move the score and the
final verdict, and a larger set of warnings/errors that are displayed but feed
nothing. A units fix on a feature in the second tier is worth making — the
warning list is what a reader uses to judge the result — but it **cannot** change
a single classification.

That means the confusion matrix before and after is byte-identical, and that is
the correct outcome. Say it in the change description, explicitly:

> `rate_per_word` populates the warning list only; no indicator reads it, so the
> confusion matrix is unchanged by design. The measurable effect is its warning
> rate dropping from 95% of all items to 7%.

Omit that sentence and a reviewer compares the matrices, sees no movement, and
reads a correct fix as a failed one. The inverse mistake is just as costly:
proposing a threshold change to a decision-carrying feature while only having
measured warning rates.

## Checklist

- [ ] Every stored baseline either has a regeneration script committed beside it,
      or a comment stating the constants are authored estimates
- [ ] No duplicate copy of a baseline that can drift from the file (or a test
      asserts the two are equal)
- [ ] Each feature's units verified against the units the constant describes,
      and the baseline population checked against the population being scored
- [ ] z-score distribution over known-normal items printed for every new
      feature/baseline pair; median near zero, spread non-trivial
- [ ] Per-class fire rate computed for every flag; none fires on ~all or ~none
      of both classes unexamined
- [ ] Fire rates surfaced in the generated report, not only in a scratch script
- [ ] Score contributions decomposable, each feature family counted once
- [ ] Threshold sweep supports both comparison directions and covers every
      statistic a threshold reads
- [ ] Each feature classified as decision-carrying or display-only, and an
      unchanged confusion matrix explained in the change description

## Learn More

- **reporting-derived-metrics** — what a feature function should return when the
  sample is too small, sentinel choice, and heavy-tailed cohort comparisons
- **writing-defect-reports** — establishing that a miscalibration reproduces at
  the layer a user sees before publishing it
