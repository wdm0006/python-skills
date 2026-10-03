---
name: permissioning-ci-workflows
description: Give a CI job exactly the credentials it needs and know when it has none — declaring `permissions:` explicitly because the default GITHUB_TOKEN scope is a repo setting, reading the 403's x-accepted-github-permissions header instead of guessing the missing scope, one API call needing two scopes, a fork pull request getting a read-only token and no repository secrets, event-conditioned steps that skip on the re-run and turn a job green without fixing it, why `pull_request_target` is not the workaround, and preferring a check that needs no credential at all. Use when a workflow step comments on a PR, pushes a commit, opens an issue, uploads a report, calls another repository's API, or fails 403 while every build and test step passes.
---

# Permissioning CI Workflows

A job that only reads code and runs tests needs no thought about credentials. The
moment a step comments on a pull request, pushes a commit, opens an issue,
uploads a report, or calls another repository's API, it depends on two things
that are invisible in the YAML: **which scopes the token carries**, and **whether
the run was allowed to have secrets at all**.

Both fail in the same shape — every build, lint, and test step green, one
trailing step red — which is why they get re-run instead of fixed.

For the cost side of workflows (triggers, concurrency, caching, matrix), see
**[running-github-actions-efficiently](../github-actions/SKILL.md)**. This skill
is about what a workflow is *allowed* to do.

## Declare permissions; never inherit them

The default `GITHUB_TOKEN` permission set is a repository/organization setting
(permissive vs. restricted), not a property of your YAML. Identical workflow
files therefore behave differently across repos and across orgs — and a repo that
tightens the default later breaks a workflow nobody touched.

Declare a read-only floor at workflow level and grant writes per job:

```yaml
permissions:
  contents: read          # floor for every job in this workflow

jobs:
  test:
    runs-on: ubuntu-latest
    # inherits contents: read — nothing else

  comment:
    runs-on: ubuntu-latest
    permissions:          # REPLACES the workflow-level set, does not merge
      contents: read
      issues: write
      pull-requests: write
```

A `permissions:` block sets every scope you did not name to `none`, and a
job-level block **replaces** the workflow-level set rather than merging with it.
That is the point at workflow level and the trap at job level: restate every
scope the job needs, not only the one you came to add.

## One API call can need two scopes

Scopes do not map one-to-one onto endpoints. The clearest case: commenting on a
pull request goes through the **issues** API
(`POST /repos/{owner}/{repo}/issues/{number}/comments`), and because a pull
request is an issue *and* a pull request, the token check requires
`issues: write` **and** `pull-requests: write`. With only the first it returns
403 after everything else in the run has already passed.

Do not guess the missing scope from the endpoint's noun. The 403 response names
what it will accept:

```console
$ gh api -i repos/OWNER/REPO/issues/123/comments -f body=probe
HTTP/2.0 403
x-accepted-github-permissions: issues=write; pull_requests=write
```

Read that header out of the failing run's log, or reproduce the single call with
`gh api -i` against a scratch resource. It is a one-line answer to a question
that otherwise costs a round of guess-and-push.

## The failure hides behind the step's own condition

Steps that write to a PR are usually gated on the event that should trigger them:

```yaml
- name: Comment on PR
  if: github.event.action == 'opened'
  uses: actions/github-script@v7
```

Pushing a commit to that PR re-runs the workflow as `synchronize`. The step is
skipped, the job goes green, and the permission was never granted — so the next
PR fails identically and the fix looks like it landed.

Any red check whose step is event-conditioned is not verified by pushing a
commit. Re-verify it on the event that runs it: a fresh PR, a `workflow_dispatch`
path, or a temporary condition change reverted in the same PR. A green run that
skipped the step under test is the same defect as a test that never asserted —
see **[writing-defect-reports](../defect-reports/SKILL.md)** on not filing a red
gate as an aside.

## A fork pull request has a read-only token and no secrets

