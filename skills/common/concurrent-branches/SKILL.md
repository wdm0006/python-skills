---
name: merging-concurrent-branches
description: Resolve conflicts between sibling branches that were opened against the same base without silently dropping work — identifying the registry files every feature PR appends to, unioning manifest and catalog entries instead of picking a side, re-deriving version bumps and other monotonic counters from the current base rather than merging them as text, taking the base's copy of shared tool config and re-applying only your delta, merging test modules instead of clobbering them, catching the duplicate-helper class of clean-but-wrong merges, and re-running the full gate on the resolution. Use when rebasing or merging a branch whose base has moved, resolving conflicts in a manifest/README/version/lockfile/test file, reviewing a PR that was rebased, or working in a repo where several PRs are open at once.
---

# Merging Concurrent Branches

When several branches are open against the same base at once, they do not collide
randomly. They collide in the same handful of files every time — the manifest that
registers a feature, the version number, the keyword list, the README table, the
dependency block, the one test module everybody adds cases to. Those files are
*registries*: append-only lists that every change touches by construction.

The failure mode is not the conflict. It's the resolution. `--ours` on a manifest
is textually valid, produces a clean tree, and passes every test — while deleting
the sibling PR's entry. Nothing goes red, because "one fewer registered feature"
and "one fewer test" are not failure signals in any gate.

## Write down the hotspot list

For any repo with more than one branch in flight, the conflict set is knowable in
advance. Enumerate it once, in `CONTRIBUTING.md` or the repo's own guide:

- The **registry/manifest** that makes a feature discoverable — plugin lists,
  entry-point tables, route registries, `__init__` re-exports
- The **version field**, and anything else that is a monotonic counter
- **Catalog prose** that restates the registry — the README table, a docs index
- The **dependency block** and its lockfile
- **Shared tool config** — the `[tool.*]` sections, the CI workflow, the linter
  config
- The **shared test module** for the component everyone is extending

Knowing the list turns resolution from improvisation into a checklist. It also
tells you, before you start, which conflicts need a *semantic* resolution rather
than a textual one — every item above does.

## Registries: union both sides, never pick one

The default instinct on a conflicted list is to keep the side you understand.
That is always wrong for a registry.

```
# Bad — clean tree, green build, sibling PR's feature is now unregistered
git checkout --ours manifest.json
```

Keep every entry from both sides, in a stable order:

```jsonc
// Resolution keeps BOTH new entries and BOTH new keywords
{
  "keywords": ["existing", "from-ours", "from-theirs"],
  "features": [
    "./features/existing",
    "./features/from-ours",
    "./features/from-theirs"
  ]
}
```

Then verify the union against the filesystem rather than by eye: every registered
path exists, and every feature directory is registered. A registry entry pointing
at nothing and a directory nobody registered are the two symptoms of a side-pick,
and both are cheap to assert in a test.

The same rule covers catalog prose. If the README lists what the manifest
registers, the resolution has to add both rows — and the row count should match
the registry count.

## Monotonic values are re-derived, not merged

A version bump is not text with two candidate values. Each sibling PR that merges
ahead of you *consumes* an increment, so both sides of the conflict are stale by
the time you resolve it.

```
# Bad — keeps "2.4.0" or "2.5.0" from the diff; base is already at 2.6.0
# Good — read the base, then bump from there
git fetch origin
git show origin/main:manifest.json | grep version   # -> 2.6.0
# resolution: 2.7.0
```

This generalizes to migration numbers, changelog entry ordering, fixture IDs, and
any "next N" allocated at authoring time. If your branch reserved a number, treat
it as a *claim*, not a fact, and re-check the claim at merge time.

## Shared config: take the base's file, re-apply your delta

Tooling config accumulates on the base while your branch is open. Your branch's
copy is a snapshot of an older base plus your one addition. Restoring that
snapshot silently reverts every sibling's config change — dropping a pytest
option, a lint rule, or a dev dependency that other merged work now depends on.

