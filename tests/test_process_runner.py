"""Echte begrensde processen, uitsluitend korte fixtures en tijdelijke mappen."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import process_runner


class ProcessRunnerTests(unittest.TestCase):
    def command(self, code, *arguments):
        return [sys.executable, "-I", "-S", "-B", "-c", code, *arguments]

    def test_separate_output_and_exitcode(self):
        result = process_runner.run_bounded(
            self.command("import sys; print('out'); print('err',file=sys.stderr); sys.exit(7)"), timeout=5)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout.strip(), b"out")
        self.assertEqual(result.stderr.strip(), b"err")

    def test_output_limit_is_shared_by_stdout_and_stderr(self):
        code = "import os; os.write(1,b'a'*8192); os.write(2,b'b'*8192)"
        with self.assertRaises(process_runner.OutputLimitExceeded):
            process_runner.run_bounded(self.command(code), timeout=5, output_limit=12000)

    def test_exact_output_limit_is_allowed(self):
        result = process_runner.run_bounded(self.command("import os; os.write(1,b'x'*8192)"),
                                            timeout=5, output_limit=8192)
        self.assertEqual(len(result.stdout), 8192)
        self.assertEqual(result.stderr, b"")

    def test_unbounded_writer_is_stopped_promptly(self):
        start = time.monotonic()
        with self.assertRaises(process_runner.OutputLimitExceeded):
            process_runner.run_bounded(self.command("import os\nwhile True: os.write(2,b'x'*8192)"),
                                       timeout=10, output_limit=32768)
        self.assertLess(time.monotonic() - start, 4)

    def test_timeout_stops_direct_process(self):
        start = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            process_runner.run_bounded(self.command("import time; time.sleep(20)"), timeout=0.4)
        self.assertLess(time.monotonic() - start, 3)

    def test_timeout_kills_descendant_holding_output_pipe(self):
        # Test zowel normale opstart als een opstart die de oude 0,8s-grens
        # overschrijdt. De echte processen en pijpen worden niet gemockt.
        for startup_delay in (0, 1):
            with self.subTest(startup_delay=startup_delay), tempfile.TemporaryDirectory() as temporary:
                pidfile = Path(temporary) / "child.pid"
                readyfile = Path(temporary) / "child.ready"
                code = ("import subprocess,sys,time; from pathlib import Path; "
                        "time.sleep(float(sys.argv[3])); "
                        "child=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time; time.sleep(60)']); "
                        "Path(sys.argv[1]).write_text(str(child.pid)); "
                        "Path(sys.argv[2]).touch(); time.sleep(60)")
                startup_timeout = 15
                deadline_observed = []
                real_clock = time.monotonic

                def clock_after_ready():
                    now = real_clock()
                    if readyfile.is_file():
                        if not deadline_observed:
                            deadline_observed.append(now)
                        # Alleen de runner-klok schuift vooruit: pas na het
                        # schrijven van de PID verloopt de uitvoerdeadline.
                        return now + startup_timeout
                    return now

                with patch.object(process_runner, "time", SimpleNamespace(monotonic=clock_after_ready)):
                    with self.assertRaises(subprocess.TimeoutExpired):
                        process_runner.run_bounded(self.command(
                            code, str(pidfile), str(readyfile), str(startup_delay)), timeout=startup_timeout)
                self.assertTrue(deadline_observed, "De fixture startte niet binnen de afzonderlijke opstartlimiet")
                self.assertLess(real_clock() - deadline_observed[0], process_runner.CLEANUP_TIMEOUT + 2)
                self.assertTrue(pidfile.is_file(), "De fixture moet echt een kindproces hebben gestart")
                self.assert_process_stopped(int(pidfile.read_text()))

    def test_success_also_cleans_up_lingering_descendant(self):
        with tempfile.TemporaryDirectory() as temporary:
            pidfile = Path(temporary) / "child.pid"
            code = ("import subprocess,sys; from pathlib import Path; "
                    "child=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time; time.sleep(20)'],"
                    "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                    "Path(sys.argv[1]).write_text(str(child.pid))")
            result = process_runner.run_bounded(self.command(code, str(pidfile)), timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assert_process_stopped(int(pidfile.read_text()))

    def assert_process_stopped(self, pid):
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            api = ctypes.WinDLL("kernel32", use_last_error=True)
            api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            api.OpenProcess.restype = wintypes.HANDLE
            api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            api.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
            if handle:
                try:
                    self.assertEqual(api.WaitForSingleObject(handle, 1000), 0)
                finally:
                    api.CloseHandle(handle)
        else:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            # Op Linux kan een gestopt kind kort als zombie op reaping wachten.
            statfile = Path(f"/proc/{pid}/stat")
            self.assertTrue(statfile.exists())
            self.assertEqual(statfile.read_text().split(")", 1)[1].split()[0], "Z")

    def test_interrupt_cleans_up_before_reraising(self):
        original = subprocess.Popen
        processes = []
        def factory(*args, **kwargs):
            process = original(*args, **kwargs)
            real_poll = process.poll
            calls = 0
            def interrupt_once():
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise KeyboardInterrupt
                return real_poll()
            process.poll = interrupt_once
            processes.append(process)
            return process
        with patch.object(process_runner.subprocess, "Popen", side_effect=factory):
            with self.assertRaises(KeyboardInterrupt):
                process_runner.run_bounded(self.command("import time; time.sleep(20)"), timeout=5)
        self.assertIsNotNone(processes[0].returncode)
        self.assert_process_stopped(processes[0].pid)

    @unittest.skipUnless(os.name == "nt", "Windows Job Object-controle")
    def test_failed_job_assignment_never_starts_project_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "not-started.txt"
            with patch.object(process_runner.WindowsJob, "assign", side_effect=OSError("fixture")):
                with self.assertRaises(OSError):
                    process_runner.run_bounded(self.command(
                        "import sys; from pathlib import Path; Path(sys.argv[1]).write_text('started')", str(marker)), timeout=5)
            self.assertFalse(marker.exists())

    def test_shell_and_command_strings_are_rejected(self):
        with self.assertRaises(ValueError):
            process_runner.run_bounded("python anything", timeout=1)
        with self.assertRaises(ValueError):
            process_runner.run_bounded(self.command("pass"), shell=True, timeout=1)
        literal = "argument; & echo not-a-command"
        result = process_runner.run_bounded(self.command("import sys; print(sys.argv[1])", literal), timeout=5)
        self.assertEqual(result.stdout.decode().strip(), literal)


if __name__ == "__main__":
    unittest.main()
