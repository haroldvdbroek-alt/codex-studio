"""Generatorcontroles met tijdelijke mappen en echte gegenereerde projecten."""

import contextlib
import io
import os
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
import tomllib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import create_project as generator


class ProjectGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Resolve zodat een door het OS gebruikte tijdelijke symlink niet stoort.
        self.root = Path(self.temp.name).resolve()

    def run_python(self, *arguments, cwd, isolated=True):
        environment = os.environ.copy()
        for variable in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH"):
            environment.pop(variable, None)
        result = subprocess.run(
            [sys.executable, *(["-I"] if isolated else []), *arguments], cwd=cwd,
            env=environment,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def template_copy(self):
        template = self.root / "template"
        for relative in generator.TEMPLATE_FILES:
            target = template / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                (generator.TEMPLATE_DIR / relative).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        return template

    def test_valid_package_names(self):
        for name, expected in (("mijn-notities", "mijn_notities"), ("app2", "app2"),
                               ("a", "a"), ("a-2", "a_2")):
            with self.subTest(name=name):
                self.assertEqual(generator.package_name_for(name), expected)

    def test_invalid_names_never_create_output(self):
        invalid = (
            "", ".", "..", "../buiten", "a/../../buiten", "a/b", "a\\b",
            "/absoluut", "C:\\temp", "C:temp", "~", "a.b", "a_b", "a b",
            "App", "café", "1app", "-app", "app-", "a--b", "a" * 65,
            "con", "nul", "aux", "prn", "com1", "lpt9", "class", "match",
            "unittest", "pathlib", "sys", "a\n", 'a"b', "a${b}",
        )
        output = self.root / "niet-aanmaken"
        for name in invalid:
            with self.subTest(name=repr(name)):
                with self.assertRaises(ValueError):
                    generator.create_project(name, output)
                self.assertFalse(output.exists())

    def test_existing_empty_directory_is_preserved(self):
        target = self.root / "bestaand"
        target.mkdir()
        with self.assertRaises(FileExistsError):
            generator.create_project("bestaand", self.root)
        self.assertEqual(list(target.iterdir()), [])

    def test_existing_directory_contents_are_preserved(self):
        target = self.root / "bestaand"
        target.mkdir()
        marker = target / "notitie.txt"
        marker.write_text("fictieve inhoud", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            generator.create_project("bestaand", self.root)
        self.assertEqual(marker.read_text(encoding="utf-8"), "fictieve inhoud")
        self.assertEqual(list(target.iterdir()), [marker])

    def test_existing_file_is_preserved(self):
        target = self.root / "bestaand"
        target.write_bytes(b"voorbeeld")
        with self.assertRaises(FileExistsError):
            generator.create_project("bestaand", self.root)
        self.assertEqual(target.read_bytes(), b"voorbeeld")

    def test_target_created_during_preparation_is_not_reused(self):
        render = generator.render_template

        def create_competing_target(project_name, package_name):
            content = render(project_name, package_name)
            (self.root / project_name).mkdir()
            return content

        with patch.object(generator, "render_template", side_effect=create_competing_target):
            with self.assertRaises(FileExistsError):
                generator.create_project("voorbeeld", self.root)
        self.assertEqual(list((self.root / "voorbeeld").iterdir()), [])

    def test_default_output_uses_home_projects(self):
        with patch.object(generator.Path, "home", return_value=self.root):
            target = generator.create_project("voorbeeld-app")
        self.assertEqual(target, self.root / "Projects" / "voorbeeld-app")

    def test_only_known_files_are_copied(self):
        template = self.template_copy()
        for relative in (".venv/config", "__pycache__/cache.pyc", ".git/config",
                         ".env", ".env.example", "persoonlijk.txt", "id_rsa",
                         "tests/persoonlijk.json", "src/project_package/prive.py"):
            path = template / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fictieve lokale gegevens", encoding="utf-8")
        with patch.object(generator, "TEMPLATE_DIR", template):
            target = generator.create_project("schone-app", self.root / "output")
        actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        expected = {p.replace("project_package", "schone_app")
                    for p in generator.TEMPLATE_FILES}
        self.assertEqual(actual, expected)

    def test_missing_template_file_leaves_no_project(self):
        with patch.object(generator, "TEMPLATE_DIR", self.root / "ontbreekt"):
            with self.assertRaises(ValueError):
                generator.create_project("voorbeeld", self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def make_link(self, link, target, is_directory=False):
        try:
            link.symlink_to(target, target_is_directory=is_directory)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolische koppelingen zijn hier niet beschikbaar.")

    def test_symlink_attributes_are_rejected_without_platform_privileges(self):
        info = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        with patch.object(Path, "lstat", return_value=info):
            with self.assertRaises(ValueError):
                generator.reject_links(self.root / "bron")

    def test_windows_junction_attributes_are_rejected(self):
        info = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
        )
        with patch.object(Path, "lstat", return_value=info):
            with self.assertRaises(ValueError):
                generator.reject_links(self.root / "bron")

    def test_symlink_in_template_is_rejected(self):
        template = self.template_copy()
        # Een nieuwe toegestane bestandslocatie, zonder iets te verwijderen.
        link = template / "gekoppeld.md"
        self.make_link(link, template / "README.md")
        with patch.object(generator, "TEMPLATE_DIR", template), patch.object(
            generator, "TEMPLATE_FILES", ("gekoppeld.md",)
        ):
            with self.assertRaises(ValueError):
                generator.create_project("voorbeeld", self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def test_symlink_in_output_path_is_rejected(self):
        real = self.root / "echte-map"
        real.mkdir()
        link = self.root / "koppeling"
        self.make_link(link, real, is_directory=True)
        with self.assertRaises(ValueError):
            generator.create_project("voorbeeld", link / "submap")
        self.assertEqual(list(real.iterdir()), [])

    def test_dangling_destination_symlink_is_preserved(self):
        link = self.root / "voorbeeld"
        self.make_link(link, self.root / "ontbreekt", is_directory=True)
        with self.assertRaises(FileExistsError):
            generator.create_project("voorbeeld", self.root)
        self.assertTrue(link.is_symlink())

    def test_generated_project_metadata_tests_app_and_workflow(self):
        target = generator.create_project("mijn-notities", self.root / "met spaties")
        metadata = tomllib.loads((target / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["name"], "mijn-notities")
        self.assertEqual(metadata["project"]["dependencies"], [])
        for path in target.rglob("*"):
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("PROJECT_NAME", content)
                self.assertNotIn("project_package", content)
        workflow = (target / ".github/workflows/python-tests.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow, (generator.TEMPLATE_DIR / ".github/workflows/python-tests.yml").read_text(encoding="utf-8"))
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        result = self.run_python("-m", "unittest", "discover", "-s", "tests", "-v", cwd=target)
        self.assertIn("Ran 4 tests", result.stderr)
        result = self.run_python("-m", "mijn_notities", cwd=target / "src", isolated=False)
        self.assertEqual(result.stdout, "Hallo, Voorbeeld!\n")
        self.assertFalse((target / ".git").exists())

    def test_cli_from_other_working_directory(self):
        output = self.root / "projecten"
        result = self.run_python(
            str(ROOT / "create_project.py"), "cli-app", "--type", "python",
            "--output", str(output), cwd=self.root,
        )
        self.assertIn("Project aangemaakt", result.stdout)
        self.assertTrue((output / "cli-app/src/cli_app/__init__.py").is_file())

    def test_cli_invalid_name_reports_error_without_traceback(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = generator.main(["../buiten", "--type", "python", "--output", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("Fout:", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_cli_rejects_unknown_type(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            generator.main(["voorbeeld", "--type", "web"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
