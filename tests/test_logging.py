"""Logging blijft gescheiden van rapporten en neemt geen foutcontext over."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import backup
import create_project
import dashboard
import reporting
import restore
import studio
import studio_logging


SECRET = "FICTIEVE-SLEUTEL-EN-PERSOONLIJK-PAD"


class LoggingTests(unittest.TestCase):
    def capture(self, callback):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = callback()
        self.assertNotIn(SECRET, out.getvalue() + err.getvalue())
        self.assertNotIn("Traceback", out.getvalue() + err.getvalue())
        return code, out.getvalue(), err.getvalue()

    def test_only_stderr_without_root_handlers_or_files(self):
        root_output = StringIO()
        handler = logging.StreamHandler(root_output)
        logging.getLogger().addHandler(handler)
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(
                logging, "FileHandler", side_effect=AssertionError("Geen logbestand")
            ):
                before = list(Path(directory).iterdir())
                _, out, err = self.capture(lambda: studio_logging.log_event("COMMAND_FAILED"))
                self.assertEqual(list(Path(directory).iterdir()), before)
            self.assertEqual(out, "")
            self.assertIn("[ERROR] COMMAND_FAILED:", err)
            self.assertEqual(root_output.getvalue(), "")
        finally:
            logging.getLogger().removeHandler(handler)
        self.assertEqual(len(studio_logging._LOGGER.handlers), 1)
        self.assertFalse(studio_logging._LOGGER.propagate)

    def test_record_arguments_exception_and_stack_are_never_formatted(self):
        def emit():
            try:
                raise RuntimeError(SECRET)
            except RuntimeError:
                studio_logging._LOGGER.error("COMMAND_FAILED", SECRET, exc_info=True,
                                             stack_info=True, extra={"personal": SECRET})
                studio_logging._LOGGER.error(SECRET)
        _, out, err = self.capture(emit)
        self.assertEqual(out, "")
        self.assertIn("UNKNOWN_EVENT", err)
        self.assertEqual(len(err.splitlines()), 2)

    def test_unknown_object_is_not_converted_to_text(self):
        class Untrusted:
            def __str__(self):
                raise AssertionError("Niet omzetten")
        _, _, err = self.capture(lambda: studio_logging.log_event(Untrusted()))
        self.assertIn("UNKNOWN_EVENT", err)

    def test_broken_stderr_does_not_fall_back_to_stdout(self):
        stream = StringIO()
        stream.close()
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(stream):
            studio_logging.log_event("COMMAND_FAILED")
        self.assertEqual(out.getvalue(), "")

    def test_report_json_on_success_and_unexpected_failure(self):
        for command in ("quality", "release-check", "benchmark"):
            for failed in (False, True):
                with self.subTest(command=command, failed=failed):
                    def collect():
                        if failed:
                            raise RuntimeError(SECRET)
                        return reporting.build([studio.CheckResult("PASS", "Controle", "Veilig")],
                                               False, command=command)
                    code, out, err = self.capture(lambda: reporting.run(
                        collect, output_format="json", command=command))
                    data = json.loads(out)
                    self.assertEqual(code, int(failed))
                    self.assertEqual(data["exit_code"], code)
                    self.assertEqual(data["command"], command)
                    if failed:
                        self.assertIn("COMMAND_FAILED", err)
                    else:
                        self.assertEqual(err, "")

    def test_report_write_failure_preserves_json_and_exitcode(self):
        with patch.object(reporting, "prepare_destination", return_value=object()), patch.object(
            reporting, "save", side_effect=OSError(SECRET)
        ):
            code, out, err = self.capture(lambda: reporting.run(
                lambda: reporting.build([], False), output_format="json", output="result.json"))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["exit_code"], 3)
        self.assertIn("REPORT_WRITE_FAILED", err)

    def test_invalid_destination_does_not_repeat_input(self):
        with patch.object(reporting, "prepare_destination", side_effect=ValueError(SECRET)):
            code, out, err = self.capture(lambda: reporting.run(
                lambda: self.fail("Collector mag niet starten"),
                output_format="json", output=SECRET))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["exit_code"], 3)
        self.assertIn("REPORT_TARGET_INVALID", err)

    def test_cancelled_collection_preserves_json_and_exitcode(self):
        def collect():
            raise KeyboardInterrupt
        code, out, err = self.capture(lambda: reporting.run(collect, output_format="json"))
        self.assertEqual(code, 130)
        self.assertEqual(json.loads(out)["completion"], "cancelled")
        self.assertIn("COMMAND_CANCELLED", err)

    def test_cli_emergency_json_does_not_leak_import_or_runtime_errors(self):
        for command in ("quality", "release-check", "benchmark"):
            with patch.object(studio, "_main", side_effect=RuntimeError(SECRET)):
                code, out, err = self.capture(lambda: studio.main([command, "--format=json"]))
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["exit_code"], 1)
            self.assertIn("COMMAND_FAILED", err)

    def test_argparse_does_not_repeat_unknown_values(self):
        for main, argv in ((studio.main, [SECRET]),
                           (create_project.main, ["voorbeeld", "--type", SECRET])):
            def run():
                with self.assertRaises(SystemExit) as raised:
                    main(argv)
                return raised.exception.code
            code, out, err = self.capture(run)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("CLI_INVALID", err)

    def test_generator_backup_and_restore_do_not_echo_exceptions(self):
        cases = ((create_project, "create_project", RuntimeError(SECRET),
                  lambda: create_project.main(["voorbeeld", "--type", "python"]), "GENERATOR_FAILED"),
                 (backup, "make_plan", ValueError(SECRET),
                  lambda: backup.run(Path("."), "voorbeeld", Path("doel"), False), "BACKUP_FAILED"),
                 (restore, "inspect", restore.RestoreError(SECRET),
                  lambda: restore.run(Path("voorbeeld.zip"), Path("nieuw"), False), "RESTORE_FAILED"))
        for module, method, error, call, event in cases:
            with self.subTest(event=event), patch.object(module, method, side_effect=error):
                code, out, err = self.capture(call)
            self.assertEqual(code, 1)
            self.assertEqual(out, "")
            self.assertIn(event, err)

    def test_dashboard_errors_never_include_request_or_exception(self):
        _, out, err = self.capture(lambda: dashboard.Server.handle_error(
            None, SECRET, (SECRET, 12345)))
        self.assertEqual(out, "")
        self.assertIn("DASHBOARD_HTTP_ERROR", err)
        with patch.object(dashboard, "local_root", side_effect=RuntimeError(SECRET)):
            code, out, err = self.capture(lambda: dashboard.serve(Path(SECRET)))
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("DASHBOARD_START_FAILED", err)

    def test_encoding_failure_keeps_json_valid(self):
        with patch.object(reporting, "encoded", side_effect=RuntimeError(SECRET)):
            code, out, err = self.capture(lambda: reporting.run(
                lambda: reporting.build([], False), output_format="json"))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["exit_code"], 3)
        self.assertIn("REPORT_TOO_LARGE", err)


if __name__ == "__main__":
    unittest.main()
