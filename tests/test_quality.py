"""Quality voert standaard niets uit en bewaart geen rapporten/caches."""

from contextlib import redirect_stdout, redirect_stderr
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
import quality
import studio


class QualityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for name in quality.REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("pass\n" if path.suffix == ".py" else "# Voorbeeld\n", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests/test_sample.py").write_text("raise RuntimeError('NIET UITVOEREN')\n", encoding="utf-8")
        self.manifest = self.root / "templates/manifest.json"
        self.data = {"schema_version": 1, "templates": {
            kind: {"version": "1.0.0", "label": kind, "directory": kind + "-app", "files": ["README.md"]}
            for kind in studio.PROJECT_TYPES}}
        self.save_manifest()
        (self.root / "templates/python-app").mkdir()
        (self.root / "templates/python-app/README.md").write_text("# Voorbeeld\n", encoding="utf-8")
        for item in (patch.object(quality, "STUDIO_ROOT", self.root), patch.object(studio, "MANIFEST_PATH", self.manifest)):
            item.start()
            self.addCleanup(item.stop)

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")

    def cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(["quality", *args])
        return code, out.getvalue(), err.getvalue()

    def test_default_is_read_only_without_execution_or_network(self):
        (self.root / ".env").write_bytes(b"FICTIEF_GEHEIM=niet-lezen")
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        real = os.open
        def guarded(path, flags, *args, **kwargs):
            self.assertNotEqual(Path(path).name, ".env")
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
            return real(path, flags, *args, **kwargs)
        with patch.object(studio, "run_bounded", side_effect=AssertionError("Geen eigen Git")), \
             patch("builtins.input", side_effect=AssertionError("Geen toestemming nodig")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")), \
             patch.object(os, "open", side_effect=guarded):
            code, out, err = self.cli()
        self.assertEqual(code, 0, err)
        self.assertIn("SKIP Tests", out)
        self.assertIn("WARN Template web", out)
        self.assertNotIn("FICTIEF_GEHEIM", out + err)
        after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_missing_required_file_blocks_tests_before_prompt(self):
        (self.root / "README.md").unlink()
        with patch("builtins.input", side_effect=AssertionError("Niet vragen")), \
             patch.object(studio, "run_bounded", side_effect=AssertionError("Niet uitvoeren")):
            code, out, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("FAIL README.md", out)
        self.assertIn("SKIP Tests", out)

    def test_syntax_error_reports_line_not_source_contents(self):
        (self.root / "ongeldig.py").write_text("FICTIEF_GEHEIM = [\n", encoding="utf-8")
        code, out, err = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("FAIL Syntaxis ongeldig.py", out)
        self.assertIn("regel 1", out)
        self.assertNotIn("FICTIEF_GEHEIM", out + err)

    def test_invalid_manifest_and_unsafe_paths_fail(self):
        for version in ("1.0", "1.0.0-beta", None):
            self.data["templates"]["web"]["version"] = version
            self.save_manifest()
            self.assertEqual(self.cli()[0], 1)
        self.data["templates"]["web"]["version"] = "1.0.0"
        self.data["templates"]["python"]["directory"] = "../outside"
        self.save_manifest()
        self.assertEqual(self.cli()[0], 1)
        self.manifest.write_text("[]", encoding="utf-8")
        self.assertEqual(self.cli()[0], 1)

    def test_existing_incomplete_planned_template_is_failure(self):
        (self.root / "templates/web-app").mkdir()
        code, out, _ = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("FAIL Template web", out)

    def test_missing_python_template_and_missing_manifest_entry_fail(self):
        self.data["templates"]["python"]["directory"] = "niet-aanwezig"
        self.save_manifest()
        self.assertEqual(self.cli()[0], 1)
        self.data["templates"].pop("python")
        self.save_manifest()
        self.assertEqual(self.cli()[0], 1)

    def test_broken_outside_links_and_unclosed_fences_fail(self):
        for text in ("[kapot](niet-aanwezig.md)", "[buiten](../../outside.md)", "```python\npass\n"):
            with self.subTest(text=text):
                (self.root / "docs/WORKFLOW.md").write_text(text, encoding="utf-8")
                self.assertEqual(self.cli()[0], 1)

    def test_relative_parent_link_inside_studio_and_external_link_are_valid(self):
        (self.root / "docs/WORKFLOW.md").write_text("[regels](../AGENTS.md) [online](https://example.invalid/)", encoding="utf-8")
        with patch.object(socket, "socket", side_effect=AssertionError("Niet ophalen")):
            self.assertEqual(self.cli()[0], 0)

    def test_tests_must_be_discoverable(self):
        (self.root / "tests/test_sample.py").rename(self.root / "tests/helper.py")
        self.assertEqual(self.cli()[0], 1)

    def test_test_module_and_template_reparse_points_are_rejected(self):
        real = Path.lstat
        for target in (self.root / "tests/test_sample.py", self.root / "templates/python-app"):
            def fake(path):
                if path == target:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                return real(path)
            with self.subTest(target=target), patch.object(Path, "lstat", fake):
                self.assertEqual(self.cli()[0], 1)

    def test_item_size_and_time_limits(self):
        with patch.object(quality, "MAX_ITEMS", 0):
            self.assertEqual(self.cli()[0], 1)
        with patch.object(quality, "STATIC_SECONDS", -1):
            self.assertEqual(self.cli()[0], 1)
        (self.root / "groot.py").write_bytes(b"#" * (studio.MAX_METADATA_BYTES + 1))
        self.assertEqual(self.cli()[0], 1)

    def test_readonly_git_status_is_reused(self):
        with patch.object(studio, "git_check", return_value=studio.CheckResult("PASS", "Git", "Schone werkmap")) as check:
            code, out, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("PASS Git", out)
        self.assertEqual(check.call_args.args[0].location, self.root)

    def test_optional_tests_warn_and_only_run_fixed_command(self):
        completed = subprocess.CompletedProcess([], 0, b"", b"Ran 7 tests in 0.01s\nOK (skipped=1)\n")
        with patch("builtins.input", return_value="ja"), patch.object(studio, "run_bounded", return_value=completed) as run:
            code, out, err = self.cli("--run-tests")
        self.assertEqual(code, 0, err)
        self.assertLess(err.index("WAARSCHUWING"), err.index("Typ ja"))
        self.assertEqual(run.call_args.args[0], [sys.executable, "-I", "-S", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"])
        self.assertEqual(run.call_args.kwargs["cwd"], self.root)
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["timeout"], studio.TEST_TIMEOUT)
        self.assertIn("7 gevonden, 1 overgeslagen", out)

    def test_cancel_eof_and_interrupt_at_prompt_start_no_tests(self):
        for answer in ("", "nee", "q", "anders", EOFError, KeyboardInterrupt):
            with self.subTest(answer=answer), patch.object(studio, "run_bounded", side_effect=AssertionError("Niet starten")):
                options = {"side_effect": answer} if isinstance(answer, type) else {"return_value": answer}
                with patch("builtins.input", **options):
                    self.assertEqual(self.cli("--run-tests")[0], 0)

    def test_change_after_confirmation_blocks_execution(self):
        def answer(*args):
            (self.root / "studio.py").write_text("def stuk(\n", encoding="utf-8")
            return "ja"
        with patch("builtins.input", side_effect=answer), patch.object(studio, "run_bounded", side_effect=AssertionError("Niet starten")):
            self.assertEqual(self.cli("--run-tests")[0], 1)

    def test_test_failure_zero_tests_timeout_and_output_limit(self):
        cases = (subprocess.CompletedProcess([], 1, b"FICTIEF_GEHEIM", b""),
                 subprocess.CompletedProcess([], 0, b"", b"Ran 0 tests in 0.01s\nOK\n"),
                 subprocess.CompletedProcess([], 0, b"", b"Ran 3 tests in 0.01s\nOK (skipped=3)\n"),
                 subprocess.TimeoutExpired("tests", 1), studio.OutputLimitExceeded("limiet"), OSError("fout"))
        for case in cases:
            with self.subTest(case=case), patch("builtins.input", return_value="ja"):
                options = {"side_effect": case} if isinstance(case, Exception) else {"return_value": case}
                with patch.object(studio, "run_bounded", **options):
                    code, out, err = self.cli("--run-tests")
                self.assertEqual(code, 1)
                self.assertNotIn("FICTIEF_GEHEIM", out + err)

    def test_interrupt_during_tests_returns_130(self):
        with patch("builtins.input", return_value="ja"), patch.object(studio, "run_bounded", side_effect=KeyboardInterrupt):
            self.assertEqual(self.cli("--run-tests")[0], 130)


if __name__ == "__main__":
    unittest.main()
