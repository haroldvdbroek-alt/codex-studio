"""Lokale releasevoorcontrole, zonder publiceren of externe goedkeuring te claimen."""

from pathlib import Path
import os
import re
import subprocess

import backup
import quality
import reporting
import studio

MANUAL_CHECKS = (
    reporting.ManualCheck("actions", "GitHub Actions", "Controleer in GitHub de vereiste workflows voor exact de gerapporteerde commit; lokale tests bewijzen geen geslaagde Actions-run."),
    reporting.ManualCheck("review", "Pull request en reviews", "Controleer de juiste repository, doelbranch, actuele PR en vereiste onafhankelijke goedkeuringen."),
    reporting.ManualCheck("protection", "Branchbescherming", "Verifieer de ingestelde branchregels en verplichte statuschecks in GitHub; lokale Git-configuratie bewijst die niet."),
    reporting.ManualCheck("security", "Secrets en afhankelijkheden", "Beoordeel relevante externe secret-/dependency-scans en meldingen; de lokale controle is geen security-audit."),
    reporting.ManualCheck("compatibility", "Platforms en herstelproef", "Beoordeel overgeslagen tests, ondersteunde Windows/Python-versies, browsergedrag en een passende back-up/herstelproef; vul hiaten handmatig aan."),
    reporting.ManualCheck("publication", "Versie, artefacten en publicatietoestemming", "Vergelijk release-notities, kandidaatversie en definitieve artefacten; controleer externe tags/releases en geef apart toestemming voor iedere publicatiestap."),
)


def version_value(value):
    if value is None:
        return None
    try:
        studio.parse_semver(value)
    except ValueError:
        return None
    return value


def info(version=None, commit=None, ready=False, state="LOCAL_INCOMPLETE"):
    return reporting.ReleaseInfo(version, commit, ready, state, MANUAL_CHECKS)


def changelog_check(root, version):
    if version is None:
        return quality.result("SKIP", "Changelog-versie", "Geen geldige kandidaatversie opgegeven; geen releasegeschiedenis verzonnen.")
    try:
        text = studio.read_bytes_file(root / "CHANGELOG.md").decode("utf-8-sig")
        match = re.compile(r"## \[" + re.escape(version) + r"\](?: - [0-9]{4}-[0-9]{2}-[0-9]{2})?")
        body, found, fence = [], False, None
        for line in text.splitlines():
            clean = line.strip()
            if clean.startswith(("```", "~~~")):
                token = clean[:3]
                if fence is None:
                    fence = token
                elif token == fence:
                    fence = None
                continue
            if fence is not None:
                continue
            if clean.startswith("## "):
                if found:
                    break
                found = bool(match.fullmatch(clean))
                continue
            if found:
                body.append(clean)
        notes = "\n".join(body).strip()
        if not found or not notes or notes.casefold() in {"todo", "tbd", "...", "…", "nog invullen"}:
            raise ValueError("Release-notities ontbreken.")
        return quality.result("PASS", "Changelog-versie", "Exacte kandidaatversie heeft een lokale changelogsectie met notities; inhoud nog handmatig beoordelen.")
    except (OSError, ValueError, RecursionError):
        return quality.result("FAIL", "Changelog-versie", "CHANGELOG.md ontbreekt, is onveilig/ongeldig of mist een ingevulde sectie ## [MAJOR.MINOR.PATCH] voor deze kandidaat.")


def read_commit(root):
    executable = studio.trusted_executable("git", root.parent)
    if not executable:
        raise ValueError("Geen vertrouwde Git.")
    command = [executable, "--no-optional-locks", "-c", "core.fsmonitor=false",
               "-c", "core.hooksPath=" + os.devnull, "-C", str(root), "rev-parse", "--verify", "HEAD"]
    completed = studio.run_bounded(command, cwd=root, env=studio.child_environment(), shell=False,
                                  capture_output=True, timeout=studio.GIT_TIMEOUT)
    commit = completed.stdout.decode("ascii").strip()
    if completed.returncode or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit):
        raise ValueError("Geen geldige lokale HEAD.")
    return commit


