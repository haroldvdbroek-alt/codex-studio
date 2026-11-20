"""Eén rapportmodel met veilige tekst-, JSON-, Markdown- en bestandsuitvoer."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import stat
import sys

import backup
import studio

STATUSES = ("PASS", "WARN", "FAIL", "SKIP")
FORMATS = {"text": ".txt", "json": ".json", "markdown": ".md"}
MAX_REPORT_BYTES = 4 * 1024 * 1024
PROTECTED = {".git", ".aws", ".ssh", ".codex", ".agents", ".venv", "node_modules", "__pycache__"}


@dataclass(frozen=True)
class ManualCheck:
    id: str
    label: str
    message: str


@dataclass(frozen=True)
class ReleaseInfo:
    version: str | None
    commit: str | None
    local_ready: bool
    state: str
    manual_checks: tuple[ManualCheck, ...]

    def as_dict(self):
        return {"version": self.version, "commit": self.commit, "local_ready": self.local_ready,
                "state": self.state, "published": False,
                "manual_checks": [{"id": item.id, "status": "HANDMATIG_TE_VERIFIEREN",
                                   "label": studio.terminal_text(item.label),
                                   "message": studio.terminal_text(item.message)} for item in self.manual_checks]}


@dataclass(frozen=True)
class Report:
    results: tuple
    tests_requested: bool
    completion: str
    exit_code: int
    command: str = "quality"
    release: ReleaseInfo | None = None

    @property
    def summary(self):
        return {status: sum(item.status == status for item in self.results) for status in STATUSES}

    def as_dict(self):
        data = {"schema_version": 1, "command": self.command, "completion": self.completion,
                "tests_requested": self.tests_requested, "exit_code": self.exit_code,
                "summary": self.summary,
                "results": [{"status": item.status, "label": item.label, "message": item.message}
                            for item in self.results]}
        if self.release is not None:
            data["release"] = self.release.as_dict()
        return data


def build(results, tests_requested=False, *, completion="complete", exit_code=None, command="quality", release=None):
    if completion not in {"complete", "error", "cancelled"}:
        raise ValueError("Ongeldige rapportstatus.")
    items = []
    for item in results:
        if item.status not in STATUSES:
            raise ValueError("Ongeldige controlestatus.")
        items.append(studio.CheckResult(item.status, studio.terminal_text(item.label),
                                       studio.terminal_text(item.message)))
    code = int(any(item.status == "FAIL" for item in items)) if exit_code is None else exit_code
    if code not in {0, 1, 3, 4, 130} or command not in {"quality", "release-check"}:
        raise ValueError("Ongeldige rapport-exitcode.")
    return Report(tuple(items), bool(tests_requested), completion, code, command, release)


def markdown_cell(value):
    # Entiteiten voorkomen HTML, links, tabelkolommen en Markdown-opmaak.
    return "".join(c if 32 <= ord(c) < 127 and c not in "\\|`*_[]<>!&#"
                   else f"&#{ord(c)};" for c in str(value))


def render(report, output_format):
    if output_format == "json":
        return (json.dumps(report.as_dict(), ensure_ascii=True, allow_nan=False, indent=2)
                .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") + "\n")
    counts = ", ".join(f"{count} {status}" for status, count in report.summary.items())
    metadata = (f"Status: {report.completion}; exitcode: {report.exit_code}; "
                f"tests gevraagd: {'ja' if report.tests_requested else 'nee'}.")
    if output_format == "text":
        lines = [*(f"{item.status} {item.label}: {item.message}" for item in report.results),
                 "Samenvatting: " + counts, metadata]
        if report.release is not None:
            info = report.release.as_dict()
            lines.extend(["Release-status: " + info["state"], "Kandidaatversie: " + (info["version"] or "onbekend"),
                          "Lokale commit: " + (info["commit"] or "onbekend"),
                          "NIET GEPUBLICEERD. Geen externe controle of publicatiegoedkeuring afgegeven."])
            lines.extend(f"{item['status']} {item['label']}: {item['message']}" for item in info["manual_checks"])
        return "\n".join(lines) + "\n"
    if output_format == "markdown":
        title = "Qualityrapport" if report.command == "quality" else "Lokale releasecontrole"
        lines = ["# " + title, "", "Schema: 1; opdracht: " + report.command + ".", "", metadata, "",
                 "Samenvatting: " + counts, "", "| Status | Controle | Resultaat |", "| --- | --- | --- |"]
        lines.extend("| " + " | ".join(markdown_cell(value) for value in
                     (item.status, item.label, item.message)) + " |" for item in report.results)
        if report.release is not None:
            info = report.release.as_dict()
            lines.extend(["", "## Handmatige vrijgave staat nog open", "",
                          "Release-status: " + markdown_cell(info["state"]), "",
                          "Kandidaatversie: " + markdown_cell(info["version"] or "onbekend"), "",
                          "Lokale commit: " + markdown_cell(info["commit"] or "onbekend"), "",
                          "NIET GEPUBLICEERD. Geen externe controle of publicatiegoedkeuring afgegeven.", "",
                          "| Status | Externe controle | Zelf verifiëren |", "| --- | --- | --- |"])
            lines.extend("| " + " | ".join(markdown_cell(value) for value in
                         (item["status"], item["label"], item["message"])) + " |" for item in info["manual_checks"])
        return "\n".join(lines) + "\n"
    raise ValueError("Onbekend rapportformaat.")


def encoded(report, output_format):
    payload = render(report, output_format).encode("utf-8")
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Rapport te groot.")
    return payload


@dataclass(frozen=True)
class Destination:
    path: Path
    parent_identity: tuple


def parent_identity(path):
    info = path.lstat()
    return info.st_dev, info.st_ino, info.st_mode


def prepare_destination(value, output_format):
    path = backup.local_path(Path(value))
    if (path.suffix.casefold() != FORMATS[output_format]
            or not backup.archive_name_safe(Path(path.name))):
        raise ValueError("Rapportnaam of extensie ongeldig.")
    studio.reject_links(path.parent)
    if not path.parent.is_dir():
        raise ValueError("Rapportouder ontbreekt.")
    path = path.parent.resolve(strict=True) / path.name
    if any(part.casefold() in PROTECTED for part in path.parts[:-1]):
        raise ValueError("Rapport in beschermde administratie geweigerd.")
    if os.path.lexists(path):
        raise FileExistsError("Rapportdoel bestaat al.")
    return Destination(path, parent_identity(path.parent))


def save(destination, payload, output_format):
    """Publiceer uitsluitend een volledig nieuw bestand; nooit een overwrite-fallback."""
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Rapport te groot.")
    if prepare_destination(destination.path, output_format) != destination:
        raise ValueError("Rapportouder veranderd.")
    temporary = destination.path.parent / (".quality-report-" + secrets.token_hex(12) + ".incomplete")
    descriptor = os.open(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        identity = os.fstat(stream.fileno())
        if stream.write(payload) != len(payload):
            raise OSError("Onvolledig rapport geschreven.")
        stream.flush()
        os.fsync(stream.fileno())
        studio.reject_links(temporary)
        if (temporary.stat().st_dev, temporary.stat().st_ino) != (identity.st_dev, identity.st_ino):
            raise ValueError("Tijdelijk rapport vervangen.")
    if prepare_destination(destination.path, output_format) != destination:
        raise ValueError("Rapportouder veranderd tijdens schrijven.")
    studio.reject_links(temporary)
    info = temporary.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or (info.st_dev, info.st_ino) != (identity.st_dev, identity.st_ino)):
        raise ValueError("Tijdelijk rapport veranderd.")
    if os.name == "nt":
        os.rename(temporary, destination.path)  # Windows weigert een bestaand doel.
    else:
        os.link(temporary, destination.path, follow_symlinks=False)  # Ook POSIX: geen overwrite.
        try:
            temporary.unlink()
        except OSError:
            # Het eindrapport is al volledig gepubliceerd; geen foutieve exitcode
            # in een geldig rapport veroorzaken door alleen een opruimprobleem.
            studio.print_output("Waarschuwing: rapport opgeslagen; eigen tijdelijk rapportbestand bleef achter.", file=sys.stderr)


def run(collector, *, tests_requested=False, output_format="text", output=None, command="quality", release=None):
    """Gedeelde veilige aflevering; alleen de collector bepaalt de controle-inhoud."""
    destination = None
    try:
        if output_format not in FORMATS:
            raise ValueError("Ongeldig formaat.")
        if output is not None:
            destination = prepare_destination(output, output_format)
    except (OSError, ValueError, RuntimeError):
        report = build([studio.CheckResult("FAIL", "Rapportbestand", "Rapportdoel ongeldig, bestaand of onveilig; kies een nieuwe lokale bestandsnaam met passende extensie en bestaande oudermap.")],
                       tests_requested, command=command, release=release, completion="error", exit_code=3)
    else:
        report = collector()
    def changed(items, completion, code):
        return build(items, tests_requested, command=report.command, release=report.release,
                     completion=completion, exit_code=code)
    try:
        payload = encoded(report, output_format)
    except (ValueError, RecursionError):
        report = changed([studio.CheckResult("FAIL", "Rapport", "Rapport overschrijdt een limiet of kon niet veilig worden opgebouwd; geen volledig rapport opgeslagen.")], "error", 3)
        destination = None
        payload = render(report, output_format if output_format in FORMATS else "text").encode("utf-8")
    if destination is not None and report.exit_code != 130:
        try:
            save(destination, payload, output_format)
            studio.print_output("Rapport opgeslagen: " + studio.terminal_text(str(destination.path)), file=sys.stderr)
        except KeyboardInterrupt:
            report = changed([*report.results, studio.CheckResult("SKIP", "Rapportbestand", "Opslaan onderbroken; eventueel tijdelijk .incomplete-bestand blijft achter.")], "cancelled", 130)
            payload = render(report, output_format).encode("utf-8")
        except (OSError, ValueError, RuntimeError):
            report = changed([*report.results, studio.CheckResult("FAIL", "Rapportbestand", "Rapport niet veilig opgeslagen; geen bestaand bestand overschreven. Eventueel eigen .incomplete-bestand blijft achter.")], "error", 3)
            payload = render(report, output_format).encode("utf-8")
    elif destination is not None:
        studio.print_output("Geen rapportbestand aangemaakt wegens annuleren.", file=sys.stderr)
    try:
        studio.print_output(payload.decode("utf-8").rstrip("\n"))
    except (OSError, ValueError):
        studio.print_output("Rapport kon niet naar stdout worden geschreven.", file=sys.stderr)
        return 3
    return report.exit_code
