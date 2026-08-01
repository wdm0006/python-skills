---
name: running-resumable-sync-jobs
description: Design and review long-running batch or sync jobs that process many items against a remote API and persist checkpoint state — exit codes that report partial failure, checkpoints that are safe to resume, per-item tolerance vs. fatal abort, telling "zero" apart from "couldn't fetch", bounded retries, honest dry-runs, and compensating reserved resources. Use when writing or reviewing a mirror/sync command, a nightly cron job, an importer, a paginated fetcher, or a background worker that consumes quota.
---

# Running Resumable Sync Jobs

A sync job is a loop over N items against a service that will fail partway
through. Everything hard about these jobs is what happens on item K of N: what
the process reports, what it wrote down, and what the *next* run does with that.
Get the happy path right and you still ship a job that silently under-collects,
double-applies, or bills for work it never did.

## The exit code is the only thing automation reads

The most common failure: per-item errors are printed as warnings, the loop
`continue`s, and the run finishes by saving state, committing, printing
"Sync complete!" and returning success. A cron wrapper, a CI step, or a
supervisor sees exit 0 and reports a healthy job forever.

```python
# Bad — the warning goes to a log nobody reads; the process says "fine".
for user in users:
    try:
        mirror(user)
    except MirrorError as e:
        print(f"Warning: failed to mirror {user}: {e}")
        continue
save_state(); commit(); print("Sync complete!")
return 0

# Good — failures are counted and surfaced in the status the caller can act on.
failed = []
for user in users:
    try:
        mirror(user)
    except MirrorError as e:
        log.error("failed to mirror %s: %s", user, e)
        failed.append(user)
save_state()           # keep the work that succeeded
if failed:
    log.error("%d of %d targets failed: %s", len(failed), len(users), failed)
    return 1           # or 2, if you want "partial" distinguishable from "total"
return 0
```

Continuing past a failure is usually right — you want the other 99 items. What
is never right is continuing *and* claiming success. If partial success must be
acceptable to the caller, make it an explicit opt-in (`--allow-partial`), not the
default silence.

## Checkpoint what actually happened, not what you attempted

Resumable jobs record "item X is done" so the next run skips it. Two ways that
record goes wrong, and both are worse than no checkpoint at all:

**Attempted-but-unfinished recorded as done.** State is saved for everything
processed before the failure, so the next run skips those and the post-failure
items stay pending forever — and because the run exited 0, nothing ever says so.
This is the exit-code bug above compounding into permanent data loss.

**Finished-but-not-recorded.** A batch applies its units one at a time
(N commits, N rows, N API calls) and the helper returns only an error when unit
K fails — no count of the K−1 that landed. The caller leaves that item's state
untouched, so the next run recomputes the *whole* delta and re-applies the units
that already succeeded. Every retry over-applies.

```python
# Bad — the caller learns nothing about how far the batch got.
def apply_batch(units) -> None:
    for u in units:
        apply(u)            # raises on failure; K-1 side effects already landed

# Good — report progress alongside the failure so state can advance.
def apply_batch(units) -> int:
    """Returns the number of units successfully applied."""
    applied = 0
    for u in units:
        try:
            apply(u)
        except Exception:
            raise PartialBatch(applied) from None
        applied += 1
    return applied
```

Either report the partial count and check it in, or make the unit of work atomic
(one transaction, one commit) so "some of it happened" is not a reachable state.
Pick one deliberately; the default — raise and discard the count — is the bug.

## Per-item tolerance must be decided *before* the shared error handler

Jobs accumulate a shared `handle_api_error(response)` helper. These are almost
always **fatal by default**: unknown status → log and exit. That is the right
default for a single-target command and the wrong one for a loop over 900 items,
where one deleted account should skip one item.

The trap is that the skip branch looks present but is dead:

```python
# Bad — handle_api_error raises SystemExit on any non-200, so the skip below
# is unreachable. One 404 aborts the run after 800 successful calls and
# writes no output at all.
r = get(f"/users/{login}")
if r.status_code != 200:
    signal = handle_api_error(r)
    if signal == "retry":
        continue
    log.warning("Skipping user %s due to error", login)   # never runs
    skipped += 1
    continue
```

