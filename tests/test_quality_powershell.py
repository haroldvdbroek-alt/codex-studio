"""Geen taakregistratie of policywijziging; alleen parser- en tijdelijke proeven."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-quality.ps1"
POWERSHELL = (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" /
              "WindowsPowerShell/v1.0/powershell.exe")


def windows_ps_environment(env=None):
    # PowerShell 7 voegt eigen modules toe die Windows PowerShell 5.1 niet kan
    # laden. Laat 5.1 zijn eigen standaardmodulepaden kiezen; wijzig geen policy.
    clean = dict(os.environ if env is None else env)
    for name in list(clean):
        if name.casefold() == "psmodulepath":
            del clean[name]
    return clean


def ps_command(code, *, env=None):
    return subprocess.run([str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", code],
                          capture_output=True, text=True, errors="replace", shell=False, timeout=30,
                          env=windows_ps_environment(env))


class ScriptSourceTests(unittest.TestCase):
    def test_windows_powershell_uses_own_module_paths_without_changing_policy(self):
        original = {"PSModulePath": "fictieve-powershell-7-modules", "KEEP": "voorbeeld",
                    "PSExecutionPolicyPreference": "Restricted"}
        with patch.object(subprocess, "run") as run:
            ps_command("Get-ExecutionPolicy", env=original)
        environment = run.call_args.kwargs["env"]
        self.assertNotIn("PSModulePath", environment)
        self.assertEqual(environment["KEEP"], "voorbeeld")
        self.assertEqual(environment["PSExecutionPolicyPreference"], "Restricted")
        self.assertIn("PSModulePath", original)
        self.assertNotIn("-ExecutionPolicy", run.call_args.args[0])

    def test_script_has_no_tests_installation_or_policy_bypass_flags(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("--run-tests", "-ExecutionPolicy", "Register-ScheduledTask", "schtasks",
                          "Set-ExecutionPolicy", "Unblock-File", "Invoke-Expression", "Install-Module",
                          "pip install", "npm install", "Schedule.Service"):
            self.assertNotIn(forbidden.casefold(), text.casefold())
        self.assertIn("--format', 'json', '--output'", text)

    @unittest.skipUnless(os.name == "nt" and POWERSHELL.is_file(), "Windows PowerShell-parser vereist")
    def test_real_powershell_ast_has_only_expected_native_invocation(self):
        env = dict(os.environ)
        env["CODEX_SCRIPT_TO_PARSE"] = str(SCRIPT)
        code = """
$tokens = $null
$parseErrors = $null
$tree = [System.Management.Automation.Language.Parser]::ParseFile($env:CODEX_SCRIPT_TO_PARSE, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { exit 1 }
$commands = @($tree.FindAll({param($node) $node -is [System.Management.Automation.Language.CommandAst]}, $true))
$native = @($commands | Where-Object { $_.InvocationOperator -eq 'Ampersand' })
if ($native.Count -ne 1 -or $native[0].CommandElements[0].Extent.Text -ne '$checkedPython' -or $native[0].CommandElements[1].Extent.Text -ne '@qualityArguments') { exit 2 }
$parameters = @($tree.ParamBlock.Parameters | ForEach-Object { $_.Name.VariablePath.UserPath })
if (($parameters -join ',') -ne 'PythonPath,ReportDirectory') { exit 3 }
Write-Output 'AST_OK'
"""
        result = ps_command(code, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AST_OK", result.stdout)


@unittest.skipUnless(os.name == "nt" and POWERSHELL.is_file(), "Windows PowerShell vereist")
class ScriptExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="codex-ps-quality-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.app = self.base / "Studio & voorbeeld"
        (self.app / "scripts").mkdir(parents=True)
        shutil.copyfile(SCRIPT, self.app / "scripts/run-quality.ps1")
        self.reports = self.base / "Rapporten & voorbeeld $waarde"
        self.reports.mkdir()
        # Een vertrouwde fixture controleert de argumenten zonder echte projecten,
        # Git, netwerk of taken te benaderen. Dit is geen vervanging van studio.py.
        (self.app / "studio.py").write_text("""from pathlib import Path
import json, os, sys
assert sys.flags.ignore_environment and sys.flags.no_site and sys.dont_write_bytecode
assert sys.argv[1:4] == ['quality', '--format', 'json']
assert sys.argv[4] == '--output' and len(sys.argv) == 6
assert Path.cwd() == Path(__file__).resolve().parent
code_file = Path(__file__).with_name('test-exitcode.txt')
code = int(code_file.read_text()) if code_file.exists() else 0
report = {'schema_version':1, 'command':'quality', 'tests_requested':False, 'exit_code':code}
with Path(sys.argv[5]).open('x',encoding='utf-8') as output:
    json.dump(report,output)
print(json.dumps(report))
sys.exit(code)
""", encoding="utf-8")
        policy = ps_command("Get-ExecutionPolicy")
        self.policy = policy.stdout.strip()
        self.assertEqual(policy.returncode, 0, policy.stderr)

    def require_allowed_policy(self):
        if self.policy not in {"RemoteSigned", "Unrestricted", "Bypass"}:
            self.skipTest("Bestaande uitvoerpolicy " + self.policy + " staat dit niet-ondertekende testscript niet toe; beleid niet gewijzigd.")

    def execute(self, *, python=None, directory=None, extra=()):
        return subprocess.run([str(POWERSHELL), "-NoProfile", "-NonInteractive", "-File",
                               str(self.app / "scripts/run-quality.ps1"), "-PythonPath",
                               str(sys.executable if python is None else python), "-ReportDirectory",
                               str(self.reports if directory is None else directory), *extra],
                              cwd=self.base, text=True, errors="replace", capture_output=True,
                              shell=False, timeout=30, env=windows_ps_environment())

    def test_restricted_policy_blocks_execution_without_side_effects(self):
        if self.policy != "Restricted":
            self.skipTest("Deze proef geldt alleen bij bestaande Restricted-policy.")
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UnauthorizedAccess", result.stderr)
        self.assertEqual(list(self.reports.iterdir()), [])

    def test_allowed_execution_is_read_only_and_uses_unique_reports(self):
        self.require_allowed_policy()
        for _ in range(2):
            result = self.execute()
            self.assertEqual(result.returncode, 0, result.stderr)
        reports = list(self.reports.glob("quality-*.json"))
        self.assertEqual(len(reports), 2)
        for path in reports:
            self.assertFalse(json.loads(path.read_bytes())["tests_requested"])
        self.assertFalse(list(self.app.rglob("__pycache__")))

    def test_quality_failure_exit_code_is_preserved(self):
        self.require_allowed_policy()
        (self.app / "test-exitcode.txt").write_text("1", encoding="ascii")
        result = self.execute()
        self.assertEqual(result.returncode, 1, result.stderr)
        path = next(self.reports.glob("*.json"))
        self.assertEqual(json.loads(path.read_bytes())["exit_code"], 1)

    def test_missing_python_or_report_directory_creates_no_reports(self):
        self.require_allowed_policy()
        for options in ({"python": self.base / "missing/python.exe"}, {"directory": self.base / "missing"}):
            with self.subTest(options=options):
                result = self.execute(**options)
                self.assertEqual(result.returncode, 3)
                self.assertEqual(list(self.reports.iterdir()), [])

    def test_extra_run_tests_parameter_is_not_accepted(self):
        self.require_allowed_policy()
        result = self.execute(extra=("-RunTests",))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.reports.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
