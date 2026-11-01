# Skill evaluation scenarios

One JSON file per skill, recording what a correct activation and a correct run look like. This directory is a pilot (three skills). There is no runner yet and nothing here calls a model; `tests/test_eval_scenarios.py` validates the files structurally.

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
