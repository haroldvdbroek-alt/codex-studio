"""Lokaal, alleen-lezen dashboard. HTTP leest uitsluitend een begrensde snapshot."""

import ctypes
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import socket
from socketserver import ThreadingMixIn
import subprocess
import sys
import threading

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).absolute().parent))
import studio
from studio_logging import log_event, SafeArgumentParser

MAX_ENTRIES = 500
MAX_PROJECTS = 100
MAX_TREE_ENTRIES = 2000
MAX_API_BYTES = 512 * 1024
SCAN_TIMEOUT = 12
REFRESH_SECONDS = 30
ASSET_ROOT = Path(__file__).absolute().parent / "dashboard"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/static/style.css": ("style.css", "text/css; charset=utf-8"),
          "/static/app.js": ("app.js", "text/javascript; charset=utf-8")}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'")


def local_root(value: Path) -> Path:
    """Weiger UNC/devicepaden en op Windows remote/onbekende schijven vóór lstat."""
    text = str(value.expanduser())
    if text.startswith(("\\\\", "//")) or "\x00" in text:
        raise ValueError("Gebruik een rechtstreeks lokaal schijfpad.")
    root = Path(os.path.abspath(text))
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
        api.GetDriveTypeW.restype = ctypes.c_uint
        if api.GetDriveTypeW(root.anchor) not in (2, 3, 6):
            raise ValueError("Netwerk-, onbekende en niet-ondersteunde schijven zijn niet toegestaan.")
    studio.reject_links(root)
    if not root.is_dir():
        raise ValueError("De projectroot ontbreekt.")
    return root


def bounded_tree(directory: Path) -> None:
    """Begrens Git-administratie vóór de bestaande recursieve Git-controle."""
    pending, count = [directory], 0
    while pending:
        current = pending.pop()
        studio.reject_links(current)
        with os.scandir(current) as entries:
            for entry in entries:
                count += 1
                if count > MAX_TREE_ENTRIES:
                    raise ValueError("Git-administratie te groot.")
                info = entry.stat(follow_symlinks=False)
                if studio.is_link(info):
                    raise studio.UnsafePathError("Koppeling in Git-administratie.")
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))


def collect(root: Path) -> dict:
    """Uitsluitend in de vertrouwde worker; nooit tests of projectmodules laden."""
    root = local_root(root)
    warnings, projects = [], []
    try:
        catalog = studio.update_catalog()
        if any(spec["reason"] for spec in catalog.values()):
            warnings.append("Lokaal manifest bevat ongeldige of onbekende templategegevens.")
    except (OSError, ValueError, RecursionError):
        catalog = {}
        warnings.append("Lokaal manifest ontbreekt, is ongeldig of onveilig.")
    for directory, warning in studio.project_directories(root, max_entries=MAX_ENTRIES):
        if warning:
            warnings.append("Een onveilig of onleesbaar projectpad is overgeslagen.")
            continue
        if len(projects) >= MAX_PROJECTS:
            warnings.append("Projectlimiet bereikt; overzicht onvolledig.")
            break
        try:
            data = studio.read_project_data(directory)
            if data is None:
                continue
            # Zelfde naam/padbeleid als check; metadata wordt opnieuw gevalideerd.
            directory = studio.check_path(root, directory.name)
            project = studio.read_project(directory)
            update = studio.project_update(directory, data, catalog)
            try:
                configuration = studio.configuration_checks(project, studio.template_spec(project.kind))
                config = "FAIL" if any(item.status == "FAIL" for item in configuration) else "PASS"
            except (OSError, ValueError, RecursionError):
                config = "FAIL"
            try:
                gitdir = directory / ".git"
                if os.path.lexists(gitdir):
                    studio.reject_links(gitdir)
                    if gitdir.is_dir():
                        bounded_tree(gitdir)
                git = studio.git_check(project).status
            except (OSError, ValueError):
                git = "SKIP"
            projects.append({"name": project.name, "type": project.kind,
                             "template_version": project.template_version,
                             "local_version": update.local, "update": update.status,
                             "configuration": config, "git": git, "tests": "NIET_UITGEVOERD"})
        except (OSError, ValueError, RecursionError):
            # Geen exceptiontekst, projectcode, pad of bestandinhoud publiceren.
            projects.append({"name": studio.terminal_text(directory.name)[:100], "type": "ONBEKEND",
                             "template_version": None, "local_version": None, "update": "ONBEKEND",
                             "configuration": "FAIL", "git": "SKIP", "tests": "NIET_UITGEVOERD"})
            warnings.append("Een project heeft ongeldige metadata, configuratie of een onveilig pad.")
    return {"projects": projects, "warnings": warnings,
            "state": "ONVOLLEDIG" if warnings else "GEREED"}


def encode(data: dict) -> bytes:
    result = json.dumps(data, ensure_ascii=True, allow_nan=False).encode("ascii")
    if len(result) > MAX_API_BYTES:
        raise ValueError("API-uitvoer te groot.")
    return result


def message(state: str, text: str) -> bytes:
    return encode({"projects": [], "warnings": [text], "state": state})


