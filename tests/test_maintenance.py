"""Onderhoudscontrole: feiten, aanbevelingen en strikt alleen-lezen gedrag."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import maintenance
import quality
import studio


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        for name in quality.REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("pass\n" if path.suffix == ".py" else "# Voorbeeld\n", encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
        (self.root / "create_project.py").write_text("TEMPLATE_FILES = ('README.md', 'pyproject.toml')\n", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests/test_sample.py").write_text("raise RuntimeError('NIET UITVOEREN')\n", encoding="utf-8")
        self.manifest = self.root / "templates/manifest.json"
        self.data = {"schema_version": 1, "templates": {
            kind: {"version": "1.0.0", "label": kind, "directory": kind + "-app",
                   "files": ["README.md", "pyproject.toml"]}
            for kind in studio.PROJECT_TYPES}}
        self.save()
        directory = self.root / "templates/python-app"
        directory.mkdir()
        (directory / "README.md").write_text("# Voorbeeld\n", encoding="utf-8")
        self.config = directory / "pyproject.toml"
        self.config.write_text('[project]\nname="PROJECT_NAME"\nversion="0.1.0"\n', encoding="utf-8")
        for item in (patch.object(quality, "STUDIO_ROOT", self.root),
                     patch.object(studio, "MANIFEST_PATH", self.manifest)):
            item.start()
            self.addCleanup(item.stop)

    def save(self):
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")

    def cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(["maintenance", *args])
        return code, out.getvalue(), err.getvalue()

    def test_read_only_without_code_tests_subprocesses_or_network(self):
        (self.root / ".env").write_text("FICTIEF_GEHEIM", encoding="utf-8")
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        real_open = os.open
        def guarded(path, flags, *args, **kwargs):
            self.assertNotEqual(Path(path).name, ".env")
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
            return real_open(path, flags, *args, **kwargs)
        with patch.object(studio, "run_bounded", side_effect=AssertionError("Geen subprocess")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("Geen subprocessen")), \
             patch.object(quality, "run_tests", side_effect=AssertionError("Geen tests")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")), \
             patch("builtins.input", side_effect=AssertionError("Geen prompt")), \
             patch.object(os, "open", side_effect=guarded):
            code, out, err = self.cli("--format", "json")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()})
        self.assertNotIn("FICTIEF_GEHEIM", out + err)

    def test_categories_and_coverage_are_explicit(self):
        code, out, _ = self.cli("--format", "json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["command"], "maintenance")
        self.assertFalse(data["tests_requested"])
        for item in data["results"]:
            self.assertTrue(item["label"].startswith(("VASTSTELLING | ", "AANBEVELING | ")))
            if item["label"].startswith("AANBEVELING"):
                self.assertEqual(item["status"], "WARN")
        coverage = next(item for item in data["results"] if item["label"].endswith("Testdekking"))
        self.assertEqual(coverage["status"], "SKIP")
        self.assertIn("aanvullende analyse", coverage["message"])

    def test_formats_are_consistent(self):
        for fmt in ("text", "json", "markdown"):
            code, out, _ = self.cli("--format", fmt)
            self.assertEqual(code, 0, out)
            self.assertIn("VASTSTELLING", out)
            self.assertIn("AANBEVELING", out)

    def test_missing_docs_release_files_and_broken_links_fail(self):
        for name in ("docs/RELEASE.md", "CHANGELOG.md"):
            with self.subTest(name=name):
                path = self.root / name
                content = path.read_bytes()
                path.unlink()
                self.assertEqual(self.cli()[0], 1)
                path.write_bytes(content)
        (self.root / "README.md").write_text("[ontbreekt](afwezig.md)", encoding="utf-8")
        self.assertEqual(self.cli()[0], 1)

    def test_generator_manifest_mismatch_and_bad_metadata_fail(self):
        (self.root / "create_project.py").write_text("TEMPLATE_FILES = ('ander.py',)\n", encoding="utf-8")
        self.assertEqual(self.cli()[0], 1)
        self.manifest.write_text('{"FICTIEF_GEHEIM":', encoding="utf-8")
        code, out, err = self.cli("--format", "json")
        self.assertEqual(code, 1)
        json.loads(out)
        self.assertNotIn("FICTIEF_GEHEIM", out + err)

    def test_versions_are_independent_and_invalid_values_fail(self):
        self.assertEqual(self.cli()[0], 0)  # Project 0.1.0 versus template 1.0.0 is geldig.
        self.config.write_text('[project]\nversion="01.0.0"\n', encoding="utf-8")
        self.assertEqual(self.cli()[0], 1)

    def test_dynamic_package_version_and_unknown_studio_version_are_skipped(self):
        self.config.write_text('[project]\ndynamic=["version"]\n', encoding="utf-8")
        code, out, _ = self.cli("--format", "json")
        self.assertEqual(code, 0)
        rows = json.loads(out)["results"]
        for label in ("Projectversie python", "Studioreleaseversie"):
            self.assertEqual(next(r for r in rows if r["label"].endswith(label))["status"], "SKIP")

    def test_invalid_and_duplicate_changelog_versions_fail(self):
        for content in ("## [1.0]\n", "## [1.0.0]\n## [1.0.0]\n", "# Geen secties\n"):
            (self.root / "CHANGELOG.md").write_text(content, encoding="utf-8")
            self.assertEqual(self.cli()[0], 1)

    def test_no_test_files_is_structure_failure_not_coverage_claim(self):
        (self.root / "tests/test_sample.py").rename(self.root / "tests/sample.py")
        code, out, _ = self.cli("--format", "json")
        self.assertEqual(code, 1)
        rows = json.loads(out)["results"]
        self.assertTrue(any(r["status"] == "FAIL" and r["label"].endswith("Tests-structuur") for r in rows))
        self.assertEqual(next(r for r in rows if r["label"].endswith("Testdekking"))["status"], "SKIP")

    def test_traversal_and_reparse_paths_are_rejected(self):
        self.data["templates"]["python"]["directory"] = "../buiten"
        self.save()
        self.assertEqual(self.cli()[0], 1)
        with patch.object(Path, "lstat", return_value=SimpleNamespace(
                st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)):
            self.assertEqual(self.cli()[0], 1)

    def test_limits_interrupt_and_unexpected_errors_have_safe_json(self):
        for error, expected in ((ValueError("FICTIEF_GEHEIM"), 1),
                                (RuntimeError("FICTIEF_GEHEIM"), 1), (KeyboardInterrupt(), 130)):
            with patch.object(quality, "static_checks", side_effect=error):
                code, out, err = self.cli("--format", "json")
            self.assertEqual(code, expected)
            self.assertEqual(json.loads(out)["exit_code"], expected)
            self.assertNotIn("FICTIEF_GEHEIM", out + err)
        with patch.object(quality, "MAX_ITEMS", 0):
            self.assertEqual(self.cli()[0], 1)

    def test_write_execution_and_root_flags_are_not_available(self):
        for option in ("--output", "--run-tests", "--root", "--fix"):
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                studio.main(["maintenance", option])
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
