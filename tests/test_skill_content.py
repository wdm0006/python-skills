import ast
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


def python_fences(text):
    """Yield (fence index, info tokens, source) while tracking every language.

    Space-indented list fences are supported; remove the opening indentation
    from code lines. Pipe-prefixed table cells and blockquotes are skipped.
    Fences on the same line as a list marker are also skipped.
    Indices are one-based across all fenced blocks in the file.
    """
    fence = None
    index = 0
    for line in text.splitlines(keepends=True):
        if fence is None:
            opening = re.match(r"^( *)(`{3,}|~{3,})([^\n]*)$", line.rstrip("\r\n"))
            if opening is None:
                continue
            indent, fence, info = opening.groups()
            info = info.split()
            index += 1
            source = []
        elif re.fullmatch(r" *" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*", line.rstrip("\r\n")):
            if info and info[0] == "python":
                yield index, info, "".join(source)
            fence = None
        else:
            source.append(line[len(indent):] if line.startswith(indent) else line)
    if fence is not None and info and info[0] == "python":
        yield index, info, "".join(source)


class SkillContentTests(unittest.TestCase):
    def skill_files(self):
        files = sorted(SKILLS.glob("*/*/SKILL.md"))
        self.assertTrue(files)
        return files

    def test_python_fence_scanner_tracks_delimiters_and_indentation(self):
        text = (
            "````markdown\n```python\nnot python!\n```\n````\n"
            "```bash\necho hello\n```\n"
            "1. Example:\n\n   ```python\n   if True:\n       value = 1\n   ```\n"
            "~~~python fragment\nexcept Exception:\n~~~\n"
            "| ```python |\n| broken! |\n| ``` |\n"
            "> ```python\n> broken!\n> ```\n"
            "```python\nvalue = 2\n````\n"
            "```python\nvalue = 3\n"
        )
        self.assertEqual(list(python_fences(text)), [
            (3, ["python"], "if True:\n    value = 1\n"),
            (4, ["python", "fragment"], "except Exception:\n"),
            (5, ["python"], "value = 2\n"),
            (6, ["python"], "value = 3\n"),
        ])

    def test_python_fences_parse(self):
        """Parse Python examples; only ``python fragment`` opts out.

        Intentional partial statements use that exact info string so Markdown
        still displays Python code. See python_fences for container handling.
        """
        files = sorted(SKILLS.rglob("*.md"))
        self.assertTrue(files)
        for markdown_file in files:
            for index, info, source in python_fences(markdown_file.read_text()):
                with self.subTest(file=str(markdown_file.relative_to(ROOT)), fence=index):
                    if info != ["python", "fragment"]:
                        ast.parse(source, filename=str(markdown_file.relative_to(ROOT)))

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
