"""Het menu delegeert; bestaande toestemmingsgrenzen blijven verplicht."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import backup
import create_project
import quality
import restore
import studio
import studio_menu


class StudioMenuTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.project = self.root / "voorbeeld"
        self.project.mkdir()
        (self.project / studio.METADATA_FILE).write_text(json.dumps({
            "schema_version": 1, "generator": {"version": "1.0.0"},
            "project": {"name": "voorbeeld"}, "template": {"id": "python", "version": "1.0.0"}
        }), encoding="utf-8")

    def invoke(self, answers, *, tty=True):
        out, err = StringIO(), StringIO()
        with patch.object(sys.stdin, "isatty", return_value=tty), \
             patch("builtins.input", side_effect=answers), redirect_stdout(out), redirect_stderr(err):
            result = studio_menu.run(self.root)
        return result, out.getvalue(), err.getvalue()

    def test_no_terminal_never_reads_input_or_starts_an_action(self):
        with patch.object(studio, "main", side_effect=AssertionError("Geen actie")):
            code, _, err = self.invoke([AssertionError("Geen invoer")], tty=False)
        self.assertEqual(code, 2)
        self.assertIn("interactieve terminal", err)

    def test_cancel_initial_menu_never_dispatches(self):
        for answer in ("", "0", "q", "annuleren", EOFError(), KeyboardInterrupt()):
            with self.subTest(answer=type(answer).__name__), patch.object(studio, "main") as dispatch:
                code, out, _ = self.invoke([answer])
            self.assertEqual(code, 0)
            self.assertIn("Geannuleerd", out)
            dispatch.assert_not_called()

    def test_invalid_choice_is_not_treated_as_a_command(self):
        with patch.object(studio, "main", return_value=0) as dispatch:
            self.assertEqual(self.invoke(["quality --run-tests", "1"])[0], 0)
        dispatch.assert_called_once_with(["list", "--root=" + str(self.root)])

    def test_read_only_options_forward_fixed_commands_without_dangerous_flags(self):
        for choice, command in (("1", "list"), ("3", "updates"), ("4", "dashboard"),
                                ("5", "quality"), ("6", "maintenance"), ("11", "release-check")):
            with self.subTest(choice=choice), patch.object(studio, "main", return_value=4) as dispatch:
                self.assertEqual(self.invoke([choice])[0], 4)
            args = dispatch.call_args.args[0]
            self.assertEqual(args[0], command)
            self.assertNotIn("--create", args)
            self.assertNotIn("--run-tests", args)
            self.assertFalse(any(arg.startswith("--output") for arg in args))

    def test_check_reuses_name_and_path_validation(self):
        with patch.object(studio, "main", return_value=0) as dispatch:
            self.assertEqual(self.invoke(["2", "voorbeeld"])[0], 0)
        dispatch.assert_called_once_with(["check", "voorbeeld", "--root=" + str(self.root)])
        for name in ("../buiten", "a/b", "C:\\temp", "--run-tests", "con", "onbekend"):
            with self.subTest(name=name), patch.object(studio, "main") as dispatch:
                self.assertEqual(self.invoke(["2", name])[0], 1)
            dispatch.assert_not_called()

    def test_backup_preview_never_requests_creation_by_default(self):
        for confirmation in ("", "nee", "yes"):
            with self.subTest(confirmation=confirmation), patch.object(studio, "main", return_value=0) as dispatch:
                self.assertEqual(self.invoke(["7", "voorbeeld", str(self.root / "backups"), confirmation])[0], 0)
            self.assertNotIn("--create", dispatch.call_args.args[0])

    def test_restore_preview_never_requests_creation_by_default(self):
        with patch.object(studio, "main", return_value=0) as dispatch:
            self.assertEqual(self.invoke(["8", str(self.root / "backup.zip"), str(self.root / "nieuw"), ""])[0], 0)
        self.assertEqual(dispatch.call_args.args[0][0], "restore")
        self.assertNotIn("--create", dispatch.call_args.args[0])

    def test_creation_flag_requires_exact_yes_and_keeps_backend_confirmation(self):
        for choice, answers in (("7", ["voorbeeld", str(self.root / "backups")]),
                                ("8", [str(self.root / "backup.zip"), str(self.root / "nieuw")])):
            with self.subTest(choice=choice), patch.object(studio, "main", return_value=0) as dispatch:
                self.assertEqual(self.invoke([choice, *answers, "ja"])[0], 0)
            self.assertIn("--create", dispatch.call_args.args[0])

    def test_real_backup_cannot_write_without_its_exact_final_confirmation(self):
        output = self.root / "backups"
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch.object(backup, "create_archive", side_effect=AssertionError("Geen toestemming")):
            self.assertEqual(self.invoke(["7", "voorbeeld", str(output), "ja", "q"])[0], 0)
        self.assertFalse(output.exists())
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_real_studio_tests_require_backend_yes(self):
        results = [studio.CheckResult("PASS", "Voorcontrole", "Geldig")]
        with patch.object(quality, "static_checks", return_value=results), \
             patch.object(studio, "run_bounded", side_effect=AssertionError("Geen testuitvoering")):
            code, _, err = self.invoke(["10", "nee"])
        self.assertEqual(code, 0)
        self.assertIn("WAARSCHUWING", err)

    def test_real_restore_requires_its_own_exact_confirmation(self):
        archive, output = self.root / "archive.zip", self.root / "nieuw"
        plan = SimpleNamespace(archive=archive, output=output, files=(), excluded_count=0)
        with patch.object(restore, "inspect", return_value=plan), patch.object(restore, "restore") as write:
            self.assertEqual(self.invoke(["8", str(archive), str(output), "ja", "q"])[0], 0)
        write.assert_not_called()
        self.assertFalse(output.exists())

    def test_real_project_tests_require_backend_yes(self):
        create_project.create_project("testbaar", self.root)
        with patch.object(studio, "run_bounded", side_effect=AssertionError("Geen testuitvoering")):
            code, out, _ = self.invoke(["9", "testbaar", "nee"])
        self.assertEqual(code, 0, out)
        self.assertIn("WAARSCHUWING", out)

    def test_real_generator_cancellation_never_creates_project(self):
        destination = self.root / "nieuwe-projecten"
        with patch.object(create_project, "DEFAULT_OUTPUT", destination), \
             patch.object(create_project, "create_project") as write:
            self.assertEqual(self.invoke(["13", "1", "demo-app", "", "nee"])[0], 0)
        write.assert_not_called()
        self.assertFalse(destination.exists())

    def test_project_tests_delegate_only_to_the_existing_check_confirmation(self):
        with patch.object(studio, "main", return_value=0) as dispatch:
            self.assertEqual(self.invoke(["9", "voorbeeld"])[0], 0)
        dispatch.assert_called_once_with(["check", "voorbeeld", "--root=" + str(self.root), "--run-tests"])

    def test_benchmark_requires_explicit_yes_before_any_temporary_files(self):
        for answer in ("", "nee", "q", EOFError(), KeyboardInterrupt()):
            with self.subTest(answer=type(answer).__name__), patch.object(studio, "main") as dispatch:
                self.assertEqual(self.invoke(["12", answer])[0], 0)
            dispatch.assert_not_called()
        with patch.object(studio, "main", return_value=0) as dispatch:
            self.assertEqual(self.invoke(["12", "ja"])[0], 0)
        dispatch.assert_called_once_with(["benchmark"])

    def test_new_project_reuses_generator_menu_without_presupplied_permission(self):
        with patch.object(create_project, "main", return_value=0) as create:
            self.assertEqual(self.invoke(["13"])[0], 0)
        create.assert_called_once_with([])

    def test_cancelling_followup_inputs_dispatches_nothing(self):
        for prefix in (["2"], ["7", "voorbeeld"], ["8"], ["8", "backup.zip"]):
            for ending in ("q", EOFError(), KeyboardInterrupt()):
                with self.subTest(prefix=prefix, ending=type(ending).__name__), patch.object(studio, "main") as dispatch:
                    self.assertEqual(self.invoke([*prefix, ending])[0], 0)
                dispatch.assert_not_called()

    def test_main_entrypoints_load_same_menu_and_preserve_cli(self):
        for args in ([], ["menu"], ["menu", "--root", str(self.root)]):
            with patch.object(studio_menu, "run", return_value=0) as run:
                self.assertEqual(studio.main(args), 0)
            run.assert_called_once_with(self.root if "--root" in args else None)
        with redirect_stdout(StringIO()):
            self.assertEqual(studio.main(["list", "--root", str(self.root)]), 0)

    def test_fresh_menu_cancellation_creates_no_files_or_bytecode(self):
        app = self.root / "studio-copy"
        app.mkdir()
        for name in ("studio.py", "studio_menu.py", "studio_logging.py", "process_runner.py"):
            (app / name).write_bytes((ROOT / name).read_bytes())
        before = {p.name: p.read_bytes() for p in app.iterdir()}
        code = ("import io,runpy,sys; sys.path.insert(0,sys.argv[1]); "
                "sys.stdin=io.StringIO('q\\n'); sys.stdin.isatty=lambda:True; "
                "sys.argv=[sys.argv[1]+'/studio.py']; runpy.run_path(sys.argv[0],run_name='__main__')")
        result = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(app)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in app.iterdir()})


if __name__ == "__main__":
    unittest.main()