class Snapshot:
    """Eén worker tegelijk; HTTP kan deze niet starten of een opdracht meegeven."""
    def __init__(self, root: Path):
        self.root = root
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.payload = message("BEZIG", "Eerste controle wordt uitgevoerd.")
        self.thread = threading.Thread(target=self.refresh, daemon=True)

    def start(self):
        self.thread.start()

    def read(self):
        with self.lock:
            return self.payload

    def refresh(self):
        while not self.stop.is_set():
            try:
                # -I -S voorkomt startuphooks en project-/gebruikersimports.
                result = studio.run_bounded(
                    [sys.executable, "-I", "-S", "-B", str(Path(__file__).absolute()),
                     "--worker", str(self.root)], cwd=Path(__file__).absolute().parent,
                    env=studio.child_environment(), shell=False, capture_output=True,
                    timeout=SCAN_TIMEOUT, output_limit=MAX_API_BYTES)
                if result.returncode:
                    raise ValueError("Worker mislukt")
                payload = encode(json.loads(result.stdout))
            except Exception:
                log_event("DASHBOARD_SCAN_FAILED")
                payload = message("ONVOLLEDIG", "Controle mislukt of tijd-/uitvoerlimiet bereikt; geen volledig resultaat.")
            with self.lock:
                self.payload = payload
            if self.stop.wait(REFRESH_SECONDS):
                break

    def close(self):
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(SCAN_TIMEOUT + 5)


class Handler(BaseHTTPRequestHandler):
    server_version = "CodexStudio"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass  # Geen URL's, namen of metadata in toegangslogs.

    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def reply(self, code, body=b"", content_type="text/plain; charset=utf-8"):
        self.close_connection = True
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if code == 405:
            self.send_header("Allow", "GET")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        # Geen reflectie van onbetrouwbare requestteksten in HTML.
        self.reply(405 if code == 501 else code, b"Verzoek geweigerd.")

    def parse_request(self):
        if not super().parse_request():
            return False
        hosts = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        sites = self.headers.get_all("Sec-Fetch-Site", [])
        if (hosts != [self.server.authority] or len(origins) > 1
                or (origins and origins != ["http://" + self.server.authority])
                or len(sites) > 1 or (sites and sites[0] not in ("same-origin", "none"))):
            self.reply(403, b"Alleen toegang vanaf dit lokale dashboard.")
            return False
        return True

    def do_GET(self):
        # Exacte allowlist: geen decoding, queryparameters of filesystem-joins.
        if self.path == "/api/projects":
            self.reply(200, self.server.snapshot.read(), "application/json; charset=utf-8")
        elif self.path in self.server.assets:
            payload, mime = self.server.assets[self.path]
            self.reply(200, payload, mime)
        else:
            self.reply(404, b"Onbekende route.")


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    block_on_close = False
    request_queue_size = 8
    allow_reuse_address = False

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.slots = threading.BoundedSemaphore(8)
        # Alleen vaste lokale studio-assets; nooit projectbestanden serveren.
        self.assets = {route: (studio.read_bytes_file(ASSET_ROOT / name, 256 * 1024), mime)
                       for route, (name, mime) in ASSETS.items()}
        super().__init__(("127.0.0.1", 0), Handler)
        self.authority = "127.0.0.1:" + str(self.server_address[1])

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        def expire():
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        # Absolute deadline, ook tegen clients die langzaam headers druppelen.
        timer = threading.Timer(3, expire)
        timer.daemon = True
        timer.start()
        request.settimeout(2)
        try:
            super().process_request_thread(request, client_address)
        finally:
            timer.cancel()
            self.slots.release()

    def handle_error(self, request, client_address):
        log_event("DASHBOARD_HTTP_ERROR")


def serve(root: Path) -> int:
    snapshot = None
    try:
        snapshot = Snapshot(local_root(root))
        with Server(snapshot) as server:
            snapshot.start()
            studio.print_output("Open http://" + server.authority + "/")
            studio.print_output("Alleen-lezen dashboard. Stop met Ctrl+C; opruimen kan enkele seconden duren.")
            server.serve_forever(poll_interval=0.2)
        return 0
    except KeyboardInterrupt:
        studio.print_output("Dashboard gestopt.")
        return 0
    except Exception:
        log_event("DASHBOARD_START_FAILED")
        return 1
    finally:
        if snapshot is not None:
            snapshot.close()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        # Geïsoleerde Python neemt de scriptmap niet automatisch in sys.path op.
        try:
            sys.stdout.buffer.write(encode(collect(Path(sys.argv[2]))))
        except Exception:
            log_event("DASHBOARD_SCAN_FAILED")
            sys.exit(1)
    else:
        import argparse
        parser = SafeArgumentParser(prog="dashboard.py", description="Lokaal Codex Studio-dashboard")
        parser.add_argument("--root", type=Path, default=Path.home() / "Projects", help="Oudermap van projecten (standaard: ~/Projects)")
        sys.exit(serve(parser.parse_args().root))
