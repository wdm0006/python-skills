import importlib
import importlib.util
import os
import py_compile
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "python"
    / "project-setup"
    / "scripts"
    / "create_project.py"
)
SPEC = importlib.util.spec_from_file_location("create_project", SCRIPT)
assert SPEC and SPEC.loader
CREATE_PROJECT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CREATE_PROJECT
SPEC.loader.exec_module(CREATE_PROJECT)


class CreateProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_cwd = Path.cwd()
        os.chdir(self.temp_dir.name)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        self.temp_dir.cleanup()

    def test_dotted_distribution_name_uses_importable_package_name(self):
        project = CREATE_PROJECT.create_project("my.project")

        self.assertTrue((project / "src" / "my_project" / "__init__.py").is_file())
        self.assertTrue((project / "tests" / "test_my_project.py").is_file())
        sys.path.insert(0, str(project / "src"))
        try:
            package = importlib.import_module("my_project")
            self.assertEqual(package.__version__, "0.1.0")
        finally:
            sys.path.pop(0)
            sys.modules.pop("my_project", None)

    def test_invalid_package_name_fails_before_creating_directory(self):
        for name in ("123-library", "has!punctuation", "class"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "valid Python package name"):
                    CREATE_PROJECT.create_project(name)
                self.assertFalse(Path(name).exists())

    def test_metadata_is_serialized_in_toml_and_python(self):
        author = 'O"Connor\\Tools'
        email = 'dev\\ops"team@example.com'
        description = 'A "quoted" \\library'

        project = CREATE_PROJECT.create_project(
            "quoted-library",
            author=author,
            email=email,
            description=description,
        )

        with (project / "pyproject.toml").open("rb") as file:
            metadata = tomllib.load(file)["project"]
        self.assertEqual(metadata["description"], description)
        self.assertEqual(metadata["authors"], [{"name": author, "email": email}])

        for python_file in project.rglob("*.py"):
            py_compile.compile(python_file, doraise=True)

    def test_generated_python_files_end_with_single_newline(self):
        project = CREATE_PROJECT.create_project("sample-lib")

        init_py = project / "src" / "sample_lib" / "__init__.py"
        test_py = project / "tests" / "test_sample_lib.py"
        for python_file in (init_py, test_py):
            with self.subTest(python_file=python_file.name):
                contents = python_file.read_text()
                self.assertTrue(contents, "generated file should not be empty")
                self.assertTrue(
                    contents.endswith("\n"),
                    "generated Python file must end with a newline (Ruff W292)",
                )
                self.assertFalse(
                    contents.endswith("\n\n"),
                    "generated Python file must end with exactly one newline",
                )

    def test_hyphenated_name_keeps_existing_layout(self):
        project = CREATE_PROJECT.create_project("my-library")

        self.assertTrue((project / "src" / "my_library").is_dir())
        self.assertTrue((project / "tests" / "test_my_library.py").is_file())


if __name__ == "__main__":
    unittest.main()