On `pull_request` from a fork, `GITHUB_TOKEN` is read-only **regardless of your
`permissions:` block**, and repository and organization secrets are not passed
into the run. This is not configurable per workflow, and it is correct: a
contributor you have never met is proposing code that your runner is about to
execute.

The consequence is that every credentialed gate — a cross-repo API read, a
registry publish, a report upload, a comment — does nothing on exactly the
contributions you control least. Worse, the usual workaround makes it invisible:

```yaml
# BAD — on a fork PR this is green and verified nothing.
- name: Validate against the upstream registry
  if: ${{ secrets.REGISTRY_TOKEN != '' }}
  env:
    TOKEN: ${{ secrets.REGISTRY_TOKEN }}
  run: ./scripts/validate.sh
```

Split the check by what it needs instead of skipping it by what it has:

- The half that needs **no external truth** — schema, structure, denylists of
  known-bad patterns, anything decidable from files in the repo — must run on
  every PR, standalone, with a read-only token. Land that half first; it is a
  real gate on day one.
- The half that needs a credential runs where credentials exist: post-merge on
  `push`, on a schedule, or in a `workflow_run` triggered by the completed PR
  build.

Then say which is which in the contributing docs, so a fork PR going green is not
read as full verification.

## `pull_request_target` is not the workaround

`pull_request_target` runs in the **base** repository's context: writable token,
full secrets, and the workflow file from the base ref. That is what makes it
useful for labeling and greeting — and what makes this catastrophic:

```yaml
# BAD — hands a writable token and every secret to whoever opened the PR.
on: pull_request_target
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with: { ref: ${{ github.event.pull_request.head.sha }} }
      - run: npm ci && npm test        # executes the contributor's code
```

Any step that runs head-ref content under `pull_request_target` — a build, a
dependency install with lifecycle scripts, a test, a linter with a repo-local
plugin — executes untrusted code with your credentials in the environment. Use
`pull_request_target` only for steps that never execute head content: labels,
greetings, size and metadata checks done through the API.

## Prefer a check that needs no credential at all

Every credentialed check is one that cannot run on a fork, cannot run offline,
and breaks when the token rotates. Before granting a scope, ask whether the check
needs the network at all.

- **When the truth lives in another repository**, do not have this repo reach in.
  Have the owning repo *publish* it outward as a generated, versioned artifact
  that the consumer commits and validates against — the consumer's check then
  needs no token, runs on forks, and states which upstream version it was
  checked against. See
  **[shipping-across-surfaces](../cross-surface-changes/SKILL.md)** on never
  hand-maintaining a snapshot of a surface you don't own.
- **Never hand-maintain the allowlist instead.** Copying another system's valid
  values into a constant in this repo removes the token and keeps the coupling,
  with nothing to detect drift.
- **Coverage and quality reports** that exist only behind a third-party upload
  token vanish on fork PRs and during that service's outages. Run the tool in the
  job and print the report into the log (`--cov-report=term-missing` or the
  equivalent), so the number is in the run everyone can already read.

## Checklist

```
Scopes:
- [ ] Every workflow declares permissions explicitly; none rely on the repo default
- [ ] Workflow-level floor is read-only; writes granted per job
- [ ] Job-level permissions blocks restate contents: read (they replace, not merge)
- [ ] Missing scope taken from the 403's x-accepted-github-permissions, not guessed
- [ ] PR-comment steps carry issues: write AND pull-requests: write

Forks:
- [ ] Known which gates do nothing on a fork PR (read-only token, no secrets)
- [ ] Credential-free half of each gate runs standalone on every PR
- [ ] No step silently skipped on an empty secret and reported as passing
- [ ] pull_request_target used only for steps that never run head-ref content

Verification:
- [ ] Event-conditioned steps re-verified on the event that runs them, not by a push
- [ ] Green run confirmed to have actually executed the step, not skipped it
- [ ] Checks that could be decided from repo contents don't take a token
```