```
# Take the base's version wholesale, then re-add only what your branch introduced
git checkout --theirs pyproject.toml     # or: git checkout origin/main -- pyproject.toml
# now hand-add your branch's new dependency / config line to that file
```

Read the resulting diff against the base, not against your branch. It should
contain exactly your change and nothing else. Anything else in it is a revert you
did not intend.

## Test modules: merge the suites

Two branches each appending cases to the same test file conflict on the closing
region, and a side-pick deletes the other branch's coverage. Nothing catches it:
a suite with fewer tests still exits 0.

Keep the base's tests and layer yours on top, then check the count moved the way
you expect:

```
git checkout origin/main -- tests/test_component.py   # base's suite, intact
# re-apply your branch's new test functions into it
pytest tests/test_component.py --collect-only -q | tail -1   # count == base + yours
```

Duplicate test *names* are the other half of this: two branches often invent the
same obvious name for different cases, and in most runners the second definition
silently shadows the first. Grep the merged file for repeated `def test_` names.

## A clean merge is not a correct merge

Git merges by line, not by meaning. The most common semantic collision is two
branches independently adding the same helper to a module — different hunks, no
conflict, two definitions after the merge. The first one is dead code, and edits
to it do nothing.

Linters are less help here than you'd expect: a redefinition rule may exempt
private, underscore-prefixed names by default, which is exactly what an internal
helper is called. Check by hand after any resolution in a module both branches
touched:

```
grep -n '^def \|^class ' module.py | awk '{print $2}' | sort | uniq -d
```

Same shape, different file: the same dependency added at two different pins, the
same constant defined twice, the same route registered on two paths.

## The resolution is a commit no CI run has ever seen

A rebase produces new content. Neither branch's green run covers it, and the
merge-queue check that runs after you push is the *first* look anyone has at it.
Reproduce the repo's full gate locally on the resolved tree before pushing — the
whole gate, not just the tests, since a resolution routinely reintroduces a
formatting nit or a lint error the base had already fixed.

If the repo's gate short-circuits (lint before format-check, for example), run
each step separately so a first failure doesn't hide the second.

## Your knowledge of a file expires while your branch is open

If a sibling PR rewrote the module your work is built on, the notes you took
before the rewrite describe code that no longer exists — and confidently
proposing a change to a function that was deleted is worse than having no notes.
After any rebase onto a moved base, re-read the current file before continuing,
and treat pre-rewrite observations about its internals as void.

```
git log --oneline main -- path/to/module.py   # did it move under you?
git show origin/main:path/to/module.py        # what does it say now?
```

## Shrink the collision surface

The durable fix is to stop making every change touch the same file:

- **Generate the catalog** from the registry instead of hand-maintaining a second
  list. One less file to union.
- **One entry per file** where the format allows it (a directory of fragments
  assembled at build time) turns a guaranteed conflict into no conflict.
- **Assert the invariant** the union has to satisfy — registry ⊆ filesystem and
  filesystem ⊆ registry — so a dropped entry fails a test instead of shipping.
- **Bump the version in one place**, derived at release time from the base, not
  edited in every feature PR.

## Checklist

- [ ] The repo's conflict hotspots are written down, not rediscovered per PR
- [ ] Every conflicted registry/manifest resolution keeps **both** sides' entries
- [ ] Registry entries and on-disk files agree in both directions after resolving
- [ ] Catalog prose (README table, docs index) unioned to match the registry
- [ ] Version and other monotonic values re-derived from the **current base**
- [ ] Shared tool config taken from the base, with only your delta re-applied
- [ ] Diff reviewed against the base — it contains your change and nothing else
- [ ] Test modules merged, not side-picked; collected test count moved as expected
- [ ] No duplicate top-level `def`/`class`/test names after the merge
- [ ] Full local gate re-run on the resolved tree, each step separately
- [ ] Files rewritten by sibling PRs re-read before building on them

Related: **improving-python-code-quality** for why a duplicated private helper
slips past the linter, **reproducing-ci-locally** for running the real gate on a
resolution, and **shipping-across-surfaces** for generating a catalog instead of
maintaining a second copy of it.
