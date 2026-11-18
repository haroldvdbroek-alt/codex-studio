"""Begrensde subprocessen met procesboom-opruiming, uitsluitend standaardbibliotheek."""

import os
import signal
import subprocess
import sys
import threading
import time

MAX_OUTPUT_BYTES = 1024 * 1024
CLEANUP_TIMEOUT = 2


class OutputLimitExceeded(subprocess.SubprocessError):
    """De gezamenlijke limiet voor stdout en stderr is bereikt."""


class ProcessCleanupError(OSError):
    """Procesboom of uitvoer kon niet binnen de opruimlimiet worden gestopt."""


class WindowsJob:
    """Een anoniem Job Object, zonder breakaway, dat alle leden bij sluiten stopt."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", wintypes.DWORD), ("min_working_set", ctypes.c_size_t),
                        ("max_working_set", ctypes.c_size_t), ("active_limit", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                        ("scheduling", wintypes.DWORD)]

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("basic", BasicLimits), ("io", IoCounters),
                        ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                        ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]

        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, args, result in (
            ("CreateJobObjectW", [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            ("SetInformationJobObject", [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            ("AssignProcessToJobObject", [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            ("OpenProcess", [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
        ):
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, pid: int) -> None:
        import ctypes
        process = self.api.OpenProcess(0x0101, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.api.CloseHandle(process)

    def close(self) -> None:
        if self.handle:
            if not self.api.CloseHandle(self.handle):
                raise ProcessCleanupError("Windows-procesgroep kon niet worden gesloten.")
            self.handle = None


# De wrapper start de echte opdracht pas nadat de ouder hem in het Job Object
# heeft geplaatst. -I -S blokkeert lokale imports en site/startuphooks vóór die poort.
WINDOWS_GATE = (
    "import os,sys,subprocess; "
    "token=os.read(0,1); "
    "sys.exit(subprocess.run(sys.argv[1:],stdin=subprocess.DEVNULL,shell=False).returncode "
    "if token==b'1' else 125)"
)


def run_bounded(command, *, cwd=None, env=None, shell=False, capture_output=True,
                timeout, output_limit=MAX_OUTPUT_BYTES) -> subprocess.CompletedProcess:
    """Bewaart maximaal output_limit bytes totaal, met aparte stdout/stderr.

    De deadline omvat wachten op proces en pijpen. Opruimen heeft een aparte,
    begrensde termijn. Procescreatie zelf blijft een OS-operatie zonder harde deadline.
    """
    if shell or not capture_output or isinstance(command, (str, bytes)) or not command:
        raise ValueError("Alleen expliciete argumentlijsten zonder shell zijn toegestaan.")
    if timeout <= 0 or output_limit <= 0:
        raise ValueError("Tijd- en uitvoerlimieten moeten positief zijn.")
    deadline = time.monotonic() + timeout
    process, job = None, None
    readers = []
    changed, exceeded, read_failed = threading.Event(), threading.Event(), threading.Event()
    buffers = [bytearray(), bytearray()]
    lock = threading.Lock()

    def read_pipe(pipe, buffer):
        try:
            while True:
                chunk = os.read(pipe.fileno(), 8192)
                if not chunk:
                    break
                with lock:
                    available = max(0, output_limit - sum(len(item) for item in buffers))
                    buffer.extend(chunk[:available])
                    if len(chunk) > available:
                        exceeded.set()
                changed.set()
                if exceeded.is_set():
                    break
        except OSError:
            read_failed.set()
        finally:
            pipe.close()
            changed.set()

    try:
        if os.name == "nt":
            job = WindowsJob()
            args = [sys.executable, "-I", "-S", "-B", "-c", WINDOWS_GATE, *command]
            process = subprocess.Popen(args, cwd=cwd, env=env, shell=False, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            job.assign(process.pid)  # Bij falen wordt de poort nooit geopend.
        elif os.name == "posix":
            process = subprocess.Popen(command, cwd=cwd, env=env, shell=False, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        else:
            raise OSError("Procesboombeheer is op dit platform niet beschikbaar.")
        for pipe, buffer in zip((process.stdout, process.stderr), buffers):
            reader = threading.Thread(target=read_pipe, args=(pipe, buffer), daemon=True)
            reader.start()
            readers.append(reader)
        if os.name == "nt":
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(command, timeout)
            process.stdin.write(b"1")
            process.stdin.close()
        while True:
            if exceeded.is_set():
                raise OutputLimitExceeded("Subprocessuitvoer overschrijdt de bytegrens.")
            if read_failed.is_set():
                raise OSError("Subprocessuitvoer kon niet veilig worden gelezen.")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            if process.poll() is not None and all(not reader.is_alive() for reader in readers):
                break
            changed.wait(min(0.02, remaining))
            changed.clear()
        return subprocess.CompletedProcess(command, process.returncode, bytes(buffers[0]), bytes(buffers[1]))
    finally:
        # Ook na succes worden gewone achtergebleven kinderen opgeruimd.
        cleanup_deadline = time.monotonic() + CLEANUP_TIMEOUT
        try:
            if job is not None:
                job.close()
            elif process is not None and os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                try:
                    process.wait(timeout=max(0.01, cleanup_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    raise ProcessCleanupError("Proces kon niet tijdig worden gestopt.") from None
                if process.stdin is not None and not process.stdin.closed:
                    process.stdin.close()
                for reader in readers:
                    reader.join(timeout=max(0, cleanup_deadline - time.monotonic()))
                if any(reader.is_alive() for reader in readers):
                    raise ProcessCleanupError("Uitvoerpijpen bleven na het stoppen geopend.")
                for pipe in (process.stdout, process.stderr):
                    if pipe is not None and not pipe.closed:
                        pipe.close()
