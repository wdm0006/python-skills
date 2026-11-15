import contextlib
import copy
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "evals" / "trial.py"
spec = importlib.util.spec_from_file_location("eval_trial", SCRIPT)
TRIAL = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = TRIAL
spec.loader.exec_module(TRIAL)

PROVENANCE = {
    "trial_id": "trial-a",
    "trial_date": "2026-01-02",
    "catalog_commit": "abc1234",
    "client": "example-client 1.0",
    "model": "example-model 1",
    "reviewer": "reviewer-1",
}
SETUP = "setting-up-python-libraries"
SECURITY = "auditing-python-security"


def case(ws, case_id):
    return next(c for c in ws["cases"] if c["case_id"] == case_id)


def observe(ws, case_id, skills, evidence="transcript line"):
    case(ws, case_id)["activation"] = {"status": "observed", "activated_skills": skills, "evidence": evidence}


def rubric(ws, case_id, **statuses):
    for rid, status in statuses.items():
        record = next(r for r in case(ws, case_id)["rubric"] if r["rubric_id"] == rid)
        record["status"] = status
        if status in ("pass", "fail"):
            record["evidence"] = "file listing"
        if status == "not-applicable":
            record["na_reason"] = "prompt only asks for a scaffold"


def blank_worksheet(scenarios_dir=TRIAL.EVALS):
    return TRIAL.build_worksheet(scenarios_dir, PROVENANCE)


def mixed_worksheet():
    ws = blank_worksheet()
    observe(ws, f"{SETUP}/p1", [SETUP])
    rubric(ws, f"{SETUP}/p1", r1="pass", r2="pass", r3="pass", r4="pass", r5="pass", r6="not-applicable")
    observe(ws, f"{SETUP}/p2", [SETUP, "testing-python-libraries"])  # extra skill is preserved
    rubric(ws, f"{SETUP}/p2", r1="pass", r2="fail")
    case(ws, f"{SETUP}/p3")["activation"] = {"status": "unobserved", "activated_skills": [], "evidence": "no log"}
    observe(ws, f"{SETUP}/n1", ["testing-python-libraries"])
    observe(ws, f"{SETUP}/n2", [SETUP])  # pilot wrongly activated
    observe(ws, f"{SECURITY}/p1", [SECURITY])  # all rubric items unscored
    observe(ws, f"{SECURITY}/p2", ["keeping-git-repos-clean"])
    rubric(ws, f"{SECURITY}/p2", **{f"r{i}": "not-applicable" for i in range(1, 6)})
    observe(ws, f"{SECURITY}/n1", ["rendering-untrusted-content", SECURITY])  # expected skill and pilot both
    observe(ws, f"{SECURITY}/n2", ["keeping-git-repos-clean"])
    case(ws, f"{SECURITY}/n3")["activation"] = {"status": "unobserved", "activated_skills": [], "evidence": ""}
    return ws


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.ws = mixed_worksheet()
        self.assertEqual(TRIAL.validate_worksheet(self.ws), [])
        self.summary = TRIAL.summarize_worksheet(self.ws)

    def test_exact_per_case_outcomes(self):
        got = {c["case_id"]: (c["activation"], c.get("procedure")) for c in self.summary["cases"]}
        self.assertEqual(got[f"{SETUP}/p1"], ("pass", "pass"))
        self.assertEqual(got[f"{SETUP}/p2"], ("pass", "fail"))
        self.assertEqual(got[f"{SETUP}/p3"], ("unobserved", "incomplete"))
        self.assertEqual(got[f"{SETUP}/n1"], ("pass", None))
        self.assertEqual(got[f"{SETUP}/n2"], ("fail", None))
        self.assertEqual(got[f"{SETUP}/n3"], ("unrecorded", None))
        self.assertEqual(got[f"{SECURITY}/p1"], ("pass", "incomplete"))
        self.assertEqual(got[f"{SECURITY}/p2"], ("fail", "undefined"))
        self.assertEqual(got[f"{SECURITY}/n1"], ("fail", None))
        self.assertEqual(got[f"{SECURITY}/n2"], ("pass", None))
        self.assertEqual(got[f"{SECURITY}/n3"], ("unobserved", None))
        extra = next(c for c in self.summary["cases"] if c["case_id"] == f"{SETUP}/p2")
        self.assertEqual(extra["activated_skills"], [SETUP, "testing-python-libraries"])

    def test_activation_summary_is_separate_with_exact_counts(self):
        a = self.summary["activation"]
        self.assertEqual((a["pass"], a["fail"], a["unobserved"], a["unrecorded"]), (5, 3, 2, 8))
        self.assertEqual((a["observed"], a["total"]), (8, 18))
        self.assertEqual(a["rate_observed"], 5 / 8)
        self.assertFalse(a["complete"])
        self.assertEqual(a["by_kind"]["positive"], {"pass": 3, "fail": 1, "unobserved": 1, "unrecorded": 4})
        self.assertEqual(a["by_kind"]["negative"], {"pass": 2, "fail": 2, "unobserved": 1, "unrecorded": 4})

    def test_procedure_summary_is_separate_with_exact_counts(self):
        p = self.summary["procedure"]
        self.assertEqual(p["cases"], {"pass": 1, "fail": 1, "incomplete": 6, "undefined": 1})
        items = p["items"]
        self.assertEqual((items["pass"], items["fail"], items["unscored"]), (6, 1, 35))
        self.assertEqual(items["not_applicable_excluded"], 6)
        self.assertEqual((items["scored"], items["applicable"]), (7, 42))
        self.assertEqual(items["rate_scored"], 6 / 7)
        self.assertEqual(items["rate_applicable"], 6 / 42)
        self.assertFalse(p["complete"])

    def test_zero_denominators_are_undefined_never_full(self):
        summary = TRIAL.summarize_worksheet(blank_worksheet())
        self.assertEqual(summary["activation"]["rate_observed"], "undefined")
        self.assertEqual(summary["procedure"]["items"]["rate_scored"], "undefined")
        text = TRIAL.render_text(summary)
        self.assertIn("0/0 = undefined", text)
        self.assertNotIn("100%", text)

    def test_text_report_shows_exclusions_and_disclaimer(self):
        text = TRIAL.render_text(self.summary)
        self.assertIn("5/8 = 62%", text)
        self.assertIn("6/7 = 86%", text)
        self.assertIn("not-applicable 6 (excluded)", text)
        self.assertIn("INCOMPLETE", text)
        self.assertIn("not automatic proof", text)


