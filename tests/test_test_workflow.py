"""Een ontbrekend hulpmiddel of falende suite mag nooit een groen resultaat geven."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_tests


class TestWorkflowTests(unittest.TestCase):
    def test_missing_node_returns_failure_even_when_python_passes(self):
        with patch.object(run_tests.shutil, "which", return_value=None), patch.object(
            run_tests.subprocess, "run", return_value=SimpleNamespace(returncode=0)
        ), redirect_stdout(StringIO()):
            self.assertEqual(run_tests.main(), 1)

    def test_failing_suite_does_not_prevent_other_checks_and_returns_failure(self):
        results = [SimpleNamespace(stdout="v22.0.0"), SimpleNamespace(returncode=1)]
        results.extend(SimpleNamespace(returncode=0) for _ in range(5))
        with patch.object(run_tests.shutil, "which", return_value="node"), patch.object(
            run_tests.subprocess, "run", side_effect=results
        ) as run, redirect_stdout(StringIO()):
            self.assertEqual(run_tests.main(), 1)
        self.assertEqual(run.call_count, 7)


if __name__ == "__main__":
    unittest.main()
