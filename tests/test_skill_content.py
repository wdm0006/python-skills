import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "skills"

FENCE = re.compile(r"^(?P<fence>`{3,}|~{3,}).*?^(?P=fence)[ \t]*$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def frontmatter_fields(skill_file):
    match = re.match(r"---\n(?P<body>.*?)\n---\n", skill_file.read_text(), re.DOTALL)
    if match is None:
        raise AssertionError(f"frontmatter not found: {skill_file.relative_to(ROOT)}")
    fields = {}
    for key in ("name", "description"):
        field = re.search(rf"^{key}:[ \t]*(?P<value>.*)$", match.group("body"), re.MULTILINE)
        fields[key] = field.group("value").strip() if field else ""
    return fields


def relative_links(markdown_file):
    text = FENCE.sub("", markdown_file.read_text())
    for match in LINK.finditer(text):
        target = match.group("target").strip("<>")
        if SCHEME.match(target) or target.startswith(("#", "//")):
            continue
        target = target.split("#", 1)[0]
        if target:
            yield target


class SkillContentTests(unittest.TestCase):
    def skill_files(self):
        files = sorted(SKILLS.glob("*/*/SKILL.md"))
        self.assertTrue(files)
        return files

    def test_frontmatter_has_name_and_description(self):
        for skill_file in self.skill_files():
            with self.subTest(skill=str(skill_file.relative_to(ROOT))):
                fields = frontmatter_fields(skill_file)
                self.assertTrue(fields["name"], "empty name")
                self.assertTrue(fields["description"], "empty description")

    def test_frontmatter_names_are_unique(self):
        seen = {}
        for skill_file in self.skill_files():
            name = frontmatter_fields(skill_file)["name"]
            seen.setdefault(name, []).append(str(skill_file.relative_to(ROOT)))
        for name, files in seen.items():
            with self.subTest(name=name):
                self.assertEqual(len(files), 1, f"duplicate name in {files}")

    def test_relative_markdown_links_resolve(self):
        files = sorted(SKILLS.rglob("*.md")) + [ROOT / "README.md"]
        for markdown_file in files:
            with self.subTest(file=str(markdown_file.relative_to(ROOT))):
                missing = [
                    target
                    for target in relative_links(markdown_file)
                    if not (markdown_file.parent / target).exists()
                ]
                self.assertEqual(missing, [], "broken relative links")

    def test_link_scanner_ignores_fenced_code(self):
        sample = ROOT / "tests" / "_fence_probe.md"
        self.addCleanup(lambda: sample.unlink(missing_ok=True))
        sample.write_text(
            "[ok](https://x.y/z) [anchor](#a) [mail](mailto:a@b.c)\n"
            "```md\n[gone](nope.md)\n```\n"
            "~~~\n[gone2](nope2.md)\n~~~\n"
            "[real](missing.md#frag)\n"
        )
        self.assertEqual(list(relative_links(sample)), ["missing.md"])


if __name__ == "__main__":
    unittest.main()
