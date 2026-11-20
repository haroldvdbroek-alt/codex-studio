"""Alleen-lezen kwaliteitscontrole van de studio zelf; tests uitsluitend optioneel."""

import ast
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import warnings

import backup
import reporting
import studio

STUDIO_ROOT = Path(__file__).absolute().parent
MAX_ITEMS = 4000
MAX_LINKS = 500
STATIC_SECONDS = 30
REQUIRED = ("AGENTS.md", "README.md", "studio.py", "create_project.py", "process_runner.py",
            "dashboard.py", "dashboard/index.html", "dashboard/style.css", "dashboard/app.js",
            "backup.py", "restore.py", "quality.py", "reporting.py", "templates/manifest.json",
            "docs/WORKFLOW.md", "docs/PROJECT_CHECKLIST.md", "docs/SECURITY.md",
            "docs/BACKUPS.md", "docs/RESTORE.md", "docs/QUALITY.md",
            "scripts/run-quality.ps1", "docs/TASK_SCHEDULER.md", "release_check.py",
            "CHANGELOG.md", "docs/RELEASE.md")
PLANNED = {"web", "ai", "automation"}


def result(status, label, message):
    return studio.CheckResult(status, label, message)


def check_deadline(deadline):
    if time.monotonic() > deadline:
        raise ValueError("Controle duurt te lang.")


