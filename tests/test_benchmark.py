"""Benchmark gebruikt alleen eigen fictieve data; geen echte projectroot."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import benchmark
import reporting
import studio


class BenchmarkTests(unittest.TestCase):
    def cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(["benchmark", *args])
        return code, out.getvalue(), err.getvalue()

    def test_real_benchmark_covers_four_types_and_removes_own_data(self):
        created = []
        real = benchmark.make_workspace
        def create():
            workspace = real()
            created.append(workspace.path)
            return workspace
        with patch.object(benchmark, "make_workspace", side_effect=create), \
             patch.object(studio, "run_bounded", side_effect=AssertionError("Geen subprocess")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("Geen processen")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")):
            code, out, err = self.cli("--projects", "4", "--repeat", "1", "--format", "json")
        self.assertEqual(code, 0, err)
        data = json.loads(out)
        self.assertEqual(data["command"], "benchmark")
        self.assertFalse(data["tests_requested"])
        info = data["benchmark"]
        self.assertEqual(info["project_types"], {kind: 1 for kind in benchmark.TYPES})
        self.assertTrue(info["dataset_unchanged"])
        self.assertTrue(info["temporary_files_removed"])
        self.assertFalse(info["project_tests_executed"])
        self.assertEqual([item["operation"] for item in info["timings"]], ["list", "updates", "check"])
        self.assertTrue(created)
        self.assertTrue(all(not path.exists() for path in created))
        self.assertNotIn(str(created[0]), out)

    def test_all_project_functions_receive_only_benchmark_root(self):
        with tempfile.TemporaryDirectory() as folder:
            real_project = Path(folder) / "Projects" / "echte-projectmap"
            real_project.mkdir(parents=True)
            sentinel = real_project / "BEWAREN.txt"
            sentinel.write_bytes(b"ongewijzigd")
            before = sentinel.read_bytes(), sentinel.stat().st_mtime_ns
            recorded = []
            def wrap(function):
                def call(root, *args, **kwargs):
                    path = Path(root)
                    self.assertEqual(path.name, "projects")
                    self.assertTrue(path.parent.name.startswith(benchmark.PREFIX))
                    self.assertNotEqual(path, real_project.parent)
                    recorded.append(path)
                    return function(root, *args, **kwargs)
                return call
            with patch.object(studio, "list_projects", side_effect=wrap(studio.list_projects)), \
                 patch.object(studio, "project_updates", side_effect=wrap(studio.project_updates)), \
                 patch.object(studio, "check_project", side_effect=wrap(studio.check_project)):
                code, _, _ = self.cli("--projects", "4", "--repeat", "1")
            self.assertEqual(code, 0)
            self.assertTrue(recorded)
            self.assertEqual(before, (sentinel.read_bytes(), sentinel.stat().st_mtime_ns))
            self.assertEqual([p.name for p in real_project.iterdir()], ["BEWAREN.txt"])

    def test_timing_statistics_are_correct_and_include_one_warmup(self):
        calls = []
        def operation():
            calls.append(1)
            return "OK"
        counter = iter([0, 1_000_000, 10_000_000, 13_000_000, 20_000_000, 22_000_000])
        with patch.object(benchmark.time, "perf_counter_ns", side_effect=lambda: next(counter)):
            timing = benchmark.measure("list", operation, lambda value: self.assertEqual(value, "OK"),
                                       4, 3, float("inf"))
        self.assertEqual(len(calls), 4)
        self.assertEqual(timing.samples_ms, (1.0, 3.0, 2.0))
        self.assertEqual((timing.min_ms, timing.median_ms, timing.mean_ms, timing.max_ms), (1, 2, 2, 3))
        self.assertEqual(timing.projects_per_second, 2000)

    def test_zero_duration_does_not_produce_infinite_json(self):
        with patch.object(benchmark.time, "perf_counter_ns", return_value=0):
            timing = benchmark.measure("list", lambda: None, lambda _: None, 4, 1, float("inf"))
        self.assertIsNone(timing.projects_per_second)
        json.dumps(timing.as_dict(), allow_nan=False)

    def test_invalid_limits_or_path_options_never_create_workspace(self):
        for arguments in (("--projects", "0"), ("--projects", "201"), ("--repeat", "0"),
                          ("--repeat", "11"), ("--projects", "geen-getal"),
                          ("--root", "C:\\Projects"), ("--output", "rapport.json"), ("--run-tests",)):
            with self.subTest(arguments=arguments), patch.object(benchmark, "make_workspace", side_effect=AssertionError("Niet aanmaken")):
                with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                    studio.main(["benchmark", *arguments])
                self.assertEqual(error.exception.code, 2)

    def test_temp_basis_inside_studio_or_project_is_refused(self):
        with patch.object(benchmark.tempfile, "gettempdir", return_value=str(Path(studio.__file__).parent)):
            with self.assertRaises(ValueError):
                benchmark.make_workspace()
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            (parent / studio.METADATA_FILE).write_text("{}", encoding="utf-8")
            with patch.object(benchmark.tempfile, "gettempdir", return_value=str(parent)), self.assertRaises(ValueError):
                benchmark.make_workspace()
            self.assertEqual([path.name for path in parent.iterdir()], [studio.METADATA_FILE])

    def test_cleanup_refuses_wrong_absolute_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            path = parent / (benchmark.PREFIX + "bewaren")
            path.mkdir()
            sentinel = path / "BEWAREN.txt"
            sentinel.write_bytes(b"bewaren")
            forged = benchmark.Workspace(path, parent / "verkeerde-ouder", benchmark.identity(path))
            with self.assertRaises(ValueError):
                benchmark.cleanup(forged)
            self.assertEqual(sentinel.read_bytes(), b"bewaren")

    def test_failure_and_interrupt_clean_only_their_workspace(self):
        real = benchmark.make_workspace
        for failure, code in ((ValueError("fout"), 1), (KeyboardInterrupt(), 130)):
            created = []
            def create():
                workspace = real()
                created.append(workspace.path)
                return workspace
            with self.subTest(failure=failure), patch.object(benchmark, "make_workspace", side_effect=create), \
                 patch.object(studio, "list_projects", side_effect=failure):
                report = benchmark.collect(4, 1)
            self.assertEqual(report.exit_code, code)
            self.assertTrue(report.benchmark.temporary_files_removed)
            self.assertTrue(all(not path.exists() for path in created))

    def test_manifest_limits_and_unexpected_outcomes_fail_safely(self):
        for limit in ("MAX_FILES", "MAX_BYTES"):
            with self.subTest(limit=limit), patch.object(benchmark, limit, 0), \
                 patch.object(benchmark, "make_workspace", side_effect=AssertionError("Niet aanmaken")):
                self.assertEqual(benchmark.collect(4, 1).exit_code, 1)
        with patch.object(studio, "project_updates", return_value=([], [], 0)):
            report = benchmark.collect(4, 1)
        self.assertEqual(report.exit_code, 1)
        self.assertEqual(report.completion, "error")
        self.assertTrue(report.benchmark.temporary_files_removed)

    def test_incomplete_cleanup_is_never_reported_as_success(self):
        created = []
        real_make, real_cleanup = benchmark.make_workspace, benchmark.cleanup
        def create():
            workspace = real_make()
            created.append(workspace)
            return workspace
        try:
            with patch.object(benchmark, "make_workspace", side_effect=create), patch.object(benchmark, "cleanup", return_value=None):
                report = benchmark.collect(4, 1)
            self.assertEqual(report.exit_code, 1)
            self.assertFalse(report.benchmark.temporary_files_removed)
            self.assertTrue(any(item.status == "FAIL" and item.label == "Opruimen" for item in report.results))
        finally:
            for workspace in created:
                real_cleanup(workspace)
        with patch.object(studio, "MANIFEST_PATH", Path("niet-aanwezig-manifest.json")):
            self.assertEqual(benchmark.collect(4, 1).exit_code, 1)
        with patch.object(studio, "list_projects", return_value=([], [])):
            report = benchmark.collect(4, 1)
            self.assertEqual(report.exit_code, 1)
            self.assertTrue(report.benchmark.temporary_files_removed)

    def test_time_limit_failure_cleans_own_workspace(self):
        with patch.object(benchmark, "TIME_LIMIT", -1):
            report = benchmark.collect(4, 1)
        self.assertEqual(report.exit_code, 1)
        self.assertTrue(report.benchmark.temporary_files_removed)

    def test_report_formats_show_measurements(self):
        report = benchmark.collect(4, 1)
        self.assertEqual(report.exit_code, 0)
        for output_format in reporting.FORMATS:
            text = reporting.render(report, output_format)
            self.assertIn("list", text)
            self.assertIn("updates", text)
            self.assertIn("check", text)
        self.assertIn("Mediaan ms", reporting.render(report, "markdown"))


if __name__ == "__main__":
    unittest.main()
