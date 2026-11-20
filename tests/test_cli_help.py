"""Nederlandse hulp en veilige invoerfouten met behoud van CLI/JSON-contract."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import create_project
import quality
import reporting
import studio
import studio_logging


class DutchCLITests(unittest.TestCase):
    def parse(self, main, arguments, expected):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            main(arguments)
        self.assertEqual(raised.exception.code, expected)
        return out.getvalue(), err.getvalue()

    def test_all_studio_help_is_dutch_without_execution(self):
        commands = (None, "menu", "list", "check", "updates", "dashboard", "quality",
                    "maintenance", "backup", "restore", "benchmark", "release-check")
        with patch.object(studio, "run_bounded", side_effect=AssertionError("Geen uitvoering")):
            for command in commands:
                with self.subTest(command=command):
                    out, err = self.parse(studio.main, ([command] if command else []) + ["--help"], 0)
                    self.assertIn("Gebruik:", out)
                    self.assertIn("Opties:", out)
                    self.assertIn("Toon deze hulptekst en stop", out)
                    self.assertIn("Voorbeeld:", out)
                    self.assertNotIn("show this help", out)
                    self.assertNotIn("positional arguments:", out)
                    self.assertEqual(err, "")

    def test_generator_help_preserves_options_and_never_starts_menu(self):
        with patch.object(create_project, "interactive_arguments", side_effect=AssertionError("Geen menu")):
            out, err = self.parse(create_project.main, ["--help"], 0)
        self.assertIn("Argumenten:", out)
        self.assertIn("--template-version", out)
        self.assertIn("--type", out)
        self.assertEqual(err, "")

    def test_missing_project_and_restore_target_get_actionable_errors(self):
        for args in (["check"], ["backup"], ["restore", "voorbeeld.zip"]):
            with self.subTest(args=args):
                out, err = self.parse(studio.main, args, 2)
                self.assertEqual(out, "")
                self.assertIn("CLI_INVALID:", err)
                self.assertIn("Er ontbreken verplichte", err)
                self.assertIn("Voorbeeld:", err)
                self.assertNotIn("Traceback", err)

    def test_unknown_backup_option_explains_output_without_reflecting_values(self):
        secret = "FICTIEVE-GEHEIME-WAARDE"
        out, err = self.parse(studio.main, ["backup", "voorbeeld", "--destination", secret], 2)
        self.assertEqual(out, "")
        self.assertIn("niet ondersteund", err)
        self.assertIn("--output", err)
        self.assertNotIn(secret, err)

    def test_invalid_format_missing_value_and_number_do_not_leak_input(self):
        secret = "FICTIEVE-GEHEIME-WAARDE"
        cases = ((["quality", "--format", secret], "niet beschikbaar"),
                 (["list", "--root"], "mist een waarde"),
                 (["benchmark", "--projects", secret], "verwachte vorm"))
        for args, message in cases:
            with self.subTest(args=args):
                out, err = self.parse(studio.main, args, 2)
                self.assertEqual(out, "")
                self.assertIn(message, err)
                self.assertNotIn(secret, err)

    def test_json_schema_results_and_exitcodes_remain_unchanged(self):
        for status, code in (("PASS", 0), ("FAIL", 1)):
            report = reporting.build([studio.CheckResult(status, "Controle", "Vaste veilige melding")])
            out, err = StringIO(), StringIO()
            with patch.object(quality, "collect", return_value=report), redirect_stdout(out), redirect_stderr(err):
                result = studio.main(["quality", "--format", "json"])
            self.assertEqual(result, code)
            self.assertEqual(json.loads(out.getvalue()), report.as_dict())
            self.assertNotIn("Gebruik:", out.getvalue())

    def test_operational_error_codes_remain_stable_and_have_next_steps(self):
        for event in ("BACKUP_FAILED", "RESTORE_FAILED", "GENERATOR_FAILED"):
            stream = StringIO()
            with redirect_stderr(stream):
                studio_logging.log_event(event)
            self.assertIn(event + ":", stream.getvalue())
            self.assertIn("--output", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
