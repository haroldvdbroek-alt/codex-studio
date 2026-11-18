"""Dashboardtests met tijdelijke projecten en echte loopback-HTTP-verzoeken."""

import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio
import dashboard


class APITests(unittest.TestCase):
    def setUp(self):
        self.snapshot = SimpleNamespace(read=lambda: dashboard.encode({
            "projects": [{"name": '<script>alert("voorbeeld")</script>'}],
            "warnings": [], "state": "GEREED"}))
        self.server = dashboard.Server(self.snapshot)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def request(self, path="/api/projects", method="GET", headers=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            conn.request(method, path, headers=headers or {})
            result = conn.getresponse()
            return result.status, dict(result.getheaders()), result.read()
        finally:
            conn.close()

    def test_binds_only_ipv4_loopback_and_free_port(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertGreater(self.server.server_address[1], 0)

    def test_api_json_headers_and_no_http_execution(self):
        with patch.object(studio, "run_bounded", side_effect=AssertionError("Geen HTTP-opdracht")), \
             patch.object(studio, "check_project", side_effect=AssertionError("Geen HTTP-controle")):
            code, headers, payload = self.request()
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(payload)["state"], "GEREED")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_static_allowlist_and_traversal(self):
        for route in ("/", "/static/app.js", "/static/style.css"):
            self.assertEqual(self.request(route)[0], 200)
        for route in ("/static/../studio.py", "/static/%2e%2e/studio.py", "/static/", "/.env",
                      "/api/projects?root=C:/", "/api/tests", "/api/projects/../check",
                      "/static/%252e%252e/studio.py", "/static\\..\\studio.py"):
            with self.subTest(route=route):
                self.assertEqual(self.request(route)[0], 404)

    def test_all_other_methods_are_rejected(self):
        for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", "TRACE", "CONNECT", "CUSTOM"):
            with self.subTest(method=method):
                code, headers, _ = self.request(method=method)
                self.assertEqual(code, 405)
                self.assertEqual(headers["Allow"], "GET")

    def test_host_and_origin_validation(self):
        for headers in ({"Host": "evil.example"}, {"Origin": "https://evil.example"},
                        {"Origin": "null"}, {"Origin": "http://127.0.0.1:1"},
                        {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request(headers=headers)[0], 403)
        self.assertEqual(self.request(headers={"Origin": "http://" + self.server.authority})[0], 200)

    def test_duplicate_and_missing_host_or_origin_rejected(self):
        for headers in ([], [("Host", self.server.authority), ("Host", self.server.authority)],
                        [("Host", self.server.authority), ("Origin", "null"), ("Origin", "null")]):
            conn = http.client.HTTPConnection(*self.server.server_address, timeout=3)
            try:
                conn.putrequest("GET", "/api/projects", skip_host=True)
                for key, value in headers:
                    conn.putheader(key, value)
                conn.endheaders()
                result = conn.getresponse()
                self.assertEqual(result.status, 403)
                result.read()
            finally:
                conn.close()

    def test_frontend_renders_untrusted_text_without_html_interpretation(self):
        js = self.request("/static/app.js")[2].decode()
        self.assertIn("cell.textContent = String(value)", js)
        self.assertIn("item.textContent = warning", js)
        for forbidden in ("innerHTML", "outerHTML", "document.write", "insertAdjacentHTML", "eval("):
            self.assertNotIn(forbidden, js)
        code, headers, payload = self.request()
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(payload)["projects"][0]["name"], '<script>alert("voorbeeld")</script>')
        self.assertNotIn(b"<script>alert", self.request("/")[2])

    def test_concurrency_limit_closes_excess_request(self):
        for _ in range(8):
            self.server.slots.acquire()
        try:
            with self.assertRaises((http.client.RemoteDisconnected, ConnectionResetError)):
                self.request()
        finally:
            for _ in range(8):
                self.server.slots.release()


class CollectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.project = self.root / "voorbeeld"
        self.project.mkdir()
        self.data = {"schema_version": 1, "project": {"name": "Voorbeeld"},
                     "generator": {"version": "1.0.0"},
                     "template": {"id": "python", "version": "1.0.0"}}
        self.metadata = self.project / studio.METADATA_FILE
        self.save()

    def save(self):
        self.metadata.write_text(json.dumps(self.data), encoding="utf-8")

    def test_collection_is_read_only_and_never_runs_tests_or_network(self):
        (self.project / "source.py").write_text("raise RuntimeError('NIET UITVOEREN')", encoding="utf-8")
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.project.iterdir()}
        with patch.object(studio, "run_project_tests", side_effect=AssertionError("Geen tests")), \
             patch.object(studio, "run_bounded", side_effect=AssertionError("Geen eigen Git")), \
             patch.object(socket, "socket", side_effect=AssertionError("Geen netwerk")):
            data = dashboard.collect(self.root)
        self.assertEqual(data["projects"][0]["tests"], "NIET_UITGEVOERD")
        self.assertEqual(data["projects"][0]["update"], "ACTUEEL")
        self.assertEqual(data["projects"][0]["configuration"], "FAIL")
        self.assertEqual(data["projects"][0]["git"], "WARN")
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.project.iterdir()})

    def test_bad_metadata_hidden_and_does_not_leak_content(self):
        for text in ('{"private":"voorbeeld-geheim",', '[]', '{"schema_version":true}',
                     '{"schema_version":1,"schema_version":1}',
                     json.dumps(self.data)[:-1] + ',"extra":NaN}',
                     json.dumps(self.data)[:-1] + ',"extra":Infinity}'):
            with self.subTest(text=text):
                self.metadata.write_text(text, encoding="utf-8")
                data = dashboard.collect(self.root)
                self.assertEqual(data["projects"][0]["type"], "ONBEKEND")
                self.assertEqual(data["projects"][0]["git"], "SKIP")
                self.assertTrue(data["warnings"])
                self.assertNotIn("voorbeeld-geheim", json.dumps(data))

    def test_unknown_type_and_invalid_versions_are_rejected(self):
        for key, value in (("id", "onbekend"), ("version", "1.0")):
            with self.subTest(key=key):
                original = dict(self.data["template"])
                self.data["template"][key] = value
                self.save()
                self.assertEqual(dashboard.collect(self.root)["projects"][0]["type"], "ONBEKEND")
                self.data["template"] = original

    def test_manifest_missing_does_not_crash(self):
        with patch.object(studio, "MANIFEST_PATH", self.root / "absent.json"):
            result = dashboard.collect(self.root)
        self.assertEqual(result["projects"][0]["update"], "ONBEKEND")
        self.assertEqual(result["projects"][0]["configuration"], "FAIL")
        self.assertTrue(result["warnings"])

    def test_directory_and_project_limits(self):
        with patch.object(dashboard, "MAX_ENTRIES", 0):
            with self.assertRaises(ValueError):
                dashboard.collect(self.root)
        with patch.object(dashboard, "MAX_PROJECTS", 0):
            data = dashboard.collect(self.root)
            self.assertEqual(data["projects"], [])
            self.assertTrue(data["warnings"])

    def test_git_tree_limits(self):
        with patch.object(dashboard, "MAX_TREE_ENTRIES", 0):
            with self.assertRaises(ValueError):
                dashboard.bounded_tree(self.project)

    def test_unc_device_and_missing_roots(self):
        for text in (r"\\server\share", r"\\?\C:\Projects", r"\\.\C:\Projects", "//server/share"):
            with self.subTest(text=text), patch.object(studio, "reject_links", side_effect=AssertionError("Voor IO weigeren")):
                with self.assertRaises(ValueError):
                    dashboard.local_root(Path(text))
        with self.assertRaises((OSError, ValueError)):
            dashboard.local_root(self.root / "missing")

    def test_reparse_root_project_and_metadata_are_rejected(self):
        real = Path.lstat
        for target in (self.root, self.project, self.metadata):
            with self.subTest(target=target):
                def fake(path):
                    if path == target:
                        return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                    return real(path)
                with patch.object(Path, "lstat", fake):
                    if target == self.root:
                        with self.assertRaises(ValueError):
                            dashboard.collect(self.root)
                    else:
                        data = dashboard.collect(self.root)
                        self.assertTrue(data["warnings"])
                        self.assertFalse(any(row["configuration"] == "PASS" for row in data["projects"]))

    def test_assets_symlink_or_junction_is_rejected_before_binding(self):
        with patch.object(studio, "read_bytes_file", side_effect=studio.UnsafePathError("link")), \
             patch.object(dashboard.HTTPServer, "server_bind", side_effect=AssertionError("Niet binden")):
            with self.assertRaises(ValueError):
                dashboard.Server(SimpleNamespace())

    def test_worker_timeout_failure_and_output_limit_keep_api_usable(self):
        for failure in (subprocess.TimeoutExpired("worker", 1), studio.OutputLimitExceeded("limiet"), OSError("fout")):
            with self.subTest(failure=failure):
                snapshot = dashboard.Snapshot(self.root)
                def fail(*args, **kwargs):
                    snapshot.stop.set()
                    raise failure
                with patch.object(studio, "run_bounded", side_effect=fail):
                    snapshot.refresh()
                self.assertEqual(json.loads(snapshot.read())["state"], "ONVOLLEDIG")

    def test_fixed_worker_command_and_successful_snapshot(self):
        snapshot = dashboard.Snapshot(self.root)
        def run(command, **kwargs):
            self.assertEqual(command[:4], [sys.executable, "-I", "-S", "-B"])
            self.assertEqual(command[-2:], ["--worker", str(self.root)])
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["timeout"], dashboard.SCAN_TIMEOUT)
            snapshot.stop.set()
            return subprocess.CompletedProcess(command, 0, dashboard.encode({"projects": [], "state": "GEREED"}), b"")
        with patch.object(studio, "run_bounded", side_effect=run):
            snapshot.refresh()
        self.assertEqual(json.loads(snapshot.read())["state"], "GEREED")

    def test_output_limit(self):
        with self.assertRaises(ValueError):
            dashboard.encode({"data": "x" * dashboard.MAX_API_BYTES})

    @unittest.skipUnless(os.name == "nt", "Windows-schijftypen")
    def test_mapped_network_drive_is_rejected_before_filesystem_access(self):
        drive = SimpleNamespace(GetDriveTypeW=SimpleNamespace())
        class RemoteDrive:
            def __call__(self, value):
                return 4
        drive.GetDriveTypeW = RemoteDrive()
        with patch.object(dashboard.ctypes, "WinDLL", return_value=drive), \
             patch.object(studio, "reject_links", side_effect=AssertionError("Geen filesystem IO")):
            with self.assertRaises(ValueError):
                dashboard.local_root(self.root)

    def test_worker_does_not_publish_bad_json_or_failed_exit(self):
        for output, code in ((b"geen JSON", 0), (b"{}", 1)):
            with self.subTest(output=output, code=code):
                snapshot = dashboard.Snapshot(self.root)
                def run(*args, **kwargs):
                    snapshot.stop.set()
                    return subprocess.CompletedProcess([], code, output, b"")
                with patch.object(studio, "run_bounded", side_effect=run):
                    snapshot.refresh()
                self.assertEqual(json.loads(snapshot.read())["state"], "ONVOLLEDIG")

    def test_studio_commands_remain_available(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(studio.main(["list", "--root", str(self.root)]), 0)
            self.assertEqual(studio.main(["updates", "--root", str(self.root)]), 0)
            self.assertEqual(studio.main(["check", "voorbeeld", "--root", str(self.root)]), 1)

    def test_real_isolated_worker(self):
        result = studio.run_bounded([sys.executable, "-I", "-S", "-B", str(Path(dashboard.__file__).absolute()),
                                     "--worker", str(self.root)], timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["projects"][0]["tests"], "NIET_UITGEVOERD")

    def test_studio_dispatch_and_start_error(self):
        with patch.object(dashboard, "serve", return_value=0) as serve:
            self.assertEqual(studio.main(["dashboard", "--root", str(self.root)]), 0)
            serve.assert_called_once_with(self.root)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(dashboard.serve(self.root / "missing"), 1)


if __name__ == "__main__":
    unittest.main()
