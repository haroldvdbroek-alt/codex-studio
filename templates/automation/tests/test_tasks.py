"""Bestandscontroles met uitsluitend tijdelijke, fictieve gegevens."""

from contextlib import redirect_stderr
from io import StringIO
import logging
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from project_package.__main__ import main
from project_package.tasks import process_files, reject_links


class TaskTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / "input"
        self.source.mkdir()
        self.original = self.source / "voorbeeld.txt"
        self.original.write_bytes("Hallo café\n".encode("utf-8"))
        self.target = self.root / "output"

    def test_default_dry_run_does_not_create_parents_or_modify_source(self):
        target = self.root / "nieuw" / "output"
        with patch.object(Path, "read_text", side_effect=AssertionError("Geen inhoud lezen in dry-run")):
            self.assertEqual(process_files(self.source, target), 1)
        self.assertFalse(target.parent.exists())
        self.assertEqual(self.original.read_bytes(), "Hallo café\n".encode("utf-8"))

    def test_apply_transforms_and_preserves_source(self):
        self.assertEqual(process_files(self.source, self.target, apply=True), 1)
        self.assertEqual((self.target / "voorbeeld.txt").read_bytes(), "HALLO CAFÉ\n".encode("utf-8"))
        self.assertEqual(self.original.read_bytes(), "Hallo café\n".encode("utf-8"))

    def test_existing_targets_are_never_overwritten(self):
        for kind in ("empty", "full", "file"):
            with self.subTest(kind=kind):
                target = self.root / kind
                if kind == "file":
                    target.write_bytes(b"behouden")
                else:
                    target.mkdir()
                    if kind == "full":
                        (target / "voorbeeld.txt").write_bytes(b"behouden")
                for apply in (False, True):
                    with self.assertRaises(FileExistsError):
                        process_files(self.source, target, apply=apply)
                if kind != "empty":
                    marker = target if kind == "file" else target / "voorbeeld.txt"
                    self.assertEqual(marker.read_bytes(), b"behouden")

    def test_missing_or_file_source_is_rejected(self):
        for source in (self.root / "ontbreekt", self.original):
            with self.subTest(source=source), self.assertRaises(ValueError):
                process_files(source, self.target, apply=True)
        self.assertFalse(self.target.exists())

    def test_overlapping_paths_are_rejected(self):
        for target in (self.source, self.source / "nested", self.root):
            with self.subTest(target=target), self.assertRaises(ValueError):
                process_files(self.source, target, apply=True)

    def test_only_direct_text_files_are_processed(self):
        (self.source / "overslaan.bin").write_bytes(b"voorbeeld")
        nested = self.source / "submap"
        nested.mkdir()
        (nested / "overslaan.txt").write_bytes(b"voorbeeld")
        self.assertEqual(process_files(self.source, self.target, apply=True), 1)
        self.assertEqual([p.name for p in self.target.iterdir()], ["voorbeeld.txt"])

    def test_empty_source_creates_nothing(self):
        empty = self.root / "leeg"
        empty.mkdir()
        self.assertEqual(process_files(empty, self.target, apply=True), 0)
        self.assertFalse(self.target.exists())

    def test_invalid_utf8_is_detected_before_writing(self):
        (self.source / "z-invalid.txt").write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            process_files(self.source, self.target, apply=True)
        self.assertFalse(self.target.exists())

    def test_logging_has_no_contents_or_personal_paths(self):
        output = StringIO()
        logger = logging.Logger("offline-test", level=logging.INFO)
        logger.addHandler(logging.StreamHandler(output))
        process_files(self.source, self.target, logger=logger)
        self.assertIn("DRY-RUN", output.getvalue())
        self.assertNotIn("Hallo", output.getvalue())
        self.assertNotIn(str(self.root), output.getvalue())

    def test_symlink_and_junction_attributes_are_rejected(self):
        for mode, attributes in ((stat.S_IFLNK, 0), (stat.S_IFDIR, stat.FILE_ATTRIBUTE_REPARSE_POINT)):
            info = SimpleNamespace(st_mode=mode, st_file_attributes=attributes)
            with patch.object(Path, "lstat", return_value=info), self.assertRaises(ValueError):
                reject_links(self.target)

    def test_real_source_symlink_is_rejected(self):
        link = self.source / "link.txt"
        try:
            link.symlink_to(self.original)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks zijn hier niet beschikbaar.")
        with self.assertRaises(ValueError):
            process_files(self.source, self.target, apply=True)
        self.assertFalse(self.target.exists())

    def test_cli_defaults_to_dry_run_and_apply_is_explicit(self):
        with redirect_stderr(StringIO()):
            self.assertEqual(main([str(self.source), str(self.target)]), 0)
            self.assertFalse(self.target.exists())
            self.assertEqual(main([str(self.source), str(self.target), "--apply"]), 0)
        self.assertTrue((self.target / "voorbeeld.txt").is_file())

    def test_cli_reports_error_without_contents(self):
        with redirect_stderr(StringIO()) as output:
            self.assertEqual(main([str(self.root / "ontbreekt"), str(self.target)]), 1)
        self.assertIn("ERROR", output.getvalue())


if __name__ == "__main__":
    unittest.main()
