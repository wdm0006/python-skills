import importlib.util
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

    def test_first_update_inserts_one_heading_below_unreleased(self):
        self.assertTrue(BUMP_VERSION.update_changelog(self.project, "1.2.3"))

        self.assertEqual(len(self.headings("1.2.3")), 1)
        lines = self.changelog.read_text().splitlines()
        unreleased = lines.index("## [Unreleased]")
        self.assertEqual(lines[unreleased + 1], "")
        self.assertRegex(lines[unreleased + 2], r'^## \[1\.2\.3\] - \d{4}-\d{2}-\d{2}$')

    def test_repeated_update_is_a_no_op(self):
        self.assertTrue(BUMP_VERSION.update_changelog(self.project, "1.2.3"))
        after_first = self.changelog.read_bytes()

        self.assertFalse(BUMP_VERSION.update_changelog(self.project, "1.2.3"))

        self.assertEqual(self.changelog.read_bytes(), after_first)
        self.assertEqual(len(self.headings("1.2.3")), 1)

    def test_version_mentioned_only_in_prose_or_links_is_not_a_release_heading(self):
        # The fixture already cites 1.2.3 in release notes and in a link
        # reference, so the first insertion must still happen.
        self.assertTrue(BUMP_VERSION.update_changelog(self.project, "1.2.3"))
        self.assertEqual(len(self.headings("1.2.3")), 1)

    def test_other_versions_are_still_inserted(self):
        self.assertTrue(BUMP_VERSION.update_changelog(self.project, "1.2.3"))
        self.assertTrue(BUMP_VERSION.update_changelog(self.project, "1.3.0"))

        self.assertEqual(len(self.headings("1.2.3")), 1)
        self.assertEqual(len(self.headings("1.3.0")), 1)

    def test_existing_heading_for_a_longer_version_does_not_block_a_prefix(self):
        self.assertTrue(BUMP_VERSION.update_changelog(self.project, "1.2.30"))
        self.assertTrue(BUMP_VERSION.update_changelog(self.project, "1.2.3"))

        self.assertEqual(len(self.headings("1.2.3")), 1)
        self.assertEqual(len(self.headings("1.2.30")), 1)


if __name__ == "__main__":
    unittest.main()
