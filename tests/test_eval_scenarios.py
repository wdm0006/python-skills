import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
EVALS = ROOT / "evals"
SCHEMA_VERSION = 1
MIN_PROMPTS = 2


def skill_names():
    names = set()
    for skill_file in (ROOT / "skills").glob("*/*/SKILL.md"):
        match = re.match(r"---\n(.*?)\n---\n", skill_file.read_text(), re.DOTALL)
        field = re.search(r"^name:[ \t]*(.+)$", match.group(1), re.MULTILINE) if match else None
        if field:
            names.add(field.group(1).strip())
    return names


def nonempty_strings(value):
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def scenario_errors(data, known_skills):
    errors = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    skill = data.get("skill")
    if skill not in known_skills:
        errors.append(f"unknown skill: {skill!r}")
    positives = data.get("positive_prompts")
    if not nonempty_strings(positives) or len(positives) < MIN_PROMPTS:
        errors.append(f"positive_prompts needs {MIN_PROMPTS}+ non-empty strings")
    negatives = data.get("negative_prompts")
    if not isinstance(negatives, list) or len(negatives) < MIN_PROMPTS:
        errors.append(f"negative_prompts needs {MIN_PROMPTS}+ entries")
    else:
        for entry in negatives:
            if not isinstance(entry, dict) or not nonempty_strings([entry.get("prompt")]):
                errors.append(f"negative prompt needs a non-empty prompt: {entry!r}")
                continue
            expected = entry.get("expected_skill")
            if expected not in known_skills:
                errors.append(f"negative prompt names unknown skill: {expected!r}")
            elif expected == skill:
                errors.append(f"negative prompt must name a different skill: {expected!r}")
    rubric = data.get("rubric")
    if not nonempty_strings(rubric) or not rubric:
        errors.append("rubric needs 1+ non-empty strings")
    return errors


class EvalScenarioTests(unittest.TestCase):
    def test_scenario_files_are_valid(self):
        files = sorted(EVALS.glob("*.json"))
        self.assertGreaterEqual(len(files), 3)
        known = skill_names()
        for path in files:
            with self.subTest(file=path.name):
                data = json.loads(path.read_text())
                self.assertEqual(scenario_errors(data, known), [])
                self.assertEqual(path.stem, data["skill"])

    def test_validator_rejects_bad_scenarios(self):
        known = {"alpha", "beta"}
        good = {
            "schema_version": 1,
            "skill": "alpha",
            "positive_prompts": ["a", "b"],
            "negative_prompts": [{"prompt": "c", "expected_skill": "beta"}] * 2,
            "rubric": ["x"],
        }
        self.assertEqual(scenario_errors(good, known), [])
        bad = {
            "skill": dict(good, skill="missing"),
            "empty rubric": dict(good, rubric=[]),
            "blank rubric item": dict(good, rubric=["  "]),
            "one positive": dict(good, positive_prompts=["a"]),
            "unknown neighbour": dict(good, negative_prompts=[{"prompt": "c", "expected_skill": "nope"}] * 2),
            "self neighbour": dict(good, negative_prompts=[{"prompt": "c", "expected_skill": "alpha"}] * 2),
            "bad version": dict(good, schema_version=2),
        }
        for label, data in bad.items():
            with self.subTest(case=label):
                self.assertTrue(scenario_errors(data, known))


if __name__ == "__main__":
    unittest.main()
