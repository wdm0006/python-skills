# Skill evaluation scenarios

One JSON file per skill, recording what a correct activation and a correct run look like. This directory is a pilot (three skills). There is no runner and nothing here calls a model; `trial.py` below records and reports a reviewer's observations; `tests/test_eval_scenarios.py` validates the files structurally.

## File format (`schema_version` 1)

File name: `<skill name>.json`, where the name is the skill's frontmatter `name`.

```json
{
  "schema_version": 1,
  "skill": "<frontmatter name of the skill under evaluation>",
  "positive_prompts": ["request that should activate this skill", "..."],
  "negative_prompts": [
    {"prompt": "neighbouring request", "expected_skill": "<frontmatter name of the skill that should handle it>"}
  ],
  "rubric": ["observable artifact or command a correct run produces", "..."]
}
```

Rules enforced by the test:

- `positive_prompts`: at least 2 non-empty strings.
- `negative_prompts`: at least 2 entries; `expected_skill` must be an existing skill other than `skill`.
- `rubric`: at least 1 non-empty string. Each item must be observable (a file, a command and its result, a report section), not a judgement like "code is good".
- `skill` must match an existing `SKILL.md` frontmatter `name`.
- Prompts are generic: no real project, repository or incident names.

Bump `schema_version` for any change that alters how a file must be read.

## How a future runner will consume these

1. For each file, present every prompt to an agent with the full skill catalog installed and record which skill activated. Positive prompts must activate `skill`; each negative prompt must activate its `expected_skill`, not `skill`. This scores the `description` only.
2. For positive prompts, run the agent in a scratch project and check the `rubric` items against the resulting files and command transcript. This scores the procedure.

The two scores should be reported separately and versioned with the model and catalog commit. Live-model runs are opt-in and must stay out of default CI.

## Scratch fixtures for procedure trials

`evals/fixtures/<fixture-id>/` holds a small, versioned set of starting projects so reviewers run a procedure trial on the same inputs. Each has `fixture.json` (metadata) and `files/` (the starting tree). Scenario files above are unchanged (schema version 1); a fixture refers to its scenario by file name, the exact prompt text and the exact rubric item text.

| Fixture | Skill | Prompt (exact) |
|---|---|---|
| `setup-clean-parent` | `setting-up-python-libraries` | Create a new Python library called acme-utils with pytest, ruff and CI ready to go. |
| `security-inert-examples` | `auditing-python-security` | Audit my Python library for security vulnerabilities before we release. |
| `ci-gate-mismatch` | `reproducing-ci-locally` | The lint job fails in CI but passes on my machine; help me reproduce it locally. |

All other prompts remain activation-only; they have no procedure fixture yet. The insecure code in `security-inert-examples` is inert: never called, no payloads, no credentials. Do not import or run it.

### Manual trial workflow

1. Materialize into a NEW directory outside this checkout (existing destinations and unknown or unsafe fixture ids are refused before anything is written; nothing is executed or installed):

   ```bash
   uv run --no-project --python 3.12 python evals/fixtures/materialize.py ci-gate-mismatch /tmp/trial-ci-1
   ```

   It prints the fixture id and `tree_sha256`.
2. Follow the fixture's `setup` list, give the agent the `prompt` verbatim with the skill installed, and let it work in that directory.
3. Compare the result with the fixture's `expected_observations` and score the listed `rubric_items` from the resulting files and transcript. For `setup-clean-parent`, assess the generated child directory against those scaffold rubric items.
4. Record with the trial: fixture id, `tree_sha256`, the catalog commit, the agent client and model version, and which rubric items were observed, not observed, or not assessable. Worksheets and reports (proposed separately) can adopt these fields unchanged.

### Fixture validation is not agent success

`tests/test_eval_fixtures.py` checks deterministic facts only: each prompt and rubric text still exists in its scenario, starting-file hashes are unchanged, the materializer is repeatable and refuses unsafe requests, and the `ci-gate-mismatch` reproduction behaves as documented (local command exits 0, the workflow command exits 1, aligned configuration plus the code fix exit 0, using pinned `ruff==0.9.10` through `uvx`; skipped when `uv` is absent). It never runs an agent. A passing suite says the inputs are intact, not that any skill works; no success rate is measured or claimed here. Changing a fixture file means regenerating its hashes in `fixture.json` and re-reading the affected trials.

## Trial worksheets and reports

`evals/trial.py` is a stdlib-only helper with two operations. It makes no network calls, launches no agent and executes nothing from a scenario.

```bash
# 1. Write an unscored worksheet to a NEW file outside evals/ (existing files are never overwritten)
uv run --no-project --python 3.12 python evals/trial.py init /tmp/trial-1.json \
  --trial-id trial-1 --client "<client and version>" --model "<model and version>" --reviewer "<name or handle>"

# 2. Edit the worksheet by hand while reviewing a trial (see below)

# 3. Validate and report (text by default; --check-current notes scenarios edited since the trial)
uv run --no-project --python 3.12 python evals/trial.py report /tmp/trial-1.json
uv run --no-project --python 3.12 python evals/trial.py report /tmp/trial-1.json --format json
```

`init` fills `trial_date` (today) and `catalog_commit` (`git rev-parse HEAD`) unless given as `--trial-date` / `--catalog-commit`. Provenance fields still empty are listed; `report` refuses a worksheet that lacks any of `trial_id`, `trial_date`, `catalog_commit`, `client`, `model`, `reviewer`. Keep worksheets out of `evals/` (it refuses that location) so they are never read as scenario files, and do not commit real transcripts.

The worksheet snapshots each scenario (content plus hashes) and assigns case ids `<skill>/p<N>` (positive prompt N) and `<skill>/n<N>` (negative prompt N). Reports read only that snapshot, so an old worksheet stays reportable after scenarios change.

Per case, set `activation`:

- `status`: `pending` (not yet recorded), `observed`, or `unobserved` (could not tell which skill activated).
- `activated_skills`: every skill you saw activate (list all of them; extra skills are kept and do not fail a case). Only with `observed`, which also needs `evidence` (a transcript excerpt or log reference).

For positive cases, set each rubric record's `status` to `pass`, `fail`, `not-applicable` or `unscored`. `pass`/`fail` need `evidence`; `not-applicable` needs `na_reason`. Rubrics are scenario-wide, so mark items a given prompt does not call for (for example CI artifacts when only a scaffold was requested) `not-applicable`.

Reading the report:

- Activation passes when a positive case shows the expected skill, or a negative case shows its `expected_skill` and not the skill under evaluation. `unobserved` and `pending` cases are never passes and are excluded from the observed denominator, with their counts shown.
- Procedure is summarised separately: scored items passed, passed out of all applicable items (unscored counts as not passed), failed, unscored, and not-applicable (visibly excluded). A case with unscored items and no failure is `incomplete`; a case with only not-applicable items is `undefined`.
- A zero denominator prints `undefined`, never 100%.
- Everything reported is what the reviewer recorded. It is not automatic proof of agent behavior, and one trial is not a success rate.

`tests/test_eval_trials.py` runs the helper on a mixed-result worksheet with exact expected counts. No model or network access is needed.