Branch on the cases you tolerate *before* delegating:

```python
if r.status_code != 200:
    if is_rate_limited(r):
        handle_api_error(r)      # shared wait/retry policy
        continue
    log.warning("Skipping %s: HTTP %s", login, r.status_code)
    skipped += 1
    continue
```

Then report `skipped` in the summary. Two more rules that fall out of this:

- **Grep for other callers** when you change a shared handler's contract. A
  helper that is fatal-by-default with one tolerant caller is a helper whose
  other callers are all one bad row away from discarding a full run.
- **Write output incrementally, or before enrichment.** A job that fetches a
  list, enriches every element, then writes one file at the end loses everything
  to a failure in the last element. Persist the cheap list first.

## Distinguish "zero" from "couldn't fetch"

Aggregators fold a failed fetch into the output as a plausible number. This is
the quietest bug in the whole category, because the artifact looks complete.

```python
# Bad — a rate-limited or transient clones fetch is written out as a confident 0
# and flows into the printed total.
row = {"views": views["count"], "clones": clones.get("count", 0) if clones else 0}

# Good — unknown stays unknown, and the run says how much it lost.
if clones is None:
    incomplete.append((repo, "clones"))
    row["clones"] = None          # or omit the row entirely
```

Related: a run that treats only *some* failures as decisive is inconsistent by
construction. If a `None` from fetcher A increments `skipped` and `continue`s,
but a `None` from fetchers B and C is silently coerced to 0 and dropped from the
aggregate, the trailing "skipped: M" line under-reports and the totals are wrong
in a direction no reader can detect.

**Cross-check totals against detail when the source gives you both.** If a page
publishes "1,759 contributions in 2024" and your parser extracts zero rows, that
is a parse failure, not an empty year. A positive summary with an empty detail
set must raise; zero-or-absent summary with an empty detail set is a valid empty
result.

## Bound every retry, and count per unit of work

A `continue` on a "retry" signal, inside a pagination loop, with no counter,
re-requests the same page forever against a persistent 403 or 429. The job does
not crash — it hangs, which no timeout-free supervisor will ever notice.

```python
MAX_RETRIES = 5

retries = 0                       # per page, not per run
while True:
    r = get(url, params={"page": page})
    if is_rate_limited(r):
        if retries >= MAX_RETRIES:
            return items, False   # partial + incomplete flag; warn loudly
        wait_for_reset(r)
        retries += 1
        continue
    retries = 0                   # reset after any success
    ...
```

Counting **per unit of work** and resetting after a success is what lets a long
multi-page fetch ride out repeated rate limits while still bounding retries of a
single stuck page. A per-run counter kills legitimate long jobs; no counter hangs
forever.

