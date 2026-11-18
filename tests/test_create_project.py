"""Generatorcontroles met tijdelijke mappen en echte gegenereerde projecten."""

import contextlib
import io
import os
import shutil
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
            generator.main(["voorbeeld", "--type", "onbekend"])
        self.assertEqual(error.exception.code, 2)

    def test_web_invalid_names_never_create_output(self):
        output = self.root / "output"
        for name in ("../buiten", "a/b", "a\\b", "<script>", 'a"b', "a b", "con", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                generator.create_project(name, output, project_type="web")
        self.assertFalse(output.exists())

    def test_web_preserves_existing_targets(self):
        for name, kind in (("leeg", "empty"), ("gevuld", "full"), ("bestand", "file")):
            with self.subTest(kind=kind):
                target = self.root / name
                if kind == "file":
                    target.write_text("fictief", encoding="utf-8")
                else:
                    target.mkdir()
                    if kind == "full":
                        (target / "notitie.txt").write_text("fictief", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    generator.create_project(name, self.root, project_type="web")
                if kind == "empty":
                    self.assertEqual(list(target.iterdir()), [])
                else:
                    marker = target if kind == "file" else target / "notitie.txt"
                    self.assertEqual(marker.read_text(encoding="utf-8"), "fictief")

    def test_web_only_known_files_are_copied(self):
        template = self.root / "web-template"
        for relative in generator.WEB_TEMPLATE_FILES:
            target = template / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((generator.WEB_TEMPLATE_DIR / relative).read_bytes())
        for relative in (".venv/config", "__pycache__/cache.pyc", ".git/config",
                         "node_modules/test.js", ".env", "public/app.js.bak",
                         "persoonlijk.txt", "public/prive.json"):
            target = template / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fictief", encoding="utf-8")
        with patch.object(generator, "WEB_TEMPLATE_DIR", template):
            target = generator.create_project("schone-webapp", self.root / "output", project_type="web")
        actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        self.assertEqual(actual, set(generator.WEB_TEMPLATE_FILES))

    def test_web_missing_source_leaves_no_project(self):
        with patch.object(generator, "WEB_TEMPLATE_DIR", self.root / "ontbreekt"):
            with self.assertRaises(ValueError):
                generator.create_project("voorbeeld", self.root / "output", project_type="web")
        self.assertFalse((self.root / "output").exists())

    def test_web_source_links_are_rejected(self):
        info = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        with patch.object(Path, "lstat", return_value=info):
            with self.assertRaises(ValueError):
                generator.render_template("voorbeeld", "voorbeeld", project_type="web")

    def test_api_rejects_unknown_type_without_creating_output(self):
        with self.assertRaises(ValueError):
            generator.create_project("voorbeeld", self.root / "output", project_type="onbekend")
        self.assertFalse((self.root / "output").exists())

    def test_web_cli_from_other_working_directory(self):
        output = self.root / "met spaties"
        result = self.run_python(
            str(ROOT / "create_project.py"), "mijn-website", "--type", "web",
            "--output", str(output), cwd=self.root,
        )
        self.assertIn("node --test", result.stdout)
        self.assertTrue((output / "mijn-website/public/index.html").is_file())
        self.assertFalse((output / "mijn-website/pyproject.toml").exists())

    def test_automation_invalid_names_create_nothing(self):
        for name in ("../buiten", "a/b", "a\\b", "a b", "con", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                generator.create_project(name, self.root / "output", project_type="automation")
        self.assertFalse((self.root / "output").exists())

    def test_automation_preserves_existing_targets(self):
        target = self.root / "bestaand"
        target.mkdir()
        with self.assertRaises(FileExistsError):
            generator.create_project("bestaand", self.root, project_type="automation")
        marker = target / "behouden.txt"
        marker.write_bytes(b"fictief")
        with self.assertRaises(FileExistsError):
            generator.create_project("bestaand", self.root, project_type="automation")
        self.assertEqual(marker.read_bytes(), b"fictief")

    def test_automation_copies_only_known_files(self):
        template = self.root / "automation-template"
        for relative in generator.AUTOMATION_TEMPLATE_FILES:
            target = template / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((generator.AUTOMATION_TEMPLATE_DIR / relative).read_bytes())
        for relative in ("input/prive.txt", "output/prive.txt", ".env", "run.log",
                         ".git/config", ".venv/config", "__pycache__/cached.pyc"):
            target = template / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fictief")
        with patch.object(generator, "AUTOMATION_TEMPLATE_DIR", template):
            target = generator.create_project("mijn-taak", self.root / "output", project_type="automation")
        actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        expected = {p.replace("project_package", "mijn_taak") for p in generator.AUTOMATION_TEMPLATE_FILES}
        self.assertEqual(actual, expected)

    def test_automation_missing_source_leaves_no_project(self):
        with patch.object(generator, "AUTOMATION_TEMPLATE_DIR", self.root / "ontbreekt"):
            with self.assertRaises(ValueError):
                generator.create_project("voorbeeld", self.root / "output", project_type="automation")
        self.assertFalse((self.root / "output").exists())

    def test_automation_source_links_are_rejected(self):
        info = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        with patch.object(Path, "lstat", return_value=info), self.assertRaises(ValueError):
            generator.render_template("voorbeeld", "voorbeeld", project_type="automation")

    def test_generated_automation_cli_tests_and_task_work_independently(self):
        output = self.root / "met spaties"
        self.run_python(str(ROOT / "create_project.py"), "mijn-taak", "--type", "automation",
                        "--output", str(output), cwd=self.root)
        target = output / "mijn-taak"
        for path in target.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("PROJECT_NAME", text)
                self.assertNotIn("project_package", text)
        metadata = tomllib.loads((target / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["name"], "mijn-taak")
        self.assertEqual(metadata["project"]["dependencies"], [])
        self.assertFalse((target / ".git").exists())
        standalone = self.root / "zelfstandig"
        shutil.copytree(target, standalone)
        source = self.root / "fictieve-input"
        source.mkdir()
        (source / "voorbeeld.txt").write_bytes(b"hallo\n")
        destination = self.root / "nieuwe-uitvoer"
        with patch.object(generator, "AUTOMATION_TEMPLATE_DIR", self.root / "onbeschikbaar"):
            self.run_python("-S", "-B", "-m", "unittest", "discover", "-s", "tests", "-v", cwd=standalone)
            arguments = ("-E", "-S", "-B", "-m", "mijn_taak", str(source), str(destination))
            self.run_python(*arguments, cwd=standalone / "src", isolated=False)
            self.assertFalse(destination.exists())
            self.run_python(*arguments, "--apply", cwd=standalone / "src", isolated=False)
        self.assertEqual((destination / "voorbeeld.txt").read_bytes(), b"HALLO\n")
        self.assertEqual((source / "voorbeeld.txt").read_bytes(), b"hallo\n")

    def test_ai_invalid_names_never_create_output(self):
        output = self.root / "output"
        for name in ("../buiten", "a/b", "a\\b", "a b", "con", "class", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                generator.create_project(name, output, project_type="ai")
        self.assertFalse(output.exists())

    def test_ai_preserves_existing_targets(self):
        for name, is_file in (("bestaand", False), ("bestand", True)):
            target = self.root / name
            if is_file:
                target.write_text("fictief", encoding="utf-8")
            else:
                target.mkdir()
            with self.assertRaises(FileExistsError):
                generator.create_project(name, self.root, project_type="ai")
            if is_file:
                self.assertEqual(target.read_text(encoding="utf-8"), "fictief")
            else:
                self.assertEqual(list(target.iterdir()), [])

    def test_ai_copies_example_but_no_secrets_or_temporary_files(self):
        template = self.root / "ai-template"
        for relative in generator.AI_TEMPLATE_FILES:
            path = template / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((generator.AI_TEMPLATE_DIR / relative).read_bytes())
        for relative in (".env", ".env.local", ".env.production", ".venv/config",
                         ".git/config", "__pycache__/cached.pyc", "persoonlijk.txt",
                         "src/project_package/config.py.bak"):
            path = template / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fictieve-lokale-gegevens", encoding="utf-8")
        with patch.object(generator, "AI_TEMPLATE_DIR", template):
            target = generator.create_project("veilige-demo", self.root / "output", project_type="ai")
        expected = {name.replace("project_package", "veilige_demo")
                    for name in generator.AI_TEMPLATE_FILES}
        actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        self.assertEqual(actual, expected)
        example = (target / ".env.example").read_text(encoding="utf-8")
        self.assertIn("AI_API_KEY=\n", example)
        self.assertIn("!.env.example", (target / ".gitignore").read_text(encoding="utf-8"))

    def test_ai_missing_source_leaves_no_project(self):
        with patch.object(generator, "AI_TEMPLATE_DIR", self.root / "ontbreekt"):
            with self.assertRaises(ValueError):
                generator.create_project("voorbeeld", self.root / "output", project_type="ai")
        self.assertFalse((self.root / "output").exists())

    def test_ai_source_links_are_rejected(self):
        info = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        with patch.object(Path, "lstat", return_value=info):
            with self.assertRaises(ValueError):
                generator.render_template("voorbeeld", "voorbeeld", project_type="ai")

    def test_ai_cli_from_other_working_directory(self):
        output = self.root / "met spaties"
        self.run_python(str(ROOT / "create_project.py"), "mijn-ai-app", "--type", "ai",
                        "--output", str(output), cwd=self.root)
        self.assertTrue((output / "mijn-ai-app/src/mijn_ai_app/config.py").is_file())
        self.assertTrue((output / "mijn-ai-app/.env.example").is_file())
        self.assertFalse((output / "mijn-ai-app/.env").exists())

    def test_generated_ai_project_works_independently_without_keys(self):
        target = generator.create_project("mijn-ai-app", self.root / "output", project_type="ai")
        for path in target.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("PROJECT_NAME", text)
                self.assertNotIn("project_package", text)
        metadata = tomllib.loads((target / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["name"], "mijn-ai-app")
        self.assertEqual(metadata["project"]["dependencies"], [])
        self.assertFalse((target / ".git").exists())
        standalone = self.root / "zelfstandige-ai"
        shutil.copytree(target, standalone)
        # Een minimale omgeving zonder doorgifte van sleutels uit het echte proces.
        environment = {"SystemRoot": os.environ.get("SystemRoot", "")}
        cases = (
            (["-I", "-S", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], standalone),
            (["-E", "-S", "-B", "-m", "mijn_ai_app"], standalone / "src"),
        )
        with patch.object(generator, "AI_TEMPLATE_DIR", self.root / "onbeschikbaar"):
            for arguments, cwd in cases:
                result = subprocess.run([sys.executable, *arguments], cwd=cwd, env=environment,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if cwd == standalone:
                    self.assertIn("Ran 13 tests", result.stderr)
                else:
                    self.assertEqual(result.stdout, "[demo:demo-model] Geef een korte begroeting.\n")

    def test_generated_webproject_works_after_moving_without_template(self):
        target = generator.create_project("mijn-website", self.root / "output", project_type="web")
        for path in target.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("PROJECT_NAME", text)
                self.assertNotIn("project_package", text)
        self.assertIn("<title>mijn-website</title>",
                      (target / "public/index.html").read_text(encoding="utf-8"))
        self.assertFalse((target / ".git").exists())
        # Alleen het project gaat mee; geen studio, lokale venv of node_modules.
        standalone = self.root / "zelfstandig"
        shutil.copytree(target, standalone)
        with patch.object(generator, "WEB_TEMPLATE_DIR", self.root / "niet-beschikbaar"):
            self.run_python("-S", "-B", "-m", "unittest", "discover", "-s", "tests", "-v", cwd=standalone)
            node = shutil.which("node")
            if not node:
                self.skipTest("Node.js ontbreekt; JavaScript-integratie niet uitgevoerd.")
            result = subprocess.run(
                [node, "--test", "--test-reporter=tap", "tests/counter.test.cjs"], cwd=standalone,
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("# pass 6", result.stdout)


if __name__ == "__main__":
    unittest.main()
