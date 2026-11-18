"""Alleen-lezen projectoverzicht op basis van .codex-studio.json."""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata

METADATA_FILE = ".codex-studio.json"
MAX_METADATA_BYTES = 64 * 1024
PROJECT_TYPES = {"python", "web", "ai", "automation"}


class UnsafePathError(ValueError):
    """Een koppeling of veranderend pad wordt niet vertrouwd."""


def is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def reject_links(path: Path) -> None:
    for part in (*reversed(path.parents), path):
        if is_link(part.lstat()):
            raise UnsafePathError("Symlinks en junctions zijn niet toegestaan.")


def terminal_text(value: str) -> str:
    """Ook paden kunnen stuurtekens bevatten; druk deze zichtbaar af."""
    return "".join(c if c.isprintable() and not unicodedata.category(c).startswith("C")
                   else ascii(c)[1:-1] for c in value)


def output_text(value: str, stream) -> str:
    """Behoud Unicode waar mogelijk; escape tekens buiten de uitvoercodering."""
    encoding = getattr(stream, "encoding", None)
    if encoding is None:
        return value
    return value.encode(encoding, errors="backslashreplace").decode(encoding)


def print_output(value: str, *, file=None) -> None:
    stream = sys.stdout if file is None else file
    print(output_text(value, stream), file=stream)


@dataclass(frozen=True)
class Project:
    name: str
    kind: str
    studio_version: str | None
    template_version: str | None
    location: Path


def metadata_field(section: object, key: str) -> str:
    if not isinstance(section, dict):
        raise ValueError("Ongeldige metadatastructuur.")
    value = section.get(key)
    if (not isinstance(value, str) or not value.strip() or len(value) > 200
            or any(not c.isprintable() or unicodedata.category(c).startswith("C") for c in value)):
        raise ValueError("Ongeldig of ontbrekend metadataveld.")
    return value


def unique_keys(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Dubbele JSON-velden zijn niet toegestaan.")
        result[key] = value
    return result


def metadata_version(section: object) -> str | None:
    """Expliciet null betekent onbekend; ontbrekende of ongeldige waarden niet."""
    if not isinstance(section, dict) or "version" not in section:
        raise ValueError("Ontbrekende versie-informatie.")
    value = section["version"]
    if value is None:
        return None
    value = metadata_field(section, "version")
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value):
        raise ValueError("Ongeldig versienummer.")
    return value


def read_project(directory: Path) -> Project | None:
    """Open uitsluitend de begrensde metadata, nooit broncode of configuratie."""
    path = directory / METADATA_FILE
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    reject_links(path)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_METADATA_BYTES:
        raise ValueError("Metadata moet een gewoon bestand van maximaal 64 KiB zijn.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise UnsafePathError("Metadata is tijdens het lezen vervangen.")
        reject_links(path)
        raw = stream.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError("Metadata is te groot.")
    reject_links(path)
    # Windows PowerShell 5.1 kan UTF-8 met BOM schrijven. Verwijder alleen een
    # eventuele begin-BOM; alle overige JSON- en inhoudscontroles blijven gelden.
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys)
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("Niet-ondersteunde metadataversie; verwacht schema_version 1.")
    name = metadata_field(data.get("project"), "name")
    kind = metadata_field(data.get("template"), "id")
    studio_version = metadata_version(data.get("generator"))
    template_version = metadata_version(data.get("template"))
    if kind not in PROJECT_TYPES:
        raise ValueError("Onbekend projecttype.")
    return Project(name, kind, studio_version, template_version, directory)


def list_projects(root: Path) -> tuple[list[Project], list[str]]:
    """Scan alleen directe mappen. Waarschuwingen bevatten nooit metadata-inhoud."""
    root = Path(os.path.abspath(root.expanduser()))
    reject_links(root)
    if not root.is_dir():
        raise NotADirectoryError("De projectroot moet een bestaande map zijn.")
    projects, warnings = [], []
    for directory in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
        try:
            info = directory.lstat()
            if is_link(info):
                raise UnsafePathError("Koppeling overgeslagen.")
            if not stat.S_ISDIR(info.st_mode):
                continue
            reject_links(directory)
            project = read_project(directory)
            if project is not None:
                projects.append(project)
        except (OSError, ValueError, RecursionError) as error:
            warnings.append(f"Overgeslagen: {terminal_text(directory.name)} ({type(error).__name__}).")
    return sorted(projects, key=lambda p: (p.name.casefold(), str(p.location))), warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bekijk studio-projecten zonder ze te wijzigen.")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="Toon projecten met .codex-studio.json")
    listing.add_argument("--root", type=Path, default=None, help="Projectroot (standaard: ~/Projects)")
    args = parser.parse_args(argv)
    root = Path.home() / "Projects" if args.root is None else args.root
    try:
        projects, warnings = list_projects(root)
    except (OSError, ValueError):
        print_output("Fout: projectroot ontbreekt, is onleesbaar of bevat een onveilige koppeling.", file=sys.stderr)
        return 1
    for warning in warnings:
        print_output(f"Waarschuwing: {warning}", file=sys.stderr)
    if not projects:
        print_output("Geen projecten met geldige .codex-studio.json gevonden.")
    else:
        rows = [("NAAM", "TYPE", "STUDIO", "TEMPLATE", "LOCATIE")]
        rows.extend((p.name, p.kind, p.studio_version or "onbekend", p.template_version or "onbekend",
                     terminal_text(str(p.location))) for p in projects)
        # Bereken kolombreedtes na escapen, ook bij omgeleide CP1252-uitvoer.
        rows = [tuple(output_text(cell, sys.stdout) for cell in row) for row in rows]
        widths = [max(len(row[i]) for row in rows) for i in range(4)]
        for row in rows:
            print_output("  ".join(row[i].ljust(widths[i]) for i in range(4)) + "  " + row[4])
    # Een gedeeltelijk overzicht mag niet stilzwijgend als volledig gelden.
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