def collect(version=None, with_tests=False):
    results, commit = [], None
    candidate = version_value(version)
    try:
        root = backup.local_path(quality.STUDIO_ROOT)
        studio.reject_links(root)
        root = root.resolve(strict=True)
        results = quality.static_checks()
        if version is None:
            results.append(quality.result("WARN", "Kandidaatversie", "Niet opgegeven; kies bewust --version MAJOR.MINOR.PATCH. Template- of administratieve versies worden niet als studiorelease geraden."))
        elif candidate is None:
            results.append(quality.result("FAIL", "Kandidaatversie", "Ongeldige versie; gebruik MAJOR.MINOR.PATCH zonder voorloopnullen of suffixen."))
        else:
            results.append(quality.result("PASS", "Kandidaatversie", "Geldige expliciete kandidaatversie; dit maakt of reserveert geen versie of tag."))
        results.append(changelog_check(root, candidate))
        git = next((item for item in results if item.label == "Git"), None)
        if git is None or git.status != "PASS":
            results.append(quality.result("FAIL", "Releasewerkmap", "Een schone, eigen en veilig leesbare Git-repository is vereist. Geen commit gemaakt en geen wijzigingen weggegooid."))
        else:
            try:
                commit = read_commit(root)
                results.append(quality.result("PASS", "Releasecommit", "Lokale HEAD vastgesteld voor handmatige vergelijking met GitHub; geen remote geraadpleegd."))
            except (OSError, ValueError, subprocess.SubprocessError):
                results.append(quality.result("FAIL", "Releasecommit", "Lokale commit kon niet veilig worden vastgesteld; lege, ongeldige of onleesbare repository."))
        if not with_tests:
            tests = quality.result("SKIP", "Tests", "Niet uitgevoerd. Bestaande rapporten worden niet als actueel testbewijs overgenomen; kies zo nodig --run-tests en bevestig.")
        elif candidate is None or any(item.status == "FAIL" for item in results):
            tests = quality.result("SKIP", "Tests", "Geen tests gestart: kandidaatversie ontbreekt of lokale controles blokkeren de kandidaat.")
        else:
            tests = quality.run_tests()
        results.append(tests)
        if tests.status == "PASS":
            after = quality.static_checks()
            results.extend(quality.result("FAIL", "Na tests: " + item.label, item.message)
                           for item in after if item.status == "FAIL")
            after_git = next((item for item in after if item.label == "Git"), None)
            if after_git is None or after_git.status != "PASS":
                results.append(quality.result("FAIL", "Releasewerkmap na tests", "Werkmap is na tests niet aantoonbaar schoon; nieuw overzicht nodig."))
            elif read_commit(root) != commit:
                results.append(quality.result("FAIL", "Releasecommit na tests", "HEAD is gewijzigd tijdens de controle; nieuw overzicht nodig."))
        failed = any(item.status == "FAIL" for item in results)
        ready = not failed and candidate is not None and commit is not None and tests.status == "PASS"
        state = "BLOCKED" if failed else "MANUAL_REQUIRED" if ready else "LOCAL_INCOMPLETE"
        return reporting.build(results, with_tests, command="release-check", release=info(candidate, commit, ready, state),
                               exit_code=1 if failed else 4)
    except KeyboardInterrupt:
        results.append(quality.result("SKIP", "Releasecontrole", "Geannuleerd; eventueel gestarte tests kunnen bestanden hebben gewijzigd. Er is niets gepubliceerd."))
        return reporting.build(results, with_tests, command="release-check", release=info(candidate, commit),
                               completion="cancelled", exit_code=130)
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError):
        results.append(quality.result("FAIL", "Releasecontrole", "Lokale controle kon niet veilig worden afgerond; geen publicatie of externe verificatie uitgevoerd."))
        return reporting.build(results, with_tests, command="release-check", release=info(candidate, commit, state="BLOCKED"),
                               completion="error", exit_code=1)


def run(version=None, with_tests=False, output_format="text", output=None):
    return reporting.run(lambda: collect(version, with_tests), tests_requested=with_tests,
                         output_format=output_format, output=output, command="release-check",
                         release=info(version_value(version)))
