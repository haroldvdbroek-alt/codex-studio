"""Lokale versiecontrole zonder projectcode, Git of netwerk."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio


class UpdatesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "Projects"
        self.root.mkdir()
        self.manifest = self.base / "manifest.json"
        self.catalog = {"schema_version": 1, "templates": {
            "python": {"label": "Python", "directory": "python-app",
                       "version": "1.0.0", "files": ["README.md"]}}}
        self.save_manifest()
        mocked = patch.object(studio, "MANIFEST_PATH", self.manifest)
        mocked.start()
        self.addCleanup(mocked.stop)
        self.directory = self.root / "voorbeeld"
        self.directory.mkdir()
        self.data = {"schema_version": 1, "project": {"name": "Voorbeeld"},
                     "generator": {"version": None},
                     "template": {"id": "python", "version": "1.0.0"}}
        self.save_project()

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.catalog), encoding="utf-8")

    def save_project(self):
        (self.directory / studio.METADATA_FILE).write_text(json.dumps(self.data), encoding="utf-8")

    def cli(self, args=None):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(args or ["updates", "--root", str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_numeric_comparisons(self):
        for current, local, expected in (
            ("1.0.0", "1.0.0", "ACTUEEL"),
            ("1.0.0", "1.0.1", "NIEUW_BESCHIKBAAR"),
            ("1.0.0", "1.1.0", "NIEUW_BESCHIKBAAR"),
            ("1.9.0", "1.10.0", "NIEUW_BESCHIKBAAR"),
            ("1.9.9", "2.0.0", "GROTE_WIJZIGING"),
            ("2.0.0", "1.9.9", "PROJECT_LOOPT_VOOR"),
            ("1.0.1", "1.0.0", "PROJECT_LOOPT_VOOR"),
            ("0.1.0", "0.2.0", "NIEUW_BESCHIKBAAR"),
        ):
            with self.subTest(current=current, local=local):
                self.data["template"]["version"] = current
                self.catalog["templates"]["python"]["version"] = local
                self.save_project()
                self.save_manifest()
                code, output, error = self.cli()
                self.assertEqual(code, 0)
                self.assertIn(expected, output)
                self.assertIn(current, output)
                self.assertIn(local, output)
                self.assertFalse(error)

    def test_invalid_project_versions(self):
        for value in ("1.0", "01.0.0", "1.0.0-beta", "1.0.0+build", " 1.0.0", "1.0.0\n", True, 1, [], "9" * 201):
            with self.subTest(value=value):
                self.data["template"]["version"] = value
                self.save_project()
                code, output, _ = self.cli()
                self.assertEqual(code, 1)
                self.assertIn("ONBEKEND", output)
                self.assertIn("ongeldig", output)

    def test_missing_unknown_and_invalid_are_distinct(self):
        self.data["template"]["version"] = None
        self.save_project()
        self.assertEqual(self.cli()[0], 0)
        self.assertIn("onbekend", self.cli()[1])
        del self.data["template"]["version"]
        self.save_project()
        self.assertEqual(self.cli()[0], 1)
        self.assertIn("ontbreekt", self.cli()[1])

    def test_unknown_type_is_reported(self):
        self.data["template"]["id"] = "toekomstig"
        self.save_project()
        code, output, _ = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("Onbekend templatetype", output)
        self.assertIn("toekomstig", output)

    def test_missing_metadata_is_counted_and_not_read_recursively(self):
        folder = self.root / "niet-geregistreerd"
        folder.mkdir()
        nested = folder / "nested"
        nested.mkdir()
        (nested / studio.METADATA_FILE).write_text("ongeldig", encoding="utf-8")
        rows, warnings, missing = studio.project_updates(self.root)
        self.assertEqual((len(rows), warnings, missing), (1, [], 1))

    def test_malformed_metadata_does_not_leak_content(self):
        for text in ('{"schema_version":1,"schema_version":1}', '{"private":"voorbeeld-geheim",', '[]'):
            with self.subTest(text=text):
                (self.directory / studio.METADATA_FILE).write_text(text, encoding="utf-8")
                code, out, err = self.cli()
                self.assertEqual(code, 1)
                self.assertIn("ONBEKEND", out)
                self.assertNotIn("voorbeeld-geheim", out + err)

    def test_missing_generator_version_and_invalid_schema(self):
        for change in (lambda: self.data.update(schema_version=True),
                       lambda: self.data.update(generator={}),
                       lambda: self.data.update(project={})):
            with self.subTest(change=change):
                original = json.loads(json.dumps(self.data))
                change()
                self.save_project()
                self.assertEqual(self.cli()[0], 1)
                self.data = original

    def test_manifest_versions_missing_unknown_invalid(self):
        spec = self.catalog["templates"]["python"]
        for value, word in ((None, "onbekend"), ("bad", "ongeldig")):
            spec["version"] = value
            self.save_manifest()
            self.assertEqual(self.cli()[0], 1)
            self.assertIn(word, self.cli()[1])
        del spec["version"]
        self.save_manifest()
        self.assertIn("ontbreekt", self.cli()[1])

    def test_invalid_manifest_and_missing_template(self):
        self.catalog["templates"] = {}
        self.save_manifest()
        self.assertEqual(self.cli()[0], 1)
        self.assertIn("ontbreekt in lokaal manifest", self.cli()[1])
        self.manifest.write_text("[]", encoding="utf-8")
        self.assertEqual(self.cli()[0], 1)

    def test_manifest_path_traversal_rejected(self):
        for path in ("../outside", "C:\\outside", "file:stream", "a/../../outside"):
            with self.subTest(path=path):
                self.catalog["templates"]["python"]["files"] = [path]
                self.save_manifest()
                self.assertEqual(self.cli()[0], 1)
                self.assertIn("ONBEKEND", self.cli()[1])

    def test_default_home_and_missing_root_do_not_create_directories(self):
        with patch.object(studio.Path, "home", return_value=self.base):
            self.assertEqual(self.cli(["updates"])[0], 0)
        absent = self.base / "absent"
        self.assertEqual(self.cli(["updates", "--root", str(absent)])[0], 1)
        self.assertFalse(absent.exists())

    def test_read_only_and_only_required_files_opened(self):
        (self.directory / "app.py").write_text("raise RuntimeError('niet uitvoeren')", encoding="utf-8")
        (self.directory / ".env").write_text("PRIVATE=voorbeeld", encoding="utf-8")
        def snapshot():
            return {p.relative_to(self.base): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in self.base.rglob("*") if p.is_file()}
        before = snapshot()
        real_open = os.open
        allowed = {self.manifest, self.directory / studio.METADATA_FILE}
        def guarded_open(path, flags, *args, **kwargs):
            self.assertIn(Path(path), allowed)
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
            return real_open(path, flags, *args, **kwargs)
        with patch.object(studio.os, "open", side_effect=guarded_open), \
             patch.object(studio, "run_bounded", side_effect=AssertionError("Geen subprocess")), \
             patch.object(studio.subprocess, "Popen", side_effect=AssertionError("Geen subprocess")):
            self.assertEqual(self.cli()[0], 0)
        self.assertEqual(before, snapshot())

    def test_reparse_project_is_skipped_without_reading_metadata(self):
        real_stat = Path.lstat
        def mocked(path):
            if path == self.directory:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return real_stat(path)
        with patch.object(Path, "lstat", mocked), \
             patch.object(studio, "read_project_data", side_effect=AssertionError("Niet lezen")):
            rows, warnings, _ = studio.project_updates(self.root)
        self.assertEqual(rows, [])
        self.assertEqual(len(warnings), 1)

    def test_reparse_root_is_rejected(self):
        real_stat = Path.lstat
        def mocked(path):
            if path == self.root:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return real_stat(path)
        with patch.object(Path, "lstat", mocked):
            self.assertEqual(self.cli()[0], 1)

    def test_symlink_metadata_is_not_followed(self):
        metadata = self.directory / studio.METADATA_FILE
        target = self.base / "outside.json"
        metadata.rename(target)
        try:
            metadata.symlink_to(target)
        except OSError:
            self.skipTest("Symlinks zijn niet toegestaan op dit systeem")
        self.assertEqual(self.cli()[0], 1)

    def test_cancellation(self):
        with patch.object(studio, "project_updates", side_effect=KeyboardInterrupt):
            self.assertEqual(self.cli()[0], 130)

    def test_real_cli_without_bytecode_flag_creates_no_files(self):
        # Een aparte studio voorkomt dat bestaande caches een schrijffout verbergen.
        app = self.base / "studio"
        app.mkdir()
        source = Path(studio.__file__).parent
        for name in ("studio.py", "process_runner.py"):
            (app / name).write_bytes((source / name).read_bytes())
        (app / "templates").mkdir()
        (app / "templates" / "manifest.json").write_bytes(self.manifest.read_bytes())
        before = {p.relative_to(self.base): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.base.rglob("*") if p.is_file()}
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        result = subprocess.run([sys.executable, str(app / "studio.py"), "updates", "--root", str(self.root)],
                                cwd=self.base, env=env, capture_output=True, timeout=15, shell=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {p.relative_to(self.base): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.base.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