**Write down whose job the waiting is.** If the shared handler already slept
until the reset timestamp before returning `"retry"`, a caller that adds its own
`sleep(60)` double-waits — a bug that is invisible in output and only shows up as
a job that takes twice as long as it should. Document the contract once ("the
wait already happened; re-request now") and hold every new caller to it.

## Incremental cursors: re-include the boundary

A job that stores `last_sync` as a timestamp but compares at day granularity
loses the boundary day permanently:

```python
# Bad — skips days <= since. Anything that happened later on the same calendar
# day as the last sync is never re-fetched, and that day's count freezes.
if day_date <= since:
    continue

# Good — truncate the cursor to the comparison's granularity and re-include the
# boundary. Merging is keyed by date, so re-processing that day is idempotent.
if day_date < since.date():
    continue
```

The general rule: an incremental cursor must be exclusive only at the exact
granularity it is stored at. If your merge step is keyed and idempotent — and it
should be — re-processing the boundary unit costs nothing and closes the hole.

## Dry-run must perform every in-memory mutation the real run does

Gate persistence and external side effects. Never gate the in-memory state
changes the preview loop reads, or the preview describes a different job than the
one that will run.

```python
# Bad — under --dry-run the counters are never cleared, so the preview computes
# incremental deltas and reports "nothing to do", while a real --rebuild would
# re-apply the entire history.
if rebuild and not dry_run:
    state.clear_all_progress()

# Good — clear in memory always; only the write is gated.
if rebuild:
    state.clear_all_progress()
...
if not dry_run:
    save_state(state)
    rewrite_history()
```

Also make destructive scope explicit in the preview. A `--rebuild` that recreates
history by removing every tracked file is correct only in a dedicated
single-purpose repo; run it where other content lives and it deletes that too.
Say what will be removed, not just what will be added.

## Compensate reserved resources when the work never happens

Jobs that consume quota, credits, or seats reserve *before* doing the work — the
right order, since the alternative is unbounded free work. The reservation itself
should be a single conditional update, which is race-free and needs no lock:

```sql
UPDATE subscriptions SET usage = usage + 1
 WHERE id = :id AND usage < :limit      -- rowcount == 0 → over quota → 429
```

What is usually missing is the compensating path. Every one of these charges the
customer for nothing: the enqueue after the reservation raises; the job
dead-letters after its retries; the job record expires and the worker returns
without even dead-lettering. On a small plan, one blip is a double-digit
percentage of the month.

```sql
UPDATE subscriptions SET usage = usage - 1
 WHERE id = :id AND usage > 0           -- never goes negative
```

Three details that make refunds safe:

- **Record which period you reserved against** and skip the refund if the
  subscription has since rolled over — otherwise a late refund decrements a
  freshly-zeroed counter and grants free work.
- **Take bare identities, not a request-scoped auth object**, so the background
  worker can call the same function the request path does.
- **Refund on every terminal non-completion**, including the paths that look like
  nothing happened: the worker's missing-record branch should dead-letter rather
  than bare-return, so it is a failure you can see and act on.

## Testing these paths

- **Assert the exit code**, not just stdout. A test that only checks for a
  warning string passes on the version that exits 0.
- **Record sleep durations, don't stub them away.** `monkeypatch.setattr(mod,
  "sleep", sleeps.append)` lets you assert the exact sequence
  (`assert sleeps == [reset_wait, 0.1]`), which is what catches a redundant extra
  wait. A no-op `lambda _s: None` cannot.
- **Make the error persistent** when testing a retry cap: serve a reusable
  error response and assert the request count for the stuck page. Also match on
  the response *body* if that is what your handler branches on — status alone may
  not select the branch you think.
- **A missing cap makes the suite hang, not fail.** Run the mutated suite under
  an external timeout; no output within N seconds *is* the reproduction.
- **Test the resume, not just the run.** Fail item K, then run again against the
  same state and assert the remaining items are attempted and the completed ones
  are not re-applied. A single-run test cannot see either checkpoint bug.

## Checklist

- [ ] Non-zero exit (or an explicit `--allow-partial`) when any item failed
- [ ] Failure count and the failing identifiers appear in the final summary
- [ ] Checkpoints record only completed work; partial batches report their count
- [ ] Per-item tolerance branches *before* the shared, fatal-by-default handler
- [ ] Skip/dead branches verified reachable (grep the handler's other callers)
- [ ] Output written incrementally, or the cheap pass persisted before enrichment
- [ ] Failed fetches are `None`/absent in the artifact, never a coerced `0`
- [ ] Summary-vs-detail contradiction raises instead of returning empty
- [ ] Every retry loop is bounded, counted per unit, and reset after a success
- [ ] The "who waits" contract is documented and no caller double-sleeps
- [ ] Incremental cursor re-includes the boundary unit; merge is idempotent
- [ ] Dry-run mutates in-memory state identically; only writes are gated
- [ ] Reservations have a compensating, period-guarded, non-negative refund
- [ ] Tests assert exit codes, sleep sequences, request counts, and a resumed run

Related: **improving-python-code-quality** for making in-process errors visible
at the call site, and **testing-python-libraries** for proving a regression test
can actually fail.
