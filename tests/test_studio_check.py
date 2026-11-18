"""Check-controles met tijdelijke mappen en nagebootste subprocessen."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import studio


class CheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.manifest = json.loads(studio.MANIFEST_PATH.read_text(encoding="utf-8"))

    def project(self, kind="python", version="1.0.0"):
        directory = self.root / "voorbeeld"
        directory.mkdir()
        data = {"schema_version": 1, "project": {"name": "voorbeeld"},
                "generator": {"version": "1.0.0"}, "template": {"id": kind, "version": version}}
        (directory / studio.METADATA_FILE).write_text(json.dumps(data), encoding="utf-8-sig")
        for name in self.manifest["templates"][kind]["files"]:
            path = directory / name.replace("project_package", "voorbeeld")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# fictieve fixture\n', encoding="utf-8")
        if kind != "web":
            (directory / "pyproject.toml").write_text('[project]\nname="voorbeeld"\n', encoding="utf-8")
        return directory

    def cli(self, *extra):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = studio.main(["check", "voorbeeld", "--root", str(self.root), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_standard_mode_does_not_execute_code_or_change_files(self):
        directory = self.project()
        marker = directory / "executed.txt"
        (directory / "tests/test_greeting.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n", encoding="utf-8")
        before = {p.relative_to(directory): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in directory.rglob("*") if p.is_file()}
        with patch.object(studio, "run_bounded", side_effect=AssertionError("Geen subprocess zonder eigen Git")):
            code, output, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("PASS Metadata", output)
        self.assertIn("WARN Git", output)
        self.assertIn("SKIP Tests", output)
        self.assertIn("Samenvatting", output)
        self.assertFalse(marker.exists())
        self.assertEqual(before, {p.relative_to(directory): (p.read_bytes(), p.stat().st_mtime_ns)
                                  for p in directory.rglob("*") if p.is_file()})

    def test_all_template_types_have_static_configuration_checks(self):
        for kind in studio.PROJECT_TYPES:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                old_root = self.root
                self.root = Path(temporary).resolve()
                try:
                    self.project(kind)
                    self.assertEqual(self.cli()[0], 0)
                finally:
                    self.root = old_root

    def test_missing_configuration_fails_and_tests_are_not_offered(self):
        directory = self.project()
        (directory / "pyproject.toml").unlink()
        with patch("builtins.input", side_effect=AssertionError("Geen bevestiging")), patch.object(studio, "run_bounded", side_effect=AssertionError("Geen uitvoer")
        ):
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("FAIL pyproject.toml", output)
        self.assertIn("SKIP Tests", output)

    def test_invalid_toml_and_metadata_fail_safely_without_leaking_content(self):
        directory = self.project()
        (directory / "pyproject.toml").write_text("FICTIEF-GEHEIM = [", encoding="utf-8")
        code, output, _ = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("FAIL pyproject-inhoud", output)
        self.assertNotIn("FICTIEF-GEHEIM", output)
        (directory / studio.METADATA_FILE).write_text("FICTIEF-GEHEIM", encoding="utf-8")
        self.assertNotIn("FICTIEF-GEHEIM", self.cli()[1])
        self.assertEqual(self.cli()[0], 1)

    def test_missing_metadata_and_unknown_project_do_not_run_git(self):
        with patch.object(studio, "run_bounded", side_effect=AssertionError("Niet uitvoeren")):
            self.assertEqual(self.cli()[0], 1)
            (self.root / "voorbeeld").mkdir()
            self.assertEqual(self.cli()[0], 1)

    def test_traversal_absolute_ads_and_device_names_are_rejected(self):
        for name in ("..", "../escape", "a/b", "a\\b", "C:\\temp", "C:temp", "/tmp", "a:stream", "con", "nul", "lpt1", "com\u00b9", "a.", " a", ""):
            with self.subTest(name=name), self.assertRaises((OSError, ValueError)):
                studio.check_path(self.root, name)

    def test_junction_project_is_rejected_before_metadata_or_subprocess(self):
        directory = self.project()
        lstat = Path.lstat
        def fake(path, *args, **kwargs):
            if path == directory:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return lstat(path, *args, **kwargs)
        with patch.object(Path, "lstat", new=fake), patch.object(studio, "run_bounded") as run:
            self.assertEqual(self.cli()[0], 1)
        run.assert_not_called()

    def test_junction_in_required_configuration_blocks_tests(self):
        directory = self.project()
        lstat = Path.lstat
        def fake(path, *args, **kwargs):
            if path == directory / ".github":
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return lstat(path, *args, **kwargs)
        with patch.object(Path, "lstat", new=fake), patch("builtins.input", side_effect=AssertionError("Geen tests")), patch.object(studio, "run_bounded"
        ) as run:
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("FAIL .github/workflows", output)
        run.assert_not_called()

    def test_project_local_executables_and_startup_hooks_are_not_trusted(self):
        directory = self.project()
        filename = "git.exe" if os.name == "nt" else "git"
        (directory / filename).write_bytes(b"niet uitvoeren")
        with patch.dict(os.environ, {"PATH": str(directory), "GIT_DIR": "extern",
                                    "GIT_CONFIG_PARAMETERS": "injectie", "PYTHONPATH": "project",
                                    "NODE_OPTIONS": "--require project-code"}):
            self.assertIsNone(studio.trusted_executable("git", self.root))
            environment = studio.child_environment()
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("GIT_CONFIG_PARAMETERS", environment)
        self.assertNotIn("PYTHONPATH", environment)
        self.assertNotIn("NODE_OPTIONS", environment)
        self.assertEqual(environment["GIT_OPTIONAL_LOCKS"], "0")

    def test_unknown_template_version_keeps_checks_but_skips_tests(self):
        self.project(version=None)
        with patch("builtins.input", side_effect=AssertionError("Geen tests")):
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 0)
        self.assertIn("WARN Templateversie", output)
        self.assertIn("SKIP Tests", output)

    def test_unsupported_test_policy_is_not_taken_from_metadata(self):
        directory = self.project()
        data = json.loads((directory / studio.METADATA_FILE).read_text(encoding="utf-8-sig"))
        data["test_command"] = ["onveilig-programma"]
        (directory / studio.METADATA_FILE).write_text(json.dumps(data), encoding="utf-8")
        with patch.dict(studio.TRUSTED_TESTS, {}, clear=True), patch.object(studio, "run_bounded") as run:
            self.assertIn("SKIP Tests", self.cli("--run-tests")[1])
        run.assert_not_called()

    def test_clean_and_dirty_git_status_use_only_hardened_read_commands(self):
        directory = self.project()
        (directory / ".git").mkdir()
        for status, expected in ((b"", "PASS"), (b" M README.md\n", "WARN"), (b"?? nieuw.txt\n", "WARN")):
            responses = [SimpleNamespace(returncode=0, stdout=b"core.repositoryformatversion\0"),
                         SimpleNamespace(returncode=0, stdout=str(directory).encode() + b"\n"),
                         SimpleNamespace(returncode=0, stdout=status)]
            before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
            with patch.object(studio, "trusted_executable", return_value="C:/trusted/git.exe"), patch.object(studio, "run_bounded", side_effect=responses
            ) as run:
                result = studio.git_check(studio.read_project(directory))
            self.assertEqual(result.status, expected)
            for call in run.call_args_list:
                self.assertFalse(call.kwargs["shell"])
                self.assertEqual(call.kwargs["timeout"], studio.GIT_TIMEOUT)
                self.assertEqual(call.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
                self.assertIn("--no-optional-locks", call.args[0])
                self.assertIn("core.fsmonitor=false", call.args[0])
            self.assertEqual(before, {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()})

    def test_git_missing_repo_worktree_other_root_timeout_and_failure(self):
        directory = self.project()
        project = studio.read_project(directory)
        self.assertEqual(studio.git_check(project).status, "WARN")
        (directory / ".git").write_text("gitdir: ../extern", encoding="utf-8")
        self.assertEqual(studio.git_check(project).status, "WARN")
        (directory / ".git").unlink()
        (directory / ".git").mkdir()
        with patch.object(studio, "trusted_executable", return_value=None):
            self.assertEqual(studio.git_check(project).status, "WARN")
        for response in (SimpleNamespace(returncode=0, stdout=str(self.root).encode()),
                         SimpleNamespace(returncode=1, stdout=b""),
                         subprocess.TimeoutExpired("git", 10), FileNotFoundError()):
            with self.subTest(response=type(response).__name__), patch.object(
                studio, "trusted_executable", return_value="git"
            ), patch.object(studio, "run_bounded", side_effect=response if isinstance(response, Exception) else None,
                            return_value=response):
                self.assertEqual(studio.git_check(project).status, "FAIL")

    def test_git_filters_are_disabled_and_config_includes_are_not_followed(self):
        directory = self.project()
        (directory / ".git").mkdir()
        responses = [SimpleNamespace(returncode=0, stdout=b"filter.demo.clean\0filter.demo.process\0"),
                     SimpleNamespace(returncode=0, stdout=str(directory).encode() + b"\n"),
                     SimpleNamespace(returncode=0, stdout=b"")]
        with patch.object(studio, "trusted_executable", return_value="git"), patch.object(studio, "run_bounded", side_effect=responses
        ) as run:
            self.assertEqual(studio.git_check(studio.read_project(directory)).status, "PASS")
        self.assertIn("--no-includes", run.call_args_list[0].args[0])
        self.assertIn("filter.demo.clean=", run.call_args.args[0])
        self.assertIn("filter.demo.process=", run.call_args.args[0])
        for key in (b"include.path\0", b"includeIf.gitdir:elsewhere.path\0"):
            with patch.object(studio, "trusted_executable", return_value="git"), patch.object(studio, "run_bounded", return_value=SimpleNamespace(returncode=0, stdout=key)
            ) as run:
                self.assertEqual(studio.git_check(studio.read_project(directory)).status, "WARN")
                self.assertEqual(run.call_count, 1)

    def test_git_indirections_are_rejected_before_any_git_process(self):
        directory = self.project()
        gitdir = directory / ".git"
        gitdir.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        marker = outside / "config"
        marker.write_bytes(b"fictieve-niet-lezen-data")
        for relative in ("commondir", "gitdir", "config.worktree", "objects/info/alternates",
                         "objects/info/http-alternates"):
            with self.subTest(relative=relative):
                pointer = gitdir / relative
                pointer.parent.mkdir(parents=True, exist_ok=True)
                pointer.write_text(str(outside), encoding="utf-8")
                with patch.object(studio, "run_bounded") as run:
                    result = studio.git_check(studio.read_project(directory))
                self.assertEqual(result.status, "FAIL")
                self.assertIn("geen Git-opdracht gestart", result.message)
                run.assert_not_called()
                self.assertEqual(marker.read_bytes(), b"fictieve-niet-lezen-data")
                pointer.unlink()

    def test_git_worktree_configuration_is_not_used_for_status(self):
        directory = self.project()
        (directory / ".git").mkdir()
        with patch.object(studio, "trusted_executable", return_value="git"), patch.object(
            studio, "run_bounded", return_value=SimpleNamespace(returncode=0, stdout=b"core.worktree\0")
        ) as run:
            result = studio.git_check(studio.read_project(directory))
        self.assertEqual(result.status, "WARN")
        self.assertEqual(run.call_count, 1)

    def test_git_output_limit_has_safe_failure_result(self):
        directory = self.project()
        (directory / ".git").mkdir()
        with patch.object(studio, "trusted_executable", return_value="git"), patch.object(
            studio, "run_bounded", side_effect=studio.OutputLimitExceeded("FICTIEVE-GEHEIME-UITVOER")
        ):
            result = studio.git_check(studio.read_project(directory))
        self.assertEqual(result.status, "FAIL")
        self.assertIn("Uitvoerlimiet", result.message)
        self.assertNotIn("FICTIEVE-GEHEIME-UITVOER", result.message)

    def test_test_output_limit_stops_remaining_web_commands(self):
        self.project(kind="web")
        with patch.object(studio, "trusted_executable", return_value="C:/trusted/node.exe"), patch(
            "builtins.input", return_value="ja"
        ), patch.object(studio, "run_bounded", side_effect=studio.OutputLimitExceeded("FICTIEVE-GEHEIME-UITVOER")) as run:
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("Uitvoerlimiet", output)
        self.assertNotIn("FICTIEVE-GEHEIME-UITVOER", output)
        self.assertEqual(run.call_count, 1)

    def test_timeout_stops_remaining_web_commands(self):
        self.project(kind="web")
        with patch.object(studio, "trusted_executable", return_value="C:/trusted/node.exe"), patch(
            "builtins.input", return_value="ja"
        ), patch.object(studio, "run_bounded", side_effect=subprocess.TimeoutExpired("python", 60)) as run:
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("Tijdslimiet", output)
        self.assertEqual(run.call_count, 1)

    def test_tests_require_explicit_yes_and_warning_precedes_prompt(self):
        self.project()
        for answer in ("", "nee", "q", "yes", EOFError(), KeyboardInterrupt()):
            with self.subTest(answer=type(answer).__name__), patch("builtins.input", side_effect=[answer]), patch.object(studio, "run_bounded"
            ) as run:
                code, output, _ = self.cli("--run-tests")
                self.assertEqual(code, 0)
                self.assertIn("WAARSCHUWING: tests voeren projectcode uit", output)
                self.assertIn("Opdracht:", output)
                self.assertIn("Geannuleerd", output)
                run.assert_not_called()

    def test_allowed_test_success_failure_and_timeout(self):
        self.project()
        for response, expected in ((SimpleNamespace(returncode=0), "PASS Tests"),
                                   (SimpleNamespace(returncode=1), "FAIL Tests"),
                                   (subprocess.TimeoutExpired("python", 60), "FAIL Tests")):
            with self.subTest(expected=expected), patch("builtins.input", return_value="ja"), patch.object(studio, "run_bounded", side_effect=response if isinstance(response, Exception) else None,
                return_value=response
            ) as run:
                code, output, _ = self.cli("--run-tests")
                self.assertEqual(code, 0 if expected.startswith("PASS") else 1)
                self.assertIn(expected, output)
                args = run.call_args.args[0]
                self.assertEqual(args, [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"])
                self.assertFalse(run.call_args.kwargs["shell"])
                self.assertEqual(run.call_args.kwargs["timeout"], studio.TEST_TIMEOUT)

    def test_web_commands_are_fixed_and_missing_node_never_installs(self):
        self.project(kind="web")
        with patch.object(studio, "trusted_executable", return_value=None), patch.object(studio, "run_bounded") as run:
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("testhulpmiddel ontbreekt", output)
        run.assert_not_called()
        with patch.object(studio, "trusted_executable", return_value="C:/trusted/node.exe"):
            commands = studio.test_commands(studio.read_project(self.root / "voorbeeld"))
        self.assertEqual(commands[1], ["C:/trusted/node.exe", "--test", "tests/counter.test.cjs"])

    def test_configuration_swap_after_confirmation_is_refused(self):
        directory = self.project()
        def answer(prompt):
            (directory / "pyproject.toml").unlink()
            return "ja"
        with patch("builtins.input", side_effect=answer), patch.object(studio, "run_bounded") as run:
            self.assertEqual(self.cli("--run-tests")[0], 1)
        run.assert_not_called()

    def test_metadata_version_swap_after_confirmation_is_refused(self):
        directory = self.project()
        def answer(prompt):
            path = directory / studio.METADATA_FILE
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            data["template"]["version"] = "9.0.0"
            path.write_text(json.dumps(data), encoding="utf-8")
            return "ja"
        with patch("builtins.input", side_effect=answer), patch.object(studio, "run_bounded") as run:
            self.assertEqual(self.cli("--run-tests")[0], 1)
        run.assert_not_called()

    def test_manifest_version_change_after_confirmation_blocks_tests(self):
        self.project()
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        def answer(prompt):
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["templates"]["python"]["version"] = "2.0.0"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            return "ja"
        with patch.object(studio, "MANIFEST_PATH", manifest), patch("builtins.input", side_effect=answer), patch.object(studio, "run_bounded"
        ) as run:
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("Geen testopdracht gestart", output)
        run.assert_not_called()

    def test_executable_change_after_confirmation_blocks_tests(self):
        self.project(kind="web")
        with patch.object(studio, "trusted_executable", side_effect=["C:/trusted/node.exe", "C:/other/node.exe"]), patch(
            "builtins.input", return_value="ja"
        ), patch.object(studio, "run_bounded") as run:
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("Geen testopdracht gestart", output)
        run.assert_not_called()

    def test_unreadable_subtree_blocks_test_start(self):
        self.project()
        def unreadable_walk(path, *, followlinks, onerror):
            onerror(PermissionError("Fictieve onleesbare map"))
            return iter(())
        with patch.object(studio.os, "walk", side_effect=unreadable_walk), patch(
            "builtins.input", return_value="ja"
        ), patch.object(studio, "run_bounded") as run:
            self.assertEqual(self.cli("--run-tests")[0], 1)
        run.assert_not_called()

    def test_unreadable_git_subtree_is_not_silently_skipped(self):
        directory = self.project()
        (directory / ".git").mkdir()
        def unreadable_walk(path, *, followlinks, onerror):
            onerror(PermissionError("Fictieve onleesbare Git-map"))
            return iter(())
        with patch.object(studio.os, "walk", side_effect=unreadable_walk), patch.object(studio, "run_bounded") as run:
            self.assertEqual(studio.git_check(studio.read_project(directory)).status, "FAIL")
        run.assert_not_called()

    def test_later_precheck_failure_preserves_earlier_test_result(self):
        directory = self.project(kind="web")
        def first_test(*args, **kwargs):
            (directory / "README.md").unlink()
            return SimpleNamespace(returncode=0)
        with patch.object(studio, "trusted_executable", return_value="C:/trusted/node.exe"), patch(
            "builtins.input", return_value="ja"
        ), patch.object(studio, "run_bounded", side_effect=first_test) as run:
            code, output, _ = self.cli("--run-tests")
        self.assertEqual(code, 1)
        self.assertIn("PASS Tests", output)
        self.assertIn("FAIL Tests", output)
        self.assertIn("Eerder gestarte tests kunnen bestanden hebben gewijzigd", output)
        self.assertNotIn("Geen testopdracht gestart", output)
        self.assertEqual(run.call_count, 1)

    def test_real_git_status_is_read_only_for_clean_and_changed_tree(self):
        directory = self.project()
        git = studio.trusted_executable("git", self.root)
        if git is None:
            self.skipTest("Vertrouwde Git-executable niet beschikbaar.")
        result = subprocess.run([git, "-c", "init.templateDir=", "init", "--quiet", str(directory)],
                                env=studio.child_environment(), shell=False, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        info = directory / ".git/info"
        info.mkdir(exist_ok=True)
        exclude = info / "exclude"
        exclude.write_text("*\n", encoding="utf-8")
        def snapshot():
            return {p.relative_to(directory): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in directory.rglob("*") if p.is_file()}
        before = snapshot()
        self.assertEqual(studio.git_check(studio.read_project(directory)).status, "PASS")
        self.assertEqual(before, snapshot())
        exclude.write_text("", encoding="utf-8")
        before = snapshot()
        self.assertEqual(studio.git_check(studio.read_project(directory)).status, "WARN")
        self.assertEqual(before, snapshot())
        # Maak ook een echte index in deze tijdelijke fixture, zonder commit.
        added = subprocess.run([git, "-C", str(directory), "add", "--", "pyproject.toml"],
                               env=studio.child_environment(), shell=False, capture_output=True, timeout=10)
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertTrue((directory / ".git/index").is_file())
        before = snapshot()
        self.assertEqual(studio.git_check(studio.read_project(directory)).status, "WARN")
        self.assertEqual(before, snapshot())

    def test_untrusted_manifest_path_is_refused_without_execution(self):
        self.project()
        manifest = self.root / "manifest.json"
        self.manifest["templates"]["python"]["files"] = ["../.env"]
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        with patch.object(studio, "MANIFEST_PATH", manifest), patch.object(studio, "run_bounded") as run:
            self.assertEqual(self.cli("--run-tests")[0], 1)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
