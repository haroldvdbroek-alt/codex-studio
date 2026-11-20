"""Rapporten delen één model en overschrijven nooit bestaande gegevens."""

from contextlib import redirect_stdout, redirect_stderr
from io import BytesIO, StringIO, TextIOWrapper
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
import quality
import reporting
import studio


class QualityReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.items = [studio.CheckResult("PASS", "Python", "Syntaxis gecontroleerd"),
                      studio.CheckResult("WARN", "Template web", "Nog gepland")]
        for item in (patch.object(quality, "static_checks", side_effect=lambda **kwargs: list(self.items)),
                     patch.object(quality, "STUDIO_ROOT", self.root)):
            item.start()
            self.addCleanup(item.stop)

    def cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(["quality", *args])
        return code, out.getvalue(), err.getvalue()

    def test_json_is_one_document_with_consistent_counts_and_exit_code(self):
        code, out, err = self.cli("--format", "json")
        data = json.loads(out)
        self.assertEqual(code, data["exit_code"])
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["command"], "quality")
        self.assertEqual(data["summary"], {"PASS": 1, "WARN": 1, "FAIL": 0, "SKIP": 1})
        self.assertEqual(len(data["results"]), sum(data["summary"].values()))
        self.assertFalse(data["tests_requested"])
        self.assertEqual(data["completion"], "complete")
        self.assertEqual(err, "")

    def test_all_formats_share_result_values_counts_and_exit(self):
        for output_format in reporting.FORMATS:
            with self.subTest(output_format=output_format):
                code, out, _ = self.cli("--format", output_format)
                self.assertEqual(code, 0)
                self.assertIn("Python", out)
                self.assertIn("Syntaxis gecontroleerd", out)
                self.assertIn("Template web", out)
                if output_format != "json":
                    self.assertIn("1 PASS, 1 WARN, 0 FAIL, 1 SKIP", out)

    def test_control_failures_stay_exit_one_in_every_format(self):
        self.items.append(studio.CheckResult("FAIL", "Configuratie", "Ontbreekt"))
        for output_format in reporting.FORMATS:
            with self.subTest(output_format=output_format):
                code, out, _ = self.cli("--format", output_format)
                self.assertEqual(code, 1)
                self.assertIn("Configuratie", out)

    def test_unicode_cp1252_json_is_valid_and_preserves_values(self):
        label = "Project \U0001f600 \u6d4b\u8bd5"
        self.items = [studio.CheckResult("PASS", label, "Geldig")]
        output = BytesIO()
        wrapper = TextIOWrapper(output, encoding="cp1252", newline="")
        with redirect_stdout(wrapper), redirect_stderr(StringIO()):
            code = studio.main(["quality", "--format", "json"])
        wrapper.flush()
        data = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(data["results"][0]["label"], label)

    def test_markdown_escapes_html_links_tables_and_control_sequences(self):
        hostile = '<img src=x onerror=alert(1)> | [klik](javascript:alert(1)) `code`\n# kop\x1b[31m'
        self.items = [studio.CheckResult("WARN", hostile, "**vet** & tekst")]
        _, out, _ = self.cli("--format", "markdown")
        self.assertNotIn("<img", out)
        self.assertNotIn("[klik]", out)
        self.assertNotIn("`code`", out)
        self.assertNotIn("**vet**", out)
        self.assertNotIn("\x1b", out)
        self.assertIn("&#124;", out)
        self.assertEqual(len([line for line in out.splitlines() if line.startswith("| WARN |")]), 1)

    def test_successful_files_are_utf8_and_match_stdout(self):
        for output_format, suffix in reporting.FORMATS.items():
            target = self.root / ("rapport" + suffix)
            with self.subTest(output_format=output_format):
                code, out, err = self.cli("--format", output_format, "--output", str(target))
                self.assertEqual(code, 0, err)
                self.assertEqual(target.read_text(encoding="utf-8"), out)
                self.assertIn("Rapport opgeslagen", err)
                self.assertFalse(list(self.root.glob("*.incomplete")))

    def test_existing_file_or_directory_never_overwritten_or_tests_started(self):
        target = self.root / "bestaand.json"
        target.write_bytes(b"BEWAREN")
        with patch.object(quality, "collect", side_effect=AssertionError("Niet controleren")), \
             patch("builtins.input", side_effect=AssertionError("Niet starten")):
            code, out, _ = self.cli("--format", "json", "--output", str(target), "--run-tests")
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["exit_code"], 3)
        self.assertEqual(target.read_bytes(), b"BEWAREN")
        target = self.root / "map.json"
        target.mkdir()
        self.assertEqual(self.cli("--format", "json", "--output", str(target))[0], 3)

    def test_bad_suffix_missing_parent_and_protected_directories_refused(self):
        for target in (self.root / "rapport.md", self.root / "absent/rapport.json", self.root / "con.json"):
            with self.subTest(target=target):
                code, out, _ = self.cli("--format", "json", "--output", str(target))
                self.assertEqual(code, 3)
                self.assertEqual(json.loads(out)["completion"], "error")
                self.assertFalse(target.exists())
        admin = self.root / ".git"
        admin.mkdir()
        self.assertEqual(self.cli("--format", "json", "--output", str(admin / "rapport.json"))[0], 3)
        self.assertEqual(list(admin.iterdir()), [])

    def test_unc_device_and_stream_paths_refused(self):
        for text in (r"\\server\share\rapport.json", r"\\?\C:\rapport.json", str(self.root / "rapport.json:stream")):
            with self.subTest(text=text):
                self.assertEqual(self.cli("--format", "json", "--output", text)[0], 3)

    def test_reparse_report_parent_rejected_without_creating_files(self):
        real = Path.lstat
        def fake(path):
            if path == self.root:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return real(path)
        with patch.object(Path, "lstat", fake):
            self.assertEqual(self.cli("--format", "json", "--output", str(self.root / "rapport.json"))[0], 3)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_race_on_publish_keeps_existing_destination_unchanged(self):
        target = self.root / "rapport.json"
        operation = "rename" if os.name == "nt" else "link"
        real = getattr(os, operation)
        def race(source, destination, **kwargs):
            Path(destination).write_bytes(b"BLIJVEN BEWAREN")
            return real(source, destination, **kwargs)
        with patch.object(os, operation, side_effect=race):
            code, out, _ = self.cli("--format", "json", "--output", str(target))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["summary"]["FAIL"], 1)
        self.assertEqual(target.read_bytes(), b"BLIJVEN BEWAREN")
        self.assertTrue(list(self.root.glob("*.incomplete")))

    def test_write_failure_never_publishes_partial_final_report(self):
        target = self.root / "rapport.json"
        with patch.object(os, "fsync", side_effect=OSError("schijf vol")):
            code, out, _ = self.cli("--format", "json", "--output", str(target))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["exit_code"], 3)
        self.assertFalse(target.exists())

    def test_json_test_mode_keeps_prompts_on_stderr_only(self):
        completed = subprocess.CompletedProcess([], 0, b"", b"Ran 2 tests in 0.1s\nOK\n")
        with patch("builtins.input", return_value="ja"), patch.object(studio, "run_bounded", return_value=completed):
            code, out, err = self.cli("--format", "json", "--run-tests")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertTrue(data["tests_requested"])
        self.assertEqual(data["results"][-1]["status"], "PASS")
        self.assertNotIn("WAARSCHUWING", out)
        self.assertIn("WAARSCHUWING", err)
        self.assertIn("Doorgaan?", err)

    def test_test_confirmation_decline_is_visible_as_skip_and_exit_zero(self):
        with patch("builtins.input", return_value="nee"), patch.object(studio, "run_bounded", side_effect=AssertionError("Niet starten")):
            code, out, _ = self.cli("--format", "json", "--run-tests")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["tests_requested"])
        self.assertEqual(data["results"][-1]["status"], "SKIP")

    def test_interrupt_has_structured_exit_130_and_saves_no_report(self):
        target = self.root / "rapport.json"
        with patch.object(quality, "static_checks", side_effect=KeyboardInterrupt):
            code, out, _ = self.cli("--format", "json", "--output", str(target))
        self.assertEqual(code, 130)
        data = json.loads(out)
        self.assertEqual(data["exit_code"], 130)
        self.assertEqual(data["completion"], "cancelled")
        self.assertFalse(target.exists())

    def test_fatal_quality_error_is_structured_exit_one(self):
        with patch.object(quality, "static_checks", side_effect=OSError("FICTIEF_GEHEIM")):
            code, out, err = self.cli("--format", "json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["completion"], "error")
        self.assertNotIn("FICTIEF_GEHEIM", out + err)

    def test_failed_quality_report_can_be_saved_with_exit_one(self):
        self.items.append(studio.CheckResult("FAIL", "Configuratie", "Ontbreekt"))
        target = self.root / "mislukt.json"
        code, out, err = self.cli("--format", "json", "--output", str(target))
        self.assertEqual(code, 1, err)
        data = json.loads(target.read_bytes())
        self.assertEqual(data, json.loads(out))
        self.assertEqual(data["summary"]["FAIL"], 1)
        self.assertEqual(data["exit_code"], 1)

    def test_oversized_report_returns_small_structured_error(self):
        self.items = [studio.CheckResult("PASS", "x" * 1000, "a" * 1000)]
        target = self.root / "rapport.json"
        with patch.object(reporting, "MAX_REPORT_BYTES", 100):
            code, out, _ = self.cli("--format", "json", "--output", str(target))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["exit_code"], 3)
        self.assertNotIn("x" * 1000, out)
        self.assertFalse(target.exists())

    def test_invalid_format_is_cli_exit_two(self):
        with self.assertRaises(SystemExit) as error, redirect_stderr(StringIO()):
            studio.main(["quality", "--format", "html"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
