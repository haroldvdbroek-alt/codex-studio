"""Projectherkenning zonder bestaande projecten of persoonlijke gegevens te lezen."""

from contextlib import redirect_stderr, redirect_stdout
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import studio


class StudioTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def project(self, folder="voorbeeld", name="Voorbeeld", kind="python"):
        directory = self.root / folder
        directory.mkdir()
        data = {"schema_version": 1, "project": {"name": name},
                "generator": {"version": "1.2.0"}, "template": {"id": kind, "version": "2.0.1"}}
        (directory / studio.METADATA_FILE).write_text(json.dumps(data), encoding="utf-8")
        return directory, data

    def run_cli(self, args):
        output, error = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = studio.main(args)
        return code, output.getvalue(), error.getvalue()

    def test_lists_all_four_types_and_versions_sorted_by_name(self):
        for name, kind in (("Zulu", "python"), ("Alpha", "web"), ("Beta", "ai"), ("Gamma", "automation")):
            self.project(name.lower(), name, kind)
        projects, warnings = studio.list_projects(self.root)
        self.assertEqual([p.name for p in projects], ["Alpha", "Beta", "Gamma", "Zulu"])
        self.assertFalse(warnings)
        self.assertTrue(all(p.studio_version == "1.2.0" and p.template_version == "2.0.1" for p in projects))
        code, output, _ = self.run_cli(["list", "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn(str(self.root / "alpha"), output)
        self.assertIn("LOCATIE", output)

    def test_default_uses_home_projects_without_creating_root(self):
        with patch.object(studio.Path, "home", return_value=self.root):
            self.assertEqual(self.run_cli(["list"])[0], 1)
            self.assertFalse((self.root / "Projects").exists())
            (self.root / "Projects").mkdir()
            directory, _ = self.project()
            directory.rename(self.root / "Projects/voorbeeld")
            self.assertIn("Voorbeeld", self.run_cli(["list"])[1])

    def test_empty_root_is_success_and_not_recursive(self):
        folder = self.root / "container"
        folder.mkdir()
        child = folder / "nested"
        child.mkdir()
        (child / studio.METADATA_FILE).write_text("{}", encoding="utf-8")
        code, output, error = self.run_cli(["list", "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("Geen projecten", output)
        self.assertEqual(error, "")

    def test_explicit_unknown_versions_are_displayed_honestly(self):
        directory, data = self.project()
        data["generator"]["version"] = None
        data["template"]["version"] = None
        (directory / studio.METADATA_FILE).write_text(json.dumps(data), encoding="utf-8")
        code, output, error = self.run_cli(["list", "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(output.count("onbekend"), 2)
        self.assertEqual(error, "")
        self.assertIsNone(studio.list_projects(self.root)[0][0].studio_version)

    def test_missing_or_empty_versions_still_fail_validation(self):
        directory, data = self.project()
        for section in ({}, {"version": ""}, {"version": False}, {"version": "onbekend"}):
            data["generator"] = section
            (directory / studio.METADATA_FILE).write_text(json.dumps(data), encoding="utf-8")
            projects, warnings = studio.list_projects(self.root)
            self.assertFalse(projects)
            self.assertEqual(len(warnings), 1)

    def test_reads_only_needed_metadata_and_changes_no_files(self):
        directory, _ = self.project()
        (directory / ".env").write_bytes(b"fictieve-niet-lezen-inhoud")
        (directory / "source.py").write_bytes(b"raise RuntimeError('niet uitvoeren')")
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()}
        real_open = studio.os.open
        opened = []
        def check_open(path, flags, *args, **kwargs):
            self.assertEqual(Path(path).name, studio.METADATA_FILE)
            opened.append(path)
            return real_open(path, flags, *args, **kwargs)
        with patch.object(studio.os, "open", side_effect=check_open):
            self.assertEqual(len(studio.list_projects(self.root)[0]), 1)
        self.assertEqual(len(opened), 1)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()})

    def test_legacy_filename_is_not_read_or_migrated(self):
        directory = self.root / "oud"
        directory.mkdir()
        legacy = directory / ".codex-project.json"
        legacy.write_bytes(b"niet lezen")
        self.assertEqual(studio.list_projects(self.root), ([], []))
        self.assertEqual(list(directory.iterdir()), [legacy])

    def test_invalid_metadata_does_not_hide_valid_projects_or_leak_contents(self):
        directory, _ = self.project("ongeldig")
        (directory / studio.METADATA_FILE).write_text("GEHEIME-FICTIEVE-INHOUD", encoding="utf-8")
        self.project("geldig", "Geldig")
        code, output, error = self.run_cli(["list", "--root", str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("Geldig", output)
        self.assertIn("Waarschuwing", error)
        self.assertNotIn("GEHEIME-FICTIEVE-INHOUD", output + error)

    def test_schema_required_fields_types_versions_and_control_chars(self):
        directory, data = self.project()
        invalid = [None, [], {**data, "schema_version": True}, {**data, "schema_version": 2},
                   {**data, "project": {}}, {**data, "project": {"name": "bad\x1b[31m"}},
                   {**data, "template": {"id": "unknown", "version": "1.0.0"}},
                   {**data, "generator": {"version": "latest"}}]
        for value in invalid:
            with self.subTest(value=value):
                (directory / studio.METADATA_FILE).write_text(json.dumps(value), encoding="utf-8")
                projects, warnings = studio.list_projects(self.root)
                self.assertFalse(projects)
                self.assertEqual(len(warnings), 1)

    def test_duplicate_keys_invalid_utf8_and_large_metadata_are_rejected(self):
        directory, _ = self.project()
        for raw in (b'{"schema_version":1,"schema_version":1}', b"\xff",
                    b" " * (studio.MAX_METADATA_BYTES + 1)):
            (directory / studio.METADATA_FILE).write_bytes(raw)
            self.assertFalse(studio.list_projects(self.root)[0])

    def test_utf8_bom_and_no_bom_are_supported_without_modifying_metadata(self):
        directory, data = self.project()
        for encoding in ("utf-8", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                raw = json.dumps(data).encode(encoding)
                path = directory / studio.METADATA_FILE
                path.write_bytes(raw)
                before = path.stat().st_mtime_ns
                projects, warnings = studio.list_projects(self.root)
                self.assertEqual(len(projects), 1)
                self.assertEqual(projects[0].studio_version, "1.2.0")
                self.assertEqual(warnings, [])
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(path.stat().st_mtime_ns, before)

    def test_bom_does_not_bypass_json_or_schema_validation(self):
        directory, _ = self.project()
        for content in ("not json", '{"schema_version":2}',
                        '{"schema_version":1,"schema_version":1}'):
            with self.subTest(content=content):
                (directory / studio.METADATA_FILE).write_bytes(content.encode("utf-8-sig"))
                projects, warnings = studio.list_projects(self.root)
                self.assertFalse(projects)
                self.assertEqual(len(warnings), 1)

    def test_unicode_names_and_paths_do_not_crash_cp1252_output(self):
        name = "\u6d4b\u8bd5"
        directory, _ = self.project(folder=name, name=name)
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()}
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252:strict"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "studio.py"), "list",
                                 "--root", str(self.root)], env=environment,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"\\u6d4b\\u8bd5", result.stdout)
        self.assertIn(b"python", result.stdout)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()})

    def test_utf8_output_preserves_unicode_names(self):
        name = "\u6d4b\u8bd5"
        self.project(name=name)
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8:strict"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "studio.py"), "list",
                                 "--root", str(self.root)], env=environment,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(name.encode("utf-8"), result.stdout)

    def test_warning_omits_private_names_for_restricted_stream(self):
        from io import BytesIO, TextIOWrapper
        name = "\u6d4b\u8bd5"
        directory, _ = self.project(folder=name)
        (directory / studio.METADATA_FILE).write_bytes(b"invalid")
        raw = BytesIO()
        error = TextIOWrapper(raw, encoding="cp1252", errors="strict")
        with redirect_stdout(StringIO()), redirect_stderr(error):
            self.assertEqual(studio.main(["list", "--root", str(self.root)]), 1)
        error.flush()
        self.assertNotIn(b"\\u6d4b\\u8bd5", raw.getvalue())
        self.assertNotIn(name.encode("utf-8"), raw.getvalue())
        self.assertIn(b"Waarschuwing", raw.getvalue())
        error.detach()

    def test_unreadable_metadata_is_reported(self):
        self.project()
        with patch.object(studio.os, "open", side_effect=PermissionError):
            projects, warnings = studio.list_projects(self.root)
        self.assertFalse(projects)
        self.assertEqual(len(warnings), 1)

    def test_oversized_metadata_is_not_opened(self):
        directory, _ = self.project()
        (directory / studio.METADATA_FILE).write_bytes(b" " * (studio.MAX_METADATA_BYTES + 1))
        with patch.object(studio.os, "open", side_effect=AssertionError("Niet openen")):
            projects, warnings = studio.list_projects(self.root)
        self.assertFalse(projects)
        self.assertEqual(len(warnings), 1)

    def test_replaced_metadata_is_rejected_before_reading(self):
        self.project()
        fstat = studio.os.fstat
        def changed_identity(descriptor):
            info = fstat(descriptor)
            return SimpleNamespace(st_mode=info.st_mode, st_dev=info.st_dev, st_ino=info.st_ino + 1)
        with patch.object(studio.os, "fstat", side_effect=changed_identity):
            projects, warnings = studio.list_projects(self.root)
        self.assertFalse(projects)
        self.assertIn("UnsafePathError", warnings[0])

    def test_project_junction_is_skipped_without_opening_metadata(self):
        directory, _ = self.project()
        lstat = Path.lstat
        def simulated_junction(path, *args, **kwargs):
            if path == directory:
                return SimpleNamespace(st_mode=stat.S_IFDIR,
                                       st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return lstat(path, *args, **kwargs)
        with patch.object(Path, "lstat", new=simulated_junction), patch.object(
            studio.os, "open", side_effect=AssertionError("Koppeling niet openen")
        ):
            projects, warnings = studio.list_projects(self.root)
        self.assertFalse(projects)
        self.assertEqual(len(warnings), 1)

    def test_nonregular_metadata_and_file_root_are_rejected(self):
        directory = self.root / "map"
        directory.mkdir()
        (directory / studio.METADATA_FILE).mkdir()
        self.assertEqual(len(studio.list_projects(self.root)[1]), 1)
        file = self.root / "bestand"
        file.write_bytes(b"fictief")
        self.assertEqual(self.run_cli(["list", "--root", str(file)])[0], 1)

    def test_symlink_and_windows_junction_attributes_are_rejected(self):
        for mode, attributes in ((stat.S_IFLNK, 0), (stat.S_IFDIR, stat.FILE_ATTRIBUTE_REPARSE_POINT)):
            with patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=mode, st_file_attributes=attributes)):
                with self.assertRaises(studio.UnsafePathError):
                    studio.reject_links(self.root)

    def test_linked_root_project_and_metadata_are_not_followed(self):
        directory, _ = self.project()
        linked_root = self.root / "root-link"
        try:
            linked_root.symlink_to(directory, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks zijn hier niet beschikbaar.")
        self.assertEqual(self.run_cli(["list", "--root", str(linked_root)])[0], 1)
        linked_project = self.root / "linked-project"
        linked_project.symlink_to(directory, target_is_directory=True)
        bad = self.root / "linked-metadata"
        bad.mkdir()
        (bad / studio.METADATA_FILE).symlink_to(directory / studio.METADATA_FILE)
        projects, warnings = studio.list_projects(self.root)
        self.assertEqual(len(projects), 1)
        self.assertEqual(len(warnings), 3)

    def test_terminal_control_chars_in_paths_are_escaped(self):
        self.assertNotIn("\x1b", studio.terminal_text("map\x1b[31m"))
        self.assertNotIn("\n", studio.terminal_text("map\nnaam"))

    def test_real_cli_runs_from_another_directory(self):
        self.project()
        result = subprocess.run([sys.executable, "-B", str(ROOT / "studio.py"), "list",
                                 "--root", str(self.root)], cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Voorbeeld", result.stdout)


if __name__ == "__main__":
    unittest.main()
