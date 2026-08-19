import contextlib
import importlib.util
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "python"
    / "release-management"
    / "scripts"
    / "bump_version.py"
)
SPEC = importlib.util.spec_from_file_location("bump_version", SCRIPT)
assert SPEC and SPEC.loader
BUMP_VERSION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUMP_VERSION
SPEC.loader.exec_module(BUMP_VERSION)


CHANGELOG = """\
# Changelog

## [Unreleased]

### Fixed
- Restored parity with the 1.2.3 behaviour described in the old notes.

## [1.2.2] - 2024-01-01

### Added
- Initial release.

[Unreleased]: https://example.com/compare/v1.2.2...HEAD
[1.2.3]: https://example.com/releases/v1.2.3
[1.2.2]: https://example.com/releases/v1.2.2
"""

PYPROJECT = """\
[tool.before]
version = "9.9.9"

[project]
name = "example"
version = "1.2.3"
description = "A version = \\"value\\" example"

[tool.after]
version = "8.8.8"
"""


class ProjectVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project = Path(self.temp_dir.name)
        self.pyproject = self.project / "pyproject.toml"
        self.pyproject.write_text(PYPROJECT)

    def test_get_current_version_reads_project_table(self):
        self.assertEqual(BUMP_VERSION.get_current_version(self.project), "1.2.3")

    def test_update_changes_only_project_version(self):
        expected = PYPROJECT.replace('version = "1.2.3"', 'version = "1.2.4"')

        updated = BUMP_VERSION.update_version(self.project, "1.2.4")

        self.assertEqual(updated, [str(self.pyproject)])
        self.assertEqual(self.pyproject.read_text(), expected)

    def test_missing_project_version_uses_existing_failure_path(self):
        self.pyproject.write_text('[tool.example]\nversion = "9.9.9"\n\n[project]\nname = "example"\n')

        self.assertIsNone(BUMP_VERSION.get_current_version(self.project))
        self.assertEqual(BUMP_VERSION.update_version(self.project, "1.2.4"), [])


class UpdateChangelogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project = Path(self.temp_dir.name)
        self.changelog = self.project / "CHANGELOG.md"
        self.changelog.write_text(CHANGELOG)

    def headings(self, version):
        return re.findall(
            rf'(?m)^##\s*\[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$',
            self.changelog.read_text(),
        )

    def update(self, version, dry_run=False):
        return BUMP_VERSION.update_changelog(self.project, version, dry_run)

    def test_first_update_inserts_one_heading_below_unreleased(self):
        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_UPDATED)

        self.assertEqual(len(self.headings("1.2.3")), 1)
        lines = self.changelog.read_text().splitlines()
        unreleased = lines.index("## [Unreleased]")
        self.assertEqual(lines[unreleased + 1], "")
        self.assertRegex(lines[unreleased + 2], r'^## \[1\.2\.3\] - \d{4}-\d{2}-\d{2}$')

    def test_repeated_update_reports_already_released(self):
        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_UPDATED)
        after_first = self.changelog.read_bytes()

        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_ALREADY_RELEASED)

        self.assertEqual(self.changelog.read_bytes(), after_first)
        self.assertEqual(len(self.headings("1.2.3")), 1)

    def test_missing_changelog_reports_no_changelog(self):
        self.changelog.unlink()

        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_MISSING)

    def test_changelog_without_unreleased_heading_is_left_untouched(self):
        self.changelog.write_text(CHANGELOG.replace("## [Unreleased]\n", "", 1))
        before = self.changelog.read_bytes()

        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_NO_UNRELEASED)

        self.assertEqual(self.changelog.read_bytes(), before)
        self.assertEqual(self.headings("1.2.3"), [])

    def test_dry_run_reports_the_outcome_without_writing(self):
        before = self.changelog.read_bytes()

        self.assertEqual(self.update("1.2.3", dry_run=True), BUMP_VERSION.CHANGELOG_UPDATED)

        self.assertEqual(self.changelog.read_bytes(), before)
        self.assertEqual(self.headings("1.2.3"), [])

    def test_version_mentioned_only_in_prose_or_links_is_not_a_release_heading(self):
        # The fixture already cites 1.2.3 in release notes and in a link
        # reference, so the first insertion must still happen.
        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_UPDATED)
        self.assertEqual(len(self.headings("1.2.3")), 1)

    def test_other_versions_are_still_inserted(self):
        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_UPDATED)
        self.assertEqual(self.update("1.3.0"), BUMP_VERSION.CHANGELOG_UPDATED)

        self.assertEqual(len(self.headings("1.2.3")), 1)
        self.assertEqual(len(self.headings("1.3.0")), 1)

    def test_existing_heading_for_a_longer_version_does_not_block_a_prefix(self):
        self.assertEqual(self.update("1.2.30"), BUMP_VERSION.CHANGELOG_UPDATED)
        self.assertEqual(self.update("1.2.3"), BUMP_VERSION.CHANGELOG_UPDATED)

        self.assertEqual(len(self.headings("1.2.3")), 1)
        self.assertEqual(len(self.headings("1.2.30")), 1)


class ChangelogReportingTests(unittest.TestCase):
    """--changelog must say what happened instead of silently doing nothing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        # main() resolves --project, so match that here (/var -> /private/var).
        self.project = Path(self.temp_dir.name).resolve()
        (self.project / "pyproject.toml").write_text(PYPROJECT)
        self.changelog = self.project / "CHANGELOG.md"
        self.changelog.write_text(CHANGELOG)

    def run_main(self, spec="patch", *extra_args):
        argv = ["bump_version.py", spec, "--project", str(self.project), "--changelog"]
        argv.extend(extra_args)
        out = io.StringIO()
        original_argv = sys.argv
        sys.argv = argv
        try:
            with contextlib.redirect_stdout(out):
                BUMP_VERSION.main()
        finally:
            sys.argv = original_argv
        return out.getvalue()

    def test_updated_changelog_is_listed(self):
        output = self.run_main()

        self.assertIn(f"  - {self.changelog}\n", output)
        self.assertNotIn("Warning", output)

    def test_missing_unreleased_heading_is_reported(self):
        self.changelog.write_text(CHANGELOG.replace("## [Unreleased]\n", "", 1))
        before = self.changelog.read_bytes()

        output = self.run_main()

        self.assertIn("Warning", output)
        self.assertIn("## [Unreleased]", output)
        self.assertEqual(self.changelog.read_bytes(), before)

    def test_missing_changelog_file_is_reported(self):
        self.changelog.unlink()

        output = self.run_main()

        self.assertIn("Warning", output)
        self.assertIn(str(self.changelog), output)
        self.assertFalse(self.changelog.exists())

    def test_already_released_version_is_reported(self):
        output = self.run_main()
        self.assertIn(f"  - {self.changelog}\n", output)
        after_first = self.changelog.read_bytes()

        output = self.run_main("1.2.4")

        self.assertIn("already has a 1.2.4 heading", output)
        self.assertNotIn("Warning", output)
        self.assertEqual(self.changelog.read_bytes(), after_first)

    def test_dry_run_reports_without_writing(self):
        self.changelog.write_text(CHANGELOG.replace("## [Unreleased]\n", "", 1))
        before = self.changelog.read_bytes()

        output = self.run_main("patch", "--dry-run")

        self.assertIn("Warning", output)
        self.assertIn("## [Unreleased]", output)
        self.assertEqual(self.changelog.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
