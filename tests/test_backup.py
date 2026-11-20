"""Broncodeback-ups: alleen tijdelijke mappen en expliciete nagebootste toestemming."""

from contextlib import redirect_stdout, redirect_stderr
import hashlib
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
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio
import backup


class BackupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "Projects"
        self.root.mkdir()
        self.source = self.root / "voorbeeld"
        self.source.mkdir()
        self.output = self.base / "Backups"
        self.metadata = {"schema_version": 1, "project": {"name": "Voorbeeld"},
                         "generator": {"version": None}, "template": {"id": "python", "version": "1.0.0"}}
        self.file(studio.METADATA_FILE, json.dumps(self.metadata))
        self.file("README.md", "# Voorbeeld\n")
        self.file("src/voorbeeld/app.py", "raise RuntimeError('NIET UITVOEREN')\n")
        self.file("tests/test_app.py", "raise RuntimeError('NIET TESTEN')\n")

    def file(self, name, content="fictief"):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def plan(self):
        return backup.make_plan(self.root, "voorbeeld", self.output)

    def cli(self, create=False):
        output, error = StringIO(), StringIO()
        args = ["backup", "voorbeeld", "--root", str(self.root), "--output", str(self.output)]
        if create:
            args.append("--create")
        with redirect_stdout(output), redirect_stderr(error):
            code = studio.main(args)
        return code, output.getvalue(), error.getvalue()

    def snapshot(self):
        return {p.relative_to(self.source): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.source.rglob("*") if p.is_file()}

    def test_preview_is_read_only_even_with_create_confirmation_mock(self):
        before = self.snapshot()
        with patch("builtins.input", side_effect=AssertionError("Preview vraagt geen toestemming")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("Geen processen")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")):
            code, output, error = self.cli()
        self.assertEqual(code, 0, error)
        self.assertIn("OPNEMEN", output)
        self.assertIn("UITSLUITEN", output)
        self.assertIn("niets aangemaakt", output)
        self.assertFalse(self.output.exists())
        self.assertEqual(before, self.snapshot())

    def test_default_root_and_destination(self):
        with patch.object(Path, "home", return_value=self.base), \
             redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(studio.main(["backup", "voorbeeld"]), 0)
        self.assertFalse((self.base / "StudioBackups").exists())

    def test_sensitive_and_unknown_paths_excluded_without_opening_contents(self):
        excluded = (".env", ".env.example", ".ENV.production", "server.pem", "id_rsa", "credentials.json",
                    "src/voorbeeld/api_key.py", "data/klanten.py", "personal/notities.md", "private/foto.md",
                    ".git/config", ".venv/pyvenv.cfg", "node_modules/demo.js", "__pycache__/app.pyc",
                    "resultaat.csv", "klanten.sqlite", "oud.zip", "docs/token.md", "work/ander.py", "notes.txt")
        for name in excluded:
            self.file(name)
        real = os.open
        opened = []
        def guarded(path, flags, *args, **kwargs):
            opened.append(Path(path))
            self.assertEqual(Path(path).name, studio.METADATA_FILE)
            return real(path, flags, *args, **kwargs)
        with patch.object(backup.os, "open", side_effect=guarded):
            plan = self.plan()
        self.assertTrue(opened)
        names = {item.name for item in plan.files}
        for name in excluded:
            self.assertNotIn(name, names)
        self.assertIn(".env.example", dict(plan.excluded))
        self.assertIn("data", dict(plan.excluded))

    def test_allowed_files_cover_all_four_types(self):
        for name in ("public/index.html", "public/app.js", "public/styles.css", "tests/counter.test.cjs",
                     "pyproject.toml", "AGENTS.md", ".gitignore", "docs/handleiding.md",
                     ".github/workflows/python-tests.yml"):
            self.file(name)
        for kind in ("python", "web", "ai", "automation"):
            with self.subTest(kind=kind):
                self.metadata["template"]["id"] = kind
                self.file(studio.METADATA_FILE, json.dumps(self.metadata))
                plan = self.plan()
                self.assertIn("public/index.html", {item.name for item in plan.files})
                self.assertIn(".github/workflows/python-tests.yml", {item.name for item in plan.files})

    def test_create_requires_exact_interactive_confirmation_and_shows_plan_first(self):
        for reply in ("", "nee", "ja", "BACKUP ander-project"):
            with self.subTest(reply=reply), patch.object(sys.stdin, "isatty", return_value=True), \
                 patch("builtins.input", return_value=reply):
                code, out, err = self.cli(create=True)
                self.assertEqual(code, 0, err)
                self.assertIn("Geannuleerd", out)
                self.assertLess(out.index("OPNEMEN"), out.index("Typ exact"))
                self.assertFalse(self.output.exists())

    def test_piped_confirmation_never_creates_archive(self):
        with patch.object(sys.stdin, "isatty", return_value=False), \
             patch("builtins.input", side_effect=AssertionError("Geen piped input")):
            code, out, _ = self.cli(create=True)
        self.assertEqual(code, 0)
        self.assertIn("interactieve", out)
        self.assertFalse(self.output.exists())

    def test_interrupt_and_eof_before_confirmation_write_nothing(self):
        for error in (KeyboardInterrupt, EOFError):
            with self.subTest(error=error), patch.object(sys.stdin, "isatty", return_value=True), \
                 patch("builtins.input", side_effect=error):
                self.assertEqual(self.cli(create=True)[0], 130)
                self.assertFalse(self.output.exists())

    def test_confirmed_archive_is_verified_and_source_unchanged(self):
        before = self.snapshot()
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="BACKUP voorbeeld"), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("Geen processen")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")):
            code, out, err = self.cli(create=True)
        self.assertEqual(code, 0, err)
        self.assertIn("geverifieerd", out)
        archives = list(self.output.glob("*.zip"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(list(self.output.glob("*.incomplete")), [])
        with zipfile.ZipFile(archives[0]) as archive:
            self.assertIsNone(archive.testzip())
            manifest = json.loads(archive.read(backup.MANIFEST_NAME))
            for name, (size, digest) in manifest["files"].items():
                data = archive.read(name)
                self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (size, digest))
            self.assertTrue(all(not name.startswith(("/", "../")) and "\\" not in name for name in archive.namelist()))
        self.assertEqual(before, self.snapshot())

    def test_invalid_project_names_and_metadata_refused(self):
        for name in ("..", "../escape", "C:\\project", "con", "a/b", "a:stream"):
            with self.subTest(name=name), self.assertRaises((OSError, ValueError)):
                backup.make_plan(self.root, name, self.output)
        self.file(studio.METADATA_FILE, "[]")
        self.assertEqual(self.cli()[0], 1)
        self.assertFalse(self.output.exists())

    def test_unsafe_and_nested_destinations_refused(self):
        for output in (self.source, self.source / "backups", Path(r"\\server\share"), Path(r"\\?\C:\folder")):
            with self.subTest(output=output), self.assertRaises((OSError, ValueError)):
                backup.make_plan(self.root, "voorbeeld", output)
        self.assertFalse((self.source / "backups").exists())
        with self.assertRaises((OSError, ValueError)):
            backup.make_plan(self.root, "voorbeeld", self.base / "absent" / "Backups")

    def test_canonical_destination_alias_cannot_bypass_project_boundary(self):
        alias = self.base / "alias"
        alias.mkdir()
        real = Path.resolve
        def resolve(path, *args, **kwargs):
            if path == alias:
                return self.source
            return real(path, *args, **kwargs)
        with patch.object(Path, "resolve", resolve), self.assertRaises(ValueError):
            backup.make_plan(self.root, "voorbeeld", alias / "Backups")
        self.assertFalse((self.source / "Backups").exists())

    def test_real_preview_from_other_directory_creates_no_cache_or_archive(self):
        before = self.snapshot()
        isolated = self.base / "Studio"
        isolated.mkdir()
        for name in ("studio.py", "backup.py", "process_runner.py", "studio_logging.py"):
            (isolated / name).write_bytes((Path(studio.__file__).parent / name).read_bytes())
        studio_before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in isolated.iterdir()}
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        result = subprocess.run([sys.executable, str(isolated / "studio.py"), "backup", "voorbeeld",
                                 "--root", str(self.root), "--output", str(self.output)],
                                cwd=self.base, env=env, shell=False, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"Alleen overzicht", result.stdout)
        self.assertFalse(self.output.exists())
        self.assertEqual(before, self.snapshot())
        self.assertEqual(studio_before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in isolated.iterdir()})

    def test_existing_archive_and_staging_file_never_overwritten(self):
        self.output.mkdir()
        for filename in ("vaste.zip", "vaste.zip.incomplete"):
            path = self.output / filename
            path.write_bytes(b"bestaand")
            with self.subTest(filename=filename), self.assertRaises(FileExistsError):
                backup.make_plan(self.root, "voorbeeld", self.output, archive_name="vaste.zip")
            self.assertEqual(path.read_bytes(), b"bestaand")

    def test_source_changes_after_preview_refuse_all_writes(self):
        plan = self.plan()
        self.file("README.md", "gewijzigd")
        with self.assertRaises(ValueError):
            backup.create_archive(plan)
        self.assertFalse(self.output.exists())

    def test_new_source_file_after_preview_refuses_creation(self):
        plan = self.plan()
        self.file("nieuw.py", "pass")
        with self.assertRaises(ValueError):
            backup.create_archive(plan)
        self.assertFalse(self.output.exists())

    def test_new_content_during_confirmation_requires_new_preview(self):
        def confirm(*args):
            self.file("README.md", "ander resultaat")
            return "BACKUP voorbeeld"
        with patch.object(sys.stdin, "isatty", return_value=True), patch("builtins.input", side_effect=confirm):
            self.assertEqual(self.cli(create=True)[0], 1)
        self.assertFalse(self.output.exists())

    def test_limits_fail_without_creating_destination(self):
        for key in ("MAX_ENTRIES", "MAX_FILES", "MAX_FILE_BYTES", "MAX_TOTAL_BYTES"):
            with self.subTest(key=key), patch.object(backup, key, 0), self.assertRaises(ValueError):
                self.plan()
            self.assertFalse(self.output.exists())
        with patch.object(backup, "TIME_LIMIT", -1), self.assertRaises(ValueError):
            self.plan()

    def test_reparse_source_and_destination_rejected(self):
        self.output.mkdir()
        real = Path.lstat
        for target in (self.source, self.root, self.output):
            def fake(path):
                if path == target:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                return real(path)
            with self.subTest(target=target), patch.object(Path, "lstat", fake), self.assertRaises(ValueError):
                self.plan()

    def test_reparse_entries_are_excluded_without_following(self):
        target = self.file("src/link.py")
        real = Path.lstat
        def fake(path):
            if path == target:
                return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
            return real(path)
        with patch.object(Path, "lstat", fake):
            plan = self.plan()
        self.assertEqual(dict(plan.excluded)["src/link.py"], "symlink of junction")

    def test_hardlinks_excluded(self):
        target = self.file("docs/origineel.md")
        os.link(target, self.source / "kopie.md")
        plan = self.plan()
        self.assertEqual(dict(plan.excluded)["kopie.md"], "hardlink")
        self.assertEqual(dict(plan.excluded)["docs/origineel.md"], "hardlink")

    def test_write_and_verification_failures_leave_only_incomplete_archive(self):
        for target in ("open_source", "verify"):
            with self.subTest(target=target):
                plan = self.plan()
                with patch.object(backup, target, side_effect=OSError("fictieve fout")), self.assertRaises(OSError):
                    backup.create_archive(plan)
                self.assertFalse(plan.archive.exists())
                self.assertTrue(Path(str(plan.archive) + ".incomplete").exists())

    def test_destination_race_does_not_overwrite_existing_file(self):
        plan = self.plan()
        real = os.link
        def race(source, destination, **kwargs):
            Path(destination).write_bytes(b"bestaand doel")
            return real(source, destination, **kwargs)
        with patch.object(os, "link", side_effect=race), self.assertRaises(FileExistsError):
            backup.create_archive(plan)
        self.assertEqual(plan.archive.read_bytes(), b"bestaand doel")

    def test_source_modified_while_reading_is_refused(self):
        plan = self.plan()
        real = backup.open_source
        def open_changed(plan, item):
            stream = real(plan, item)
            self.file(item.name, "veel meer inhoud dan voorheen " * 20)
            return stream
        with patch.object(backup, "open_source", side_effect=open_changed), self.assertRaises(ValueError):
            backup.create_archive(plan)
        self.assertFalse(plan.archive.exists())

    def test_verifier_rejects_changed_archive_content(self):
        stream = __import__("io").BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("voorbeeld.py", b"ander")
        with self.assertRaises(ValueError):
            backup.verify(stream, {"voorbeeld.py": (5, hashlib.sha256(b"goed!").hexdigest())}, float("inf"))


if __name__ == "__main__":
    unittest.main()
