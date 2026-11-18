"""Versies en herkomstinformatie zonder bestaande projecten bij te werken."""

import copy
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import create_project as generator


class ManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.manifest = copy.deepcopy(generator.load_manifest())
        self.path = self.root / "manifest.json"

    def write_manifest(self):
        self.path.write_text(json.dumps(self.manifest), encoding="utf-8")
        return patch.object(generator, "MANIFEST_PATH", self.path)

    def test_all_templates_record_exact_version_and_no_personal_paths(self):
        for kind in self.manifest["templates"]:
            with self.subTest(kind=kind):
                target = generator.create_project(f"demo-{kind}", self.root, project_type=kind,
                                                  template_version="1.0.0")
                text = (target / generator.METADATA_FILE).read_text(encoding="utf-8")
                metadata = json.loads(text)
                self.assertEqual(metadata["template"], {"id": kind, "version": "1.0.0"})
                self.assertEqual(metadata["project"]["name"], f"demo-{kind}")
                self.assertEqual(metadata["schema_version"], 1)
                self.assertNotIn(str(self.root), text)

    def test_unavailable_versions_do_not_create_parent(self):
        for version in ("", "0.9.0", "2.0.0", "latest", "../1.0.0"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                generator.create_project("demo", self.root / "output", template_version=version)
        self.assertFalse((self.root / "output").exists())

    def test_manifest_changes_affect_only_new_projects(self):
        old = generator.create_project("oud-project", self.root)
        before = {p.relative_to(old): p.read_bytes() for p in old.rglob("*") if p.is_file()}
        self.manifest["templates"]["python"]["version"] = "1.1.0"
        with self.write_manifest():
            new = generator.create_project("nieuw-project", self.root, template_version="1.1.0")
            with self.assertRaises(ValueError):
                generator.create_project("verkeerde-versie", self.root, template_version="1.0.0")
            with self.assertRaises(FileExistsError):
                generator.create_project("oud-project", self.root, template_version="1.1.0")
        self.assertEqual(json.loads((new / generator.METADATA_FILE).read_text())["template"]["version"], "1.1.0")
        self.assertEqual(before, {p.relative_to(old): p.read_bytes() for p in old.rglob("*") if p.is_file()})

    def test_invalid_manifest_schemas_and_versions_fail_before_writes(self):
        mutations = (
            lambda m: m.update(schema_version=2),
            lambda m: m.update(schema_version=True),
            lambda m: m["templates"]["python"].update(version="latest"),
            lambda m: m["templates"]["python"].update(version="01.0.0"),
        )
        original = copy.deepcopy(self.manifest)
        for mutate in mutations:
            self.manifest = copy.deepcopy(original)
            mutate(self.manifest)
            with self.write_manifest(), self.assertRaises(ValueError):
                generator.create_project("demo", self.root / "output")
            self.assertFalse((self.root / "output").exists())

    def test_unsafe_duplicate_and_reserved_paths_are_rejected(self):
        original = copy.deepcopy(self.manifest)
        for path in ("../escape", "/escape", "C:/escape", "a\\b", ".git/config",
                     ".env", ".env.production", generator.METADATA_FILE,
                     "README.md", "readme.md", "a/./b"):
            with self.subTest(path=path):
                self.manifest = copy.deepcopy(original)
                self.manifest["templates"]["python"]["files"].append(path)
                with self.write_manifest(), self.assertRaises(ValueError):
                    generator.create_project("demo", self.root / "output")
                self.assertFalse((self.root / "output").exists())

    def test_manifest_file_list_is_used_at_generation_time(self):
        self.manifest["templates"]["python"]["files"] = ["README.md"]
        with self.write_manifest():
            target = generator.create_project("klein-project", self.root)
        self.assertEqual({p.name for p in target.iterdir()}, {"README.md", generator.METADATA_FILE})

    def test_cli_exact_version_and_mismatch(self):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = generator.main(["demo", "--type", "web", "--output", str(self.root),
                                     "--template-version", "1.0.0"])
            mismatch = generator.main(["ander", "--type", "web", "--output", str(self.root),
                                       "--template-version", "9.0.0"])
        self.assertEqual(result, 0)
        self.assertEqual(mismatch, 1)
        self.assertFalse((self.root / "ander").exists())

    def test_menu_pins_confirmed_version_if_manifest_changes(self):
        answers = iter(["1", "demo", str(self.root)])
        def answer(prompt):
            if prompt.startswith("Aanmaken?"):
                self.manifest["templates"]["python"]["version"] = "1.1.0"
                self.path.write_text(json.dumps(self.manifest), encoding="utf-8")
                return "ja"
            return next(answers)
        with self.write_manifest(), patch("builtins.input", side_effect=answer), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(generator.main([]), 1)
        self.assertFalse((self.root / "demo").exists())

    def test_existing_project_without_metadata_is_untouched(self):
        existing = self.root / "bestaand"
        existing.mkdir()
        marker = existing / "eigen-bestand.txt"
        marker.write_bytes(b"fictieve bestaande inhoud")
        with self.assertRaises(FileExistsError):
            generator.create_project("bestaand", self.root, template_version="1.0.0")
        self.assertEqual(list(existing.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b"fictieve bestaande inhoud")

    def test_corrupt_manifest_cli_fails_cleanly_without_writes(self):
        script = self.root / "create_project.py"
        script.write_bytes(Path(generator.__file__).read_bytes())
        templates = self.root / "templates"
        templates.mkdir()
        (templates / "manifest.json").write_text("{invalid", encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(script), "demo", "--type", "python",
                                 "--output", str(self.root / "output")],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("manifest", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "output").exists())


if __name__ == "__main__":
    unittest.main()