def regular(path):
    studio.reject_links(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Geen gewoon bestand.")


def scan_tree(directory, deadline):
    """Geen imports of bestandinhoud; alle koppelingen en grote bomen weigeren."""
    pending, files, count = [directory], [], 0
    while pending:
        current = pending.pop()
        studio.reject_links(current)
        with os.scandir(current) as entries:
            for entry in entries:
                check_deadline(deadline)
                count += 1
                if count > MAX_ITEMS:
                    raise ValueError("Te veel items.")
                path = Path(entry.path)
                info = path.lstat()
                if studio.is_link(info):
                    raise studio.UnsafePathError("Koppeling in controlemap.")
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    files.append(path)
                else:
                    raise ValueError("Bijzonder bestand in controlemap.")
    return files


def check_links(path, root):
    text = studio.read_bytes_file(path).decode("utf-8-sig")
    if text.count("```") % 2:
        raise ValueError("Niet afgesloten codeblok.")
    # Bewust eenvoudige Markdowncontrole, geen externe links of anchors ophalen.
    links = re.findall(r"\]\(([^)]+)\)", text)
    if len(links) > MAX_LINKS:
        raise ValueError("Te veel verwijzingen.")
    for link in links:
        if "://" in link or link.startswith("#") or link.startswith("mailto:"):
            continue
        link = link.split("#", 1)[0]
        if not link or "\\" in link or ":" in link or link.startswith("/"):
            raise ValueError("Onveilige documentatieverwijzing.")
        target = Path(os.path.abspath(path.parent / link))
        if not target.is_relative_to(root):
            raise ValueError("Verwijzing buiten de studio.")
        studio.reject_links(target)
        if not target.exists():
            raise ValueError("Ontbrekend verwijzingsdoel.")


def static_checks(*, include_git=True):
    deadline = time.monotonic() + STATIC_SECONDS
    root = backup.local_path(STUDIO_ROOT)
    studio.reject_links(root)
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Studio ontbreekt.")
    results, python_files = [], set()
    for name in REQUIRED:
        check_deadline(deadline)
        try:
            regular(root / name)
            results.append(result("PASS", name, "Vereist studiobestand aanwezig, gewoon bestand en geen koppeling."))
        except (OSError, ValueError):
            results.append(result("FAIL", name, "Vereist studiobestand ontbreekt, is onleesbaar of onveilig."))
    try:
        catalog = studio.update_catalog()
        if not catalog or any(item["reason"] for item in catalog.values()):
            raise ValueError("Ongeldige manifestregels.")
        results.append(result("PASS", "Manifest", "Schema, templatebeschrijvingen, versies en paden geldig."))
        for kind in sorted(studio.PROJECT_TYPES):
            check_deadline(deadline)
            if kind not in catalog:
                results.append(result("FAIL", "Template " + kind, "Beschrijving ontbreekt in manifest."))
                continue
            try:
                spec = studio.template_spec(kind)
                directory = root / "templates" / studio.safe_relative_path(spec.get("directory"))
                if not os.path.lexists(directory) and kind in PLANNED:
                    results.append(result("WARN", "Template " + kind, "Templatebron ontbreekt; op deze branch nog gepland."))
                    continue
                studio.reject_links(directory)
                if not directory.is_dir():
                    raise ValueError("Geen templatemap.")
                for name in spec["files"]:
                    check_deadline(deadline)
                    path = directory / studio.safe_relative_path(name)
                    regular(path)
                    if path.suffix == ".py":
                        python_files.add(path)
                results.append(result("PASS", "Template " + kind, "Alle gedeclareerde bronbestanden aanwezig zonder koppelingen."))
            except (OSError, ValueError):
                results.append(result("FAIL", "Template " + kind, "Aanwezige template is onvolledig of heeft een onveilig pad."))
    except (OSError, ValueError, RecursionError):
        results.append(result("FAIL", "Manifest", "Manifest ontbreekt, is ongeldig, onveilig of onvolledig."))
    try:
        with os.scandir(root) as entries:
            for count, entry in enumerate(entries, 1):
                check_deadline(deadline)
                if count > MAX_ITEMS:
                    raise ValueError("Studio te groot.")
                if entry.name.endswith(".py") and not entry.name.startswith("."):
                    path = Path(entry.path)
                    regular(path)
                    python_files.add(path)
        tests = scan_tree(root / "tests", deadline)
        python_files.update(path for path in tests if path.suffix == ".py")
        if not any(path.name.startswith("test") and path.suffix == ".py" for path in tests):
            raise ValueError("Geen testmodules.")
        results.append(result("PASS", "Tests-structuur", "Testmodules gevonden; geen tests uitgevoerd."))
    except (OSError, ValueError):
        results.append(result("FAIL", "Tests-structuur", "Onveilige, ontbrekende of te grote bron-/teststructuur, of geen testmodules."))
    for path in sorted(python_files):
        check_deadline(deadline)
        label = path.relative_to(root).as_posix()
        try:
            raw = studio.read_bytes_file(path)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Geen bronregels/secrets via parserwaarschuwingen.
                ast.parse(raw, filename=label)
            results.append(result("PASS", "Syntaxis " + label, "Python kan de syntax lezen; module niet geïmporteerd of uitgevoerd."))
        except SyntaxError as error:
            results.append(result("FAIL", "Syntaxis " + label, f"Ongeldige Python-syntaxis, regel {error.lineno}; broninhoud niet getoond."))
        except (OSError, ValueError, RecursionError):
            results.append(result("FAIL", "Syntaxis " + label, "Bron onleesbaar, onveilig, te groot of te complex."))
    for name in REQUIRED:
        if not name.endswith(".md"):
            continue
        check_deadline(deadline)
        try:
            check_links(root / name, root)
            results.append(result("PASS", "Documentatie " + name, "Lokale Markdownlinks en codeblokafsluitingen gecontroleerd."))
        except (OSError, ValueError, RecursionError):
            results.append(result("FAIL", "Documentatie " + name, "Documentatie onleesbaar/onveilig, codeblok onvolledig of lokale verwijzing ongeldig."))
    if include_git:
        try:
            check_deadline(deadline)
            gitdir = root / ".git"
            if os.path.lexists(gitdir):
                studio.reject_links(gitdir)
                if gitdir.is_dir():
                    scan_tree(gitdir, deadline)
            project = studio.Project("Codex Development Studio", "python", None, None, root)
            results.append(studio.git_check(project))
        except (OSError, ValueError):
            results.append(result("FAIL", "Git", "Git-administratie onveilig, onleesbaar, te groot of controletermijn bereikt."))
    results.append(result("SKIP", "Handmatige beoordeling", "Geen security-audit, JS/CSS-linter, browsercontrole of garantie op afwezigheid van secrets."))
    return results


def run_tests():
    root = backup.local_path(STUDIO_ROOT)
    command = [sys.executable, "-I", "-S", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    progress = lambda text: studio.print_output(text, file=sys.stderr)
    progress("WAARSCHUWING: tests voeren studiocode uit en kunnen bestanden wijzigen, processen starten of netwerkverkeer veroorzaken. Dit is geen sandbox.")
    progress("Werkmap: " + studio.terminal_text(str(root)))
    progress("Opdracht: " + studio.terminal_text(subprocess.list2cmdline(command)))
    try:
        progress("Typ ja om de vaste studio-testsuite te starten; Enter, nee of q annuleert.")
        sys.stderr.write("Doorgaan? ")
        sys.stderr.flush()
        if input().strip().casefold() != "ja":
            return result("SKIP", "Tests", "Geannuleerd; geen tests gestart.")
    except (EOFError, KeyboardInterrupt):
        return result("SKIP", "Tests", "Geannuleerd; geen tests gestart.")
    try:
        if any(item.status == "FAIL" for item in static_checks(include_git=False)):
            return result("FAIL", "Tests", "Statische controles na bevestiging mislukt; geen tests gestart.")
        completed = studio.run_bounded(command, cwd=root, env=studio.child_environment(), shell=False,
                                      capture_output=True, timeout=studio.TEST_TIMEOUT)
        if completed.returncode:
            return result("FAIL", "Tests", f"Testsuite mislukt (exitcode {completed.returncode}); ruwe uitvoer niet getoond.")
        output = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
        found = re.search(r"(?:^|\n)Ran ([0-9]+) tests? in ", output)
        skipped = re.search(r"skipped=([0-9]+)", output)
        count, skip_count = int(found[1]) if found else 0, int(skipped[1]) if skipped else 0
        if count == 0 or count <= skip_count:
            return result("FAIL", "Tests", "Geen daadwerkelijk uitgevoerde tests bevestigd; nul tests of alle tests overgeslagen.")
        return result("PASS", "Tests", f"Testsuite geslaagd: {count} gevonden, {skip_count} overgeslagen; ruwe uitvoer niet getoond.")
    except subprocess.TimeoutExpired:
        return result("FAIL", "Tests", "Tijdslimiet overschreden; procesboom gestopt. Tests kunnen bestanden hebben gewijzigd.")
    except studio.OutputLimitExceeded:
        return result("FAIL", "Tests", "Uitvoerlimiet overschreden; procesboom gestopt. Tests kunnen bestanden hebben gewijzigd.")
    except KeyboardInterrupt:
        raise
    except (OSError, ValueError, RecursionError):
        return result("FAIL", "Tests", "Testopdracht kon niet veilig worden afgerond; controleer hulpmiddelen en paden.")


def collect(with_tests=False):
    results = []
    try:
        results = static_checks()
        if not with_tests:
            tests = result("SKIP", "Tests", "Niet gevraagd; standaardmodus voert geen code uit.")
        elif any(item.status == "FAIL" for item in results):
            tests = result("SKIP", "Tests", "Niet gestart wegens mislukte statische controles.")
        else:
            counts = {status: sum(item.status == status for item in results) for status in reporting.STATUSES}
            studio.print_output("Voorcontrole: " + ", ".join(f"{count} {status}" for status, count in counts.items()), file=sys.stderr)
            tests = run_tests()
        results.append(tests)
        return reporting.build(results, with_tests)
    except KeyboardInterrupt:
        results.append(result("SKIP", "Quality", "Geannuleerd; eventueel gestarte tests kunnen bestanden hebben gewijzigd."))
        return reporting.build(results, with_tests, completion="cancelled", exit_code=130)
    except (OSError, ValueError, RecursionError):
        results.append(result("FAIL", "Quality", "Studio ontbreekt, is onveilig of de controle overschrijdt een limiet."))
        return reporting.build(results, with_tests, completion="error", exit_code=1)


def run(with_tests=False, output_format="text", output=None):
    return reporting.run(lambda: collect(with_tests), tests_requested=with_tests,
                         output_format=output_format, output=output)
