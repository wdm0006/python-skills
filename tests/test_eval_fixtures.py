import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "evals" / "fixtures" / "materialize.py"
spec = importlib.util.spec_from_file_location("materialize_fixture", SCRIPT)
MATERIALIZE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = MATERIALIZE
spec.loader.exec_module(MATERIALIZE)

FIXTURE_IDS = ["setup-clean-parent", "security-inert-examples", "ci-gate-mismatch"]
UV = shutil.which("uv")


def snapshot(directory: Path) -> dict:
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in sorted(directory.rglob("*")) if p.is_file()}


class FixtureContractTests(unittest.TestCase):
    def test_each_fixture_maps_to_one_existing_prompt_and_unchanged_inputs(self):
        prompts = set()
        for fid in FIXTURE_IDS:
            with self.subTest(fixture=fid):
                manifest = MATERIALIZE.load_manifest(fid)
                self.assertEqual(MATERIALIZE.prompt_errors(manifest), [])
                self.assertEqual(MATERIALIZE.input_errors(manifest), [])
                self.assertTrue(manifest["setup"] and manifest["expected_observations"])
                prompts.add((manifest["skill"], manifest["prompt"]))
        self.assertEqual(len(prompts), len(FIXTURE_IDS))

    def test_stale_prompt_mapping_is_detected(self):
        manifest = MATERIALIZE.load_manifest("ci-gate-mismatch")
        for label, change in {
            "prompt reworded": {"prompt": manifest["prompt"] + " Please."},
            "rubric reworded": {"rubric_items": ["no longer in the scenario"]},
            "schema bumped": {"scenario_schema_version": 2},
            "wrong skill": {"skill": "auditing-python-security"},
            "scenario missing": {"scenario": "gone.json"},
        }.items():
            with self.subTest(case=label):
                self.assertTrue(MATERIALIZE.prompt_errors(dict(manifest, **change)))

    def test_changed_fixture_input_is_detected_and_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = tmp / "fixtures"
            shutil.copytree(ROOT / "evals" / "fixtures", root, ignore=shutil.ignore_patterns("__pycache__"))
            manifest = MATERIALIZE.load_manifest("security-inert-examples", root)
            self.assertEqual(MATERIALIZE.input_errors(manifest, root), [])
            target = root / "security-inert-examples" / "files" / "src" / "sample_service" / "loaders.py"
            target.write_text(target.read_text() + "\n# edited\n")
            self.assertEqual(MATERIALIZE.input_errors(manifest, root), ["hash changed: src/sample_service/loaders.py"])
            (root / "security-inert-examples" / "files" / "extra.txt").write_text("x")
            self.assertIn("unexpected file: extra.txt", MATERIALIZE.input_errors(manifest, root))
            dest = tmp / "out"
            with self.assertRaises(MATERIALIZE.FixtureError):
                MATERIALIZE.materialize("security-inert-examples", dest, root)
            self.assertFalse(dest.exists())

    def test_security_fixture_is_inert_and_documents_findings(self):
        manifest = MATERIALIZE.load_manifest("security-inert-examples")
        source = {n: (SCRIPT.parent / "security-inert-examples" / "files" / n).read_text() for n in manifest["files"]}
        code = "\n".join(t for n, t in source.items() if n.endswith(".py"))
        for marker in ("INERT EVALUATION EXAMPLE",):
            self.assertIn(marker, code)
        for banned in ("password", "secret", "token", "api_key", "AKIA", "BEGIN PRIVATE", "os.system", "__reduce__"):
            self.assertNotIn(banned.lower(), code.lower())
        expected = " ".join(manifest["expected_observations"])
        for name in ("queries.find_user", "commands.archive", "loaders.load_state"):
            self.assertIn(name, expected)

    def test_setup_fixture_has_no_generated_package(self):
        manifest = MATERIALIZE.load_manifest("setup-clean-parent")
        self.assertEqual(list(manifest["files"]), ["PARENT.md"])


class MaterializerTests(unittest.TestCase):
    def test_two_materializations_are_identical(self):
        for fid in FIXTURE_IDS:
            with self.subTest(fixture=fid), tempfile.TemporaryDirectory() as tmp:
                a, b = Path(tmp) / "a", Path(tmp) / "b"
                MATERIALIZE.materialize(fid, a)
                MATERIALIZE.materialize(fid, b)
                manifest = MATERIALIZE.load_manifest(fid)
                self.assertEqual(snapshot(a), snapshot(b))
                self.assertEqual(sorted(snapshot(a)), sorted(manifest["files"]))
                self.assertEqual(MATERIALIZE.tree_digest(MATERIALIZE.hash_tree(a)), manifest["tree_sha256"])

    def test_refusals_happen_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sentinel = tmp / "existing"
            sentinel.mkdir()
            (sentinel / "keep.txt").write_text("keep")
            before = snapshot(tmp)
            for fid in ("../ci-gate-mismatch", "CI-gate", "ci/gate", "", "nonexistent", "-x"):
                with self.subTest(fixture=fid), self.assertRaises(MATERIALIZE.FixtureError):
                    MATERIALIZE.materialize(fid, tmp / "new")
            with self.assertRaises(MATERIALIZE.FixtureError):
                MATERIALIZE.materialize("ci-gate-mismatch", sentinel)
            link = tmp / "link"
            link.symlink_to(sentinel)
            with self.assertRaises(MATERIALIZE.FixtureError):
                MATERIALIZE.materialize("ci-gate-mismatch", link)
            with self.assertRaises(MATERIALIZE.FixtureError):
                MATERIALIZE.materialize("ci-gate-mismatch", tmp / "missing-parent" / "new")
            self.assertEqual(snapshot(tmp), before)
            self.assertFalse((tmp / "new").exists())

    def test_cli_reports_identity_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "d"
            run = lambda: subprocess.run(  # noqa: E731
                [sys.executable, "-I", str(SCRIPT), "setup-clean-parent", str(dest)], capture_output=True, text=True
            )
            first = run()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn(MATERIALIZE.load_manifest("setup-clean-parent")["tree_sha256"], first.stdout)
            self.assertEqual(run().returncode, 1)


@unittest.skipUnless(UV, "uv is required to run the pinned ruff reproduction")
class CiReproductionTests(unittest.TestCase):
    def run_cmd(self, spec, cwd):
        return subprocess.run(spec["argv"], cwd=cwd, capture_output=True, text=True).returncode

    def test_local_passes_workflow_fails_and_alignment_fixes_it(self):
        repro = MATERIALIZE.load_manifest("ci-gate-mismatch")["reproduction"]
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "p"
            MATERIALIZE.materialize("ci-gate-mismatch", project)
            self.assertIn(" ".join(repro["local"]["argv"][:-1]), (project / "Makefile").read_text())
            workflow = (project / ".github/workflows/ci.yml").read_text()
            self.assertIn(" ".join(repro["workflow"]["argv"]), workflow)
            self.assertEqual(self.run_cmd(repro["local"], project), repro["local"]["expect_exit"])
            self.assertEqual(self.run_cmd(repro["workflow"], project), repro["workflow"]["expect_exit"])
            for step in repro["align"]:
                path = project / step["file"]
                text = path.read_text()
                self.assertEqual(text.count(step["old"]), 1)
                path.write_text(text.replace(step["old"], step["new"]))
                self.assertEqual(self.run_cmd(repro["local"], project), step["then_local_exit"])
                if "then_workflow_exit" in step:
                    self.assertEqual(self.run_cmd(repro["workflow"], project), step["then_workflow_exit"])


if __name__ == "__main__":
    unittest.main()
