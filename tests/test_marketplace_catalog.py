import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"

README_SECTIONS = {
    "common": "Common (language-agnostic)",
    "go": "Go",
    "javascript": "JavaScript / Browser Extensions",
    "python": "Python",
    "rust": "Rust",
    "scala": "Scala",
    "swift": "Swift / Apple Platforms",
}


def read_section(markdown, heading):
    match = re.search(
        rf"^### {re.escape(heading)}\n(?P<body>.*?)(?=^### |^## |\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"README section not found: {heading}")
    return match.group("body")


def read_frontmatter_name(skill_file):
    contents = skill_file.read_text()
    match = re.match(r"---\n(?P<frontmatter>.*?)\n---\n", contents, re.DOTALL)
    if match is None:
        raise AssertionError(f"frontmatter not found: {skill_file.relative_to(ROOT)}")
    name = re.search(r"^name:\s*(?P<name>\S+)\s*$", match.group("frontmatter"), re.MULTILINE)
    if name is None:
        raise AssertionError(f"frontmatter name not found: {skill_file.relative_to(ROOT)}")
    return name.group("name")


class MarketplaceCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.readme = README.read_text()

    def test_readme_install_commands_match_declared_bundles_and_marketplace(self):
        commands = re.findall(r"^/plugin install ([^@\s]+)@([^\s]+)$", self.readme, re.MULTILINE)
        declared_bundles = {plugin["name"] for plugin in self.manifest["plugins"]}

        self.assertEqual({bundle for bundle, _ in commands}, declared_bundles)
        self.assertEqual({marketplace for _, marketplace in commands}, {self.manifest["name"]})
        self.assertEqual(len(commands), len(declared_bundles), "install commands must be unique")

    def test_manifest_skill_paths_and_readme_catalog_entries(self):
        skill_paths = {
            Path(skill_path.removeprefix("./"))
            for plugin in self.manifest["plugins"]
            for skill_path in plugin["skills"]
        }

        for skill_path in sorted(skill_paths):
            with self.subTest(skill_path=skill_path):
                skill_file = ROOT / skill_path / "SKILL.md"
                self.assertTrue(skill_file.is_file(), f"missing {skill_file.relative_to(ROOT)}")

                namespace = skill_path.parts[1]
                section = read_section(self.readme, README_SECTIONS[namespace])
                name = read_frontmatter_name(skill_file)
                self.assertRegex(section, rf"(?m)^\| \*\*{re.escape(name)}\*\* \|")

    def test_python_library_complete_covers_every_python_and_common_skill(self):
        expected = {
            f"./{skill_file.parent.relative_to(ROOT)}"
            for namespace in ("python", "common")
            for skill_file in sorted((ROOT / "skills" / namespace).glob("*/SKILL.md"))
        }
        complete = next(
            plugin for plugin in self.manifest["plugins"] if plugin["name"] == "python-library-complete"
        )

        self.assertEqual(expected - set(complete["skills"]), set())
    def test_readme_plus_joined_bundle_lists_match_manifest_membership(self):
        """Gate README bundle bullets written as `a` + `b` + ... against skills[].

        Scope: only bullets in "Plugin Bundles" whose text after the dash is a
        pure `+`-joined list of backticked frontmatter names. Prose-only
        bullets (narrower Python, language-agnostic) are not checked.
        """
        section = re.search(r"^## Plugin Bundles\n(?P<body>.*?)(?=^## )", self.readme, re.M | re.S)
        self.assertIsNotNone(section, "README 'Plugin Bundles' section not found")
        plugins = {plugin["name"]: plugin for plugin in self.manifest["plugins"]}
        names_to_paths = {
            read_frontmatter_name(skill_file): f"./{skill_file.parent.relative_to(ROOT)}"
            for skill_file in (ROOT / "skills").glob("*/*/SKILL.md")
        }
        name = r"`[a-z0-9-]+`"
        pattern = rf"^- \*\*(?P<bundle>[^*]+)\*\* — (?P<list>{name}(?: \+ {name})*)\.$"
        checked = 0
        for match in re.finditer(pattern, section.group("body"), re.M):
            bundle = match.group("bundle")
            with self.subTest(bundle=bundle):
                self.assertIn(bundle, plugins)
                listed = set()
                for skill_name in re.findall(r"`([^`]+)`", match.group("list")):
                    self.assertIn(skill_name, names_to_paths, f"{bundle}: unknown skill {skill_name}")
                    listed.add(names_to_paths[skill_name])
                self.assertEqual(
                    listed,
                    set(plugins[bundle]["skills"]),
                    f"{bundle}: README list differs from marketplace.json skills[]",
                )
                checked += 1
        self.assertGreaterEqual(checked, 5, "expected the +-joined language bundles to be parsed")


if __name__ == "__main__":
    unittest.main()
