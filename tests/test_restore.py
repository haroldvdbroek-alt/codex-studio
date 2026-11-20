"""Herstel uitsluitend in tijdelijke mappen, zonder projectcode uit te voeren."""

from contextlib import redirect_stdout, redirect_stderr
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backup
import restore
import studio


class RestoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.archive = self.base / "voorbeeld.zip"
        self.output = self.base / "hersteld"
        self.files = {"README.md": b"# Voorbeeld\n", "src/app.py": b"raise RuntimeError('NIET UITVOEREN')\n",
                      "tests/test_app.py": b"raise RuntimeError('NIET TESTEN')\n"}
        self.write_zip()

    def manifest(self, files=None):
        files = self.files if files is None else files
        return {"schema_version": 1, "kind": "source-backup", "excluded_count": 0,
                "files": {name: [len(data), hashlib.sha256(data).hexdigest()] for name, data in files.items()}}

    def write_zip(self, *, files=None, manifest=None, raw=None, extra=(), compression=zipfile.ZIP_STORED):
        files = self.files if files is None else files
        data = self.manifest(files) if manifest is None else manifest
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w", compression=compression) as archive:
                for name, content in files.items():
                    archive.writestr(name, content)
                archive.writestr(backup.MANIFEST_NAME, json.dumps(data).encode() if raw is None else raw)
                for name, content in extra:
                    archive.writestr(name, content)

    def cli(self, create=False):
        args = ["restore", str(self.archive), "--output", str(self.output)]
        if create:
            args.append("--create")
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_preview_verifies_without_creating_files_or_running_code(self):
        before = self.archive.read_bytes(), self.archive.stat().st_mtime_ns
        with patch("builtins.input", side_effect=AssertionError("Geen bevestiging nodig")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("Geen proces")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")):
            code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertIn("PASS SHA-256/CRC", out)
        self.assertIn("niets aangemaakt", out)
        self.assertFalse(self.output.exists())
        self.assertEqual(before, (self.archive.read_bytes(), self.archive.stat().st_mtime_ns))

    def test_exact_confirmation_restores_and_verifies_all_bytes(self):
        before = self.archive.read_bytes()
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="HERSTEL hersteld"), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("Geen proces")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")):
            code, out, err = self.cli(create=True)
        self.assertEqual(code, 0, err)
        self.assertIn("Hersteld en geverifieerd", out)
        self.assertLess(out.index("PASS SHA-256/CRC"), out.index("Typ exact"))
        actual = {p.relative_to(self.output).as_posix(): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(actual, self.files)
        self.assertEqual(self.archive.read_bytes(), before)
        self.assertFalse((self.output / restore.INCOMPLETE).exists())

    def test_cancel_and_noninteractive_mode_do_not_write(self):
        for reply in ("", "nee", "ja", "HERSTEL andere-map"):
            with self.subTest(reply=reply), patch.object(sys.stdin, "isatty", return_value=True), \
                 patch("builtins.input", return_value=reply):
                self.assertEqual(self.cli(create=True)[0], 0)
                self.assertFalse(self.output.exists())
        with patch.object(sys.stdin, "isatty", return_value=False), \
             patch("builtins.input", side_effect=AssertionError("Niet lezen")):
            self.assertEqual(self.cli(create=True)[0], 0)
            self.assertFalse(self.output.exists())

    def test_interrupt_and_eof_before_confirmation(self):
        for error in (KeyboardInterrupt, EOFError):
            with self.subTest(error=error), patch.object(sys.stdin, "isatty", return_value=True), \
                 patch("builtins.input", side_effect=error):
                self.assertEqual(self.cli(create=True)[0], 130)
                self.assertFalse(self.output.exists())

    def test_existing_empty_directory_and_file_are_never_reused(self):
        self.output.mkdir()
        with self.assertRaises(ValueError):
            restore.inspect(self.archive, self.output)
        target = self.base / "bestand"
        target.write_bytes(b"bestaand")
        with self.assertRaises(ValueError):
            restore.inspect(self.archive, target)
        self.assertEqual(target.read_bytes(), b"bestaand")

    def test_traversal_absolute_ads_and_windows_device_names_rejected(self):
        for name in ("../escape.py", "/escape.py", "C:/escape.py", "C:escape.py", "src\\escape.py",
                     "src/../escape.py", "src//app.py", "src/./app.py", "src/con.py", "src/COM¹.py",
                     "src/app.py:stream", "src/app.py.", "src/app.py ", "src/\x1b.py"):
            with self.subTest(name=name):
                self.write_zip(files={name: b"pass"})
                self.assertEqual(self.cli()[0], 1)
                self.assertFalse(self.output.exists())
        self.assertFalse((self.base / "escape.py").exists())

    def test_duplicate_case_and_unicode_alias_names_rejected(self):
        for files, extra in ((self.files, [("README.md", b"dubbel")]),
                             ({"README.md": b"a", "readme.md": b"b"}, []),
                             ({"é.py": b"a", "e\u0301.py": b"b"}, [])):
            with self.subTest(files=files):
                self.write_zip(files=files, extra=extra)
                self.assertEqual(self.cli()[0], 1)
                self.assertFalse(self.output.exists())

    def test_file_directory_prefix_conflict_rejected(self):
        self.write_zip(files={"public/app.js": b"a", "public/app.js/nested.js": b"b"})
        self.assertEqual(self.cli()[0], 1)

    def test_symlink_special_file_and_directory_entries_rejected(self):
        for mode in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFDIR):
            info = zipfile.ZipInfo("src/link.py")
            info.external_attr = (mode | 0o777) << 16
            with self.subTest(mode=mode):
                self.write_zip(extra=[(info, b"../outside")])
                self.assertEqual(self.cli()[0], 1)
                self.assertFalse(self.output.exists())

    def test_missing_extra_and_manifest_listed_as_payload_rejected(self):
        data = self.manifest()
        data["files"]["src/ontbreekt.py"] = [0, hashlib.sha256(b"").hexdigest()]
        self.write_zip(manifest=data)
        self.assertEqual(self.cli()[0], 1)
        self.write_zip(extra=[("src/extra.py", b"pass")])
        self.assertEqual(self.cli()[0], 1)
        data = self.manifest()
        data["files"][backup.MANIFEST_NAME] = [0, "0" * 64]
        self.write_zip(manifest=data)
        self.assertEqual(self.cli()[0], 1)
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("README.md", b"zonder manifest")
        self.assertEqual(self.cli()[0], 1)

    def test_corrupt_json_wrong_schema_types_and_nonstandard_constants(self):
        for raw in (b"geen JSON", b"[]", b'{"schema_version":1,"schema_version":1}',
                    json.dumps(self.manifest()).replace('"schema_version": 1', '"schema_version": true').encode(),
                    json.dumps(self.manifest()).replace('"schema_version": 1', '"schema_version": 2').encode(),
                    json.dumps(self.manifest()).replace('"excluded_count": 0', '"excluded_count": NaN').encode()):
            with self.subTest(raw=raw):
                self.write_zip(raw=raw)
                self.assertEqual(self.cli()[0], 1)
                self.assertFalse(self.output.exists())

    def test_wrong_hash_size_and_invalid_digest_refuse_confirmation(self):
        for expected in ([len(self.files["README.md"]), "0" * 64], [True, "0" * 64],
                         [2, "0" * 64], [0, "niet-een-hash"], None):
            data = self.manifest()
            data["files"]["README.md"] = expected
            with self.subTest(expected=expected):
                self.write_zip(manifest=data)
                with patch("builtins.input", side_effect=AssertionError("Niet bevestigen")):
                    self.assertEqual(self.cli(create=True)[0], 1)
                self.assertFalse(self.output.exists())

    def test_crc_damage_refused_before_writing(self):
        raw = self.archive.read_bytes().replace(b"# Voorbeeld\n", b"# Beschadig\n", 1)
        self.archive.write_bytes(raw)
        self.assertEqual(self.cli()[0], 1)
        self.assertFalse(self.output.exists())

    def test_sensitive_files_not_accepted_even_with_matching_hash(self):
        for name in (".env", ".env.example", ".git/config", "data/klant.py", "src/client_secret.py",
                     "src/.hidden/app.py"):
            with self.subTest(name=name):
                self.write_zip(files={name: b"fictief"})
                self.assertEqual(self.cli()[0], 1)

    def test_limits_reject_without_creating_destination(self):
        for module, attr in ((restore, "MAX_ARCHIVE_BYTES"), (restore, "MAX_CENTRAL_BYTES"),
                             (restore, "MAX_MANIFEST_BYTES"), (backup, "MAX_FILES"),
                             (backup, "MAX_FILE_BYTES"), (backup, "MAX_TOTAL_BYTES")):
            with self.subTest(attr=attr), patch.object(module, attr, 0):
                self.assertEqual(self.cli()[0], 1)
                self.assertFalse(self.output.exists())
        with patch.object(backup, "TIME_LIMIT", -1):
            self.assertEqual(self.cli()[0], 1)

    def test_central_directory_checked_before_zipfile_allocation(self):
        raw = bytearray(self.archive.read_bytes())
        offset = raw.rfind(b"PK\x05\x06")
        struct.pack_into("<H", raw, offset + 8, 2000)
        struct.pack_into("<H", raw, offset + 10, 2000)
        self.archive.write_bytes(raw)
        with patch.object(zipfile, "ZipFile", side_effect=AssertionError("Niet parsen")):
            self.assertEqual(self.cli()[0], 1)

    def test_wrong_actual_count_is_rejected_before_loading_zip(self):
        raw = bytearray(self.archive.read_bytes())
        offset = raw.rfind(b"PK\x05\x06")
        struct.pack_into("<H", raw, offset + 8, 1)
        struct.pack_into("<H", raw, offset + 10, 1)
        self.archive.write_bytes(raw)
        with patch.object(zipfile, "ZipFile", side_effect=AssertionError("Niet parsen")):
            self.assertEqual(self.cli()[0], 1)

    def test_zip64_locator_cannot_override_preflight_limits(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, content in self.files.items():
                archive.writestr(name, content)
            info = zipfile.ZipInfo(backup.MANIFEST_NAME)
            info.comment = b"PK\x06\x07" + b"\x00" * 16
            archive.writestr(info, json.dumps(self.manifest()))
        with patch.object(zipfile, "ZipFile", side_effect=AssertionError("Geen ZIP64 laden")):
            self.assertEqual(self.cli()[0], 1)

    def test_encrypted_unsupported_compression_and_truncated_zip(self):
        self.write_zip(compression=zipfile.ZIP_BZIP2)
        self.assertEqual(self.cli()[0], 1)
        self.write_zip()
        raw = bytearray(self.archive.read_bytes())
        offset = raw.find(b"PK\x01\x02")
        struct.pack_into("<H", raw, offset + 8, 1)
        self.archive.write_bytes(raw)
        self.assertEqual(self.cli()[0], 1)
        self.archive.write_bytes(b"PK\x03\x04")
        self.assertEqual(self.cli()[0], 1)

    def test_archive_change_after_preview_prevents_any_writes(self):
        plan = restore.inspect(self.archive, self.output)
        self.write_zip(files={"README.md": b"andere inhoud"})
        with self.assertRaises(ValueError):
            restore.restore(plan)
        self.assertFalse(self.output.exists())

    def test_new_destination_after_confirmation_is_preserved(self):
        def confirm(*args):
            self.output.mkdir()
            (self.output / "bestaand.txt").write_bytes(b"bewaren")
            return "HERSTEL hersteld"
        with patch.object(sys.stdin, "isatty", return_value=True), patch("builtins.input", side_effect=confirm):
            self.assertEqual(self.cli(create=True)[0], 1)
        self.assertEqual((self.output / "bestaand.txt").read_bytes(), b"bewaren")
        self.assertFalse((self.output / restore.INCOMPLETE).exists())

    def test_network_paths_and_missing_parents_rejected(self):
        for target in (Path(r"\\server\share\new"), Path(r"\\?\C:\folder"), self.base / "absent" / "new"):
            with self.subTest(target=target), self.assertRaises((OSError, ValueError)):
                restore.inspect(self.archive, target)

    def test_symlink_or_junction_in_archive_and_parent_rejected(self):
        real = Path.lstat
        for target in (self.archive, self.base):
            def fake(path):
                if path == target:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                return real(path)
            with self.subTest(target=target), patch.object(Path, "lstat", fake):
                self.assertEqual(self.cli()[0], 1)
                self.assertFalse(self.output.exists())

    def test_failure_or_interrupt_after_mkdir_leaves_incomplete_marker(self):
        real = restore.read_member
        for number, error in enumerate((OSError("fictief"), KeyboardInterrupt())):
            target = self.base / ("partial" + str(number))
            plan = restore.inspect(self.archive, target)
            def fail(*args, **kwargs):
                if kwargs.get("target") is not None:
                    raise error
                return real(*args, **kwargs)
            with patch.object(restore, "read_member", side_effect=fail), self.assertRaises(type(error)):
                restore.restore(plan)
            self.assertTrue((target / restore.INCOMPLETE).exists())
            self.assertFalse((target / "tests/test_app.py").exists())

    def test_backup_roundtrip_supports_all_four_project_types(self):
        root = self.base / "Projects"
        root.mkdir()
        project = root / "voorbeeld"
        project.mkdir()
        (project / "README.md").write_bytes(b"voorbeeld")
        for kind in ("python", "web", "ai", "automation"):
            with self.subTest(kind=kind):
                metadata = {"schema_version": 1, "project": {"name": "Voorbeeld"},
                            "generator": {"version": "1.0.0"}, "template": {"id": kind, "version": "1.0.0"}}
                (project / studio.METADATA_FILE).write_text(json.dumps(metadata), encoding="utf-8")
                archive = backup.create_archive(backup.make_plan(root, "voorbeeld", self.base / "Backups"))
                target = self.base / ("herstel-" + kind)
                restore.restore(restore.inspect(archive, target))
                self.assertEqual(json.loads((target / studio.METADATA_FILE).read_bytes()), metadata)
                self.assertEqual((target / "README.md").read_bytes(), b"voorbeeld")

    def test_manifest_only_archive_is_valid_but_preview_warns(self):
        self.write_zip(files={})
        code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertIn("geen projectbestanden", out)
        self.assertFalse(self.output.exists())

    def test_nul_in_zip_member_name_is_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes().replace(b"src/app.py", b"src/\x00pp.py"))
        self.assertEqual(self.cli()[0], 1)
        self.assertFalse(self.output.exists())

    def test_normal_cli_preview_creates_no_caches_in_isolated_studio(self):
        app = self.base / "Studio"
        app.mkdir()
        for name in ("studio.py", "backup.py", "restore.py", "process_runner.py", "studio_logging.py"):
            (app / name).write_bytes((Path(studio.__file__).parent / name).read_bytes())
        before = {p.name: p.read_bytes() for p in app.iterdir()}
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        result = subprocess.run([sys.executable, str(app / "studio.py"), "restore", str(self.archive),
                                 "--output", str(self.output)], cwd=self.base, env=env,
                                capture_output=True, shell=False, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in app.iterdir()})


if __name__ == "__main__":
    unittest.main()
