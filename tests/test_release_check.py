"""Lokale releasevoorcontrole geeft nooit publicatie- of externe goedkeuring."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import html
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import quality
import release_check
import reporting
import studio

READ_COMMIT = release_check.read_commit


class ReleaseCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.changelog = self.root / "CHANGELOG.md"
        self.changelog.write_text("# Changelog\n\n## [1.2.3]\n\n- Fictieve testwijziging.\n", encoding="utf-8")
        self.items = [quality.result("PASS", "Bestanden", "Aanwezig"), quality.result("PASS", "Git", "Schoon")]
        self.commit = "a" * 40
        for item in (patch.object(quality, "STUDIO_ROOT", self.root),
                     patch.object(quality, "static_checks", side_effect=lambda **kwargs: list(self.items)),
                     patch.object(release_check, "read_commit", return_value=self.commit)):
            item.start()
            self.addCleanup(item.stop)

    def cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(["release-check", *args])
        return code, out.getvalue(), err.getvalue()

    def test_default_readonly_no_code_network_or_file_changes(self):
        before = self.changelog.read_bytes(), self.changelog.stat().st_mtime_ns
        with patch.object(subprocess, "Popen", side_effect=AssertionError("Geen uitvoer")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")), \
             patch.object(quality, "run_tests", side_effect=AssertionError("Geen tests")):
            code, out, err = self.cli("--format", "json")
        self.assertEqual(code, 4, err)
        data = json.loads(out)
        self.assertEqual(data["command"], "release-check")
        self.assertEqual(data["release"]["state"], "LOCAL_INCOMPLETE")
        self.assertIsNone(data["release"]["version"])
        self.assertFalse(data["tests_requested"])
        self.assertEqual(before, (self.changelog.read_bytes(), self.changelog.stat().st_mtime_ns))
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_old_reports_are_not_used_as_current_test_evidence(self):
        (self.root / "quality.json").write_text('{"tests_requested":true,"exit_code":0}', encoding="utf-8")
        code, out, _ = self.cli("--version", "1.2.3", "--format", "json")
        self.assertEqual(code, 4)
        data = json.loads(out)
        self.assertFalse(data["release"]["local_ready"])
        self.assertEqual(next(item for item in data["results"] if item["label"] == "Tests")["status"], "SKIP")

    def test_all_local_checks_pass_still_requires_manual_verification(self):
        with patch.object(quality, "run_tests", return_value=quality.result("PASS", "Tests", "Tests geslaagd")):
            code, out, _ = self.cli("--version", "1.2.3", "--run-tests", "--format", "json")
        data = json.loads(out)
        self.assertEqual(code, 4)
        self.assertEqual(data["exit_code"], code)
        self.assertEqual(data["summary"]["FAIL"], 0)
        self.assertTrue(data["release"]["local_ready"])
        self.assertEqual(data["release"]["state"], "MANUAL_REQUIRED")
        self.assertEqual(data["release"]["commit"], self.commit)
        self.assertFalse(data["release"]["published"])
        manual = data["release"]["manual_checks"]
        self.assertGreaterEqual(len(manual), 6)
        self.assertTrue(all(item["status"] == "HANDMATIG_TE_VERIFIEREN" for item in manual))
        self.assertIn("actions", {item["id"] for item in manual})
        self.assertIn("publication", {item["id"] for item in manual})

    def test_invalid_version_not_guessed_or_echoed(self):
        for version in ("1.2", "01.2.3", "1.2.3-beta", "FICTIEF_GEHEIM"):
            with self.subTest(version=version):
                code, out, err = self.cli("--version", version, "--format", "json")
                self.assertEqual(code, 1)
                data = json.loads(out)
                self.assertEqual(data["release"]["state"], "BLOCKED")
                self.assertIsNone(data["release"]["version"])
                self.assertNotIn("FICTIEF_GEHEIM", out + err)

    def test_missing_or_placeholder_changelog_blocks_tests(self):
        for text in ("## [Unreleased]\n- Voorbeeld\n", "## [1.2.3]\n", "## [1.2.3]\nTODO\n",
                     "```markdown\n## [1.2.3]\n- Voorbeeld\n```\n"):
            with self.subTest(text=text), patch.object(quality, "run_tests", side_effect=AssertionError("Niet starten")):
                self.changelog.write_text(text, encoding="utf-8")
                self.assertEqual(self.cli("--version", "1.2.3", "--run-tests")[0], 1)
        self.changelog.unlink()
        self.assertEqual(self.cli("--version", "1.2.3")[0], 1)

    def test_changelog_requires_exact_version_not_prefix(self):
        self.changelog.write_text("## [1.2.30]\n- Voorbeeld\n", encoding="utf-8")
        self.assertEqual(self.cli("--version", "1.2.3")[0], 1)
        self.changelog.write_text("## [1.2.3] - 2026-11-20\n- Fictieve testnotities\n", encoding="utf-8")
        self.assertEqual(self.cli("--version", "1.2.3")[0], 4)

    def test_dirty_or_unavailable_git_blocks_release_and_commit_read(self):
        for status in ("WARN", "FAIL"):
            self.items[-1] = quality.result(status, "Git", "Niet aantoonbaar schoon")
            with self.subTest(status=status), patch.object(release_check, "read_commit", side_effect=AssertionError("Geen bypass")), \
                 patch.object(quality, "run_tests", side_effect=AssertionError("Niet starten")):
                self.assertEqual(self.cli("--version", "1.2.3", "--run-tests")[0], 1)

    def test_no_commit_or_git_timeout_safe_failure(self):
        for error in (ValueError("geen HEAD"), subprocess.TimeoutExpired("git", 1), OSError("niet leesbaar")):
            with self.subTest(error=error), patch.object(release_check, "read_commit", side_effect=error):
                self.assertEqual(self.cli("--version", "1.2.3")[0], 1)

    def test_test_failure_and_cancellation_do_not_release(self):
        for status, expected in (("FAIL", 1), ("SKIP", 4)):
            with self.subTest(status=status), patch.object(quality, "run_tests", return_value=quality.result(status, "Tests", "Geen goedkeuring")):
                code, out, _ = self.cli("--version", "1.2.3", "--run-tests", "--format", "json")
                self.assertEqual(code, expected)
                self.assertFalse(json.loads(out)["release"]["local_ready"])

    def test_changed_head_or_worktree_after_tests_blocks_release(self):
        with patch.object(quality, "run_tests", return_value=quality.result("PASS", "Tests", "Geslaagd")):
            with patch.object(release_check, "read_commit", side_effect=[self.commit, "b" * 40]):
                self.assertEqual(self.cli("--version", "1.2.3", "--run-tests")[0], 1)
            with patch.object(quality, "static_checks", side_effect=[list(self.items), [quality.result("WARN", "Git", "Gewijzigd")]]):
                self.assertEqual(self.cli("--version", "1.2.3", "--run-tests")[0], 1)

    def test_structured_interrupt_preserves_manual_unknowns(self):
        with patch.object(quality, "run_tests", side_effect=KeyboardInterrupt):
            code, out, _ = self.cli("--version", "1.2.3", "--run-tests", "--format", "json")
        data = json.loads(out)
        self.assertEqual(code, 130)
        self.assertEqual(data["completion"], "cancelled")
        self.assertFalse(data["release"]["published"])
        self.assertTrue(data["release"]["manual_checks"])

    def test_all_output_formats_keep_external_gates_open(self):
        for output_format in reporting.FORMATS:
            with self.subTest(output_format=output_format):
                code, out, _ = self.cli("--version", "1.2.3", "--format", output_format)
                self.assertEqual(code, 4)
                self.assertIn("HANDMATIG_TE_VERIFIEREN", html.unescape(out))
                self.assertIn("GitHub Actions", out)
                if output_format != "json":
                    self.assertIn("NIET GEPUBLICEERD", out)

    def test_safe_report_file_and_existing_target_refusal(self):
        target = self.root / "release.json"
        code, out, err = self.cli("--version", "1.2.3", "--format", "json", "--output", str(target))
        self.assertEqual(code, 4, err)
        self.assertEqual(json.loads(out), json.loads(target.read_bytes()))
        before = target.read_bytes()
        code, out, _ = self.cli("--format", "json", "--output", str(target))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["command"], "release-check")
        self.assertEqual(target.read_bytes(), before)

    def test_no_publish_or_external_approval_option(self):
        for option in ("--publish", "--approve-external", "--push"):
            with self.subTest(option=option), self.assertRaises(SystemExit) as error, redirect_stderr(StringIO()):
                studio.main(["release-check", option])
            self.assertEqual(error.exception.code, 2)

    def test_commit_read_has_only_fixed_readonly_arguments(self):
        completed = subprocess.CompletedProcess([], 0, (self.commit + "\n").encode(), b"")
        with patch.object(studio, "trusted_executable", return_value=str(self.root / "git.exe")), \
             patch.object(studio, "run_bounded", return_value=completed) as run:
            self.assertEqual(READ_COMMIT(self.root), self.commit)
        command = run.call_args.args[0]
        self.assertEqual(command[-3:], ["rev-parse", "--verify", "HEAD"])
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["timeout"], studio.GIT_TIMEOUT)
        self.assertEqual(run.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")


if __name__ == "__main__":
    unittest.main()