class ValidationTests(unittest.TestCase):
    def assert_error(self, mutate, fragment):
        ws = mixed_worksheet()
        mutate(ws)
        errors = TRIAL.validate_worksheet(ws)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_unknown_case_id(self):
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1").update(case_id="nope/p9"), "unknown case id 'nope/p9'")

    def test_duplicate_record(self):
        self.assert_error(lambda ws: ws["cases"].append(copy.deepcopy(ws["cases"][0])), "duplicate record")

    def test_missing_case(self):
        self.assert_error(lambda ws: ws["cases"].pop(), "is missing from the worksheet")

    def test_invalid_statuses(self):
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1")["activation"].update(status="maybe"), "invalid activation status")
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1")["rubric"][0].update(status="passed"), "invalid status 'passed'")

    def test_missing_provenance(self):
        for key in TRIAL.PROVENANCE:
            with self.subTest(key=key):
                self.assert_error(lambda ws: ws.update({key: None}), f"missing provenance: {key}")

    def test_mismatched_snapshot(self):
        self.assert_error(lambda ws: ws["scenarios"][SETUP]["content"]["rubric"].append("extra"), "content_sha256")
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1").update(prompt="edited"), "prompt")
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1")["rubric"][0].update(item="edited"), "item text")

    def test_evidence_and_reason_requirements(self):
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1")["rubric"][5].update(na_reason=""), "needs na_reason")
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1")["rubric"][0].update(evidence=""), "pass needs evidence")
        self.assert_error(lambda ws: case(ws, f"{SETUP}/p1")["activation"].update(evidence=""), "needs evidence")

    def test_unscored_is_valid_but_incomplete(self):
        self.assertEqual(TRIAL.validate_worksheet(blank_worksheet()), [])


class HistoricalAndCliTests(unittest.TestCase):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = TRIAL.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_report_reads_from_snapshot_after_scenarios_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenarios = Path(tmp)
            for path in (ROOT / "evals").glob("*.json"):
                shutil.copy(path, scenarios)
            ws = TRIAL.build_worksheet(scenarios, PROVENANCE)
            target = scenarios / f"{SETUP}.json"
            data = json.loads(target.read_text())
            data["rubric"] = ["a different rubric"]
            target.write_text(json.dumps(data))
            self.assertEqual(TRIAL.validate_worksheet(ws), [])
            self.assertEqual(len(case(ws, f"{SETUP}/p1")["rubric"]), 6)
            self.assertEqual(TRIAL.drifted_skills(ws, scenarios), [SETUP])

    def test_init_then_report_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws.json"
            args = ["init", str(dest)]
            for key, value in PROVENANCE.items():
                args += ["--" + key.replace("_", "-"), value]
            self.assertEqual(self.run_main(*args)[0], 0)
            ws = json.loads(dest.read_text())
            self.assertEqual(len(ws["cases"]), 18)
            code, _, err = self.run_main("init", str(dest))
            self.assertEqual(code, 1)
            self.assertIn("refusing to overwrite", err)
            case(ws, f"{SETUP}/p1")["activation"]["status"] = "bogus"
            dest.write_text(json.dumps(ws))
            code, _, err = self.run_main("report", str(dest))
            self.assertEqual(code, 1)
            self.assertIn("invalid activation status", err)
            observe(ws, f"{SETUP}/p1", [SETUP])
            dest.write_text(json.dumps(ws))
            code, out, _ = self.run_main("report", str(dest), "--format", "json")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["activation"]["pass"], 1)

    def test_init_refuses_destination_inside_evals(self):
        code, _, err = self.run_main("init", str(ROOT / "evals" / "worksheet.json"))
        self.assertEqual(code, 1)
        self.assertIn("outside evals/", err)
        self.assertFalse((ROOT / "evals" / "worksheet.json").exists())

    def test_missing_provenance_is_reported_at_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_main("init", str(Path(tmp) / "w.json"), "--catalog-commit", "abc")
            self.assertEqual(code, 0)
            self.assertIn("Fill in before reporting", out)
            self.assertIn("client", out)


if __name__ == "__main__":
    unittest.main()
