"""Controleer Studio-ZIP's en herstel uitsluitend naar een nieuwe lokale map."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import time
import unicodedata
import zipfile

import backup
import studio

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_CENTRAL_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
INCOMPLETE = "_CODEX_RESTORE_INCOMPLETE.txt"
EOCD = struct.Struct("<4s4H2LH")


class RestoreError(ValueError):
    """Veilige foutmelding zonder archiefinhoud."""


@dataclass(frozen=True)
class File:
    name: str
    size: int
    digest: str


@dataclass(frozen=True)
class Plan:
    archive: Path
    identity: tuple
    archive_digest: str
    output: Path
    parent_identity: tuple
    files: tuple[File, ...]
    excluded_count: int


def directory_identity(path):
    info = path.lstat()
    return info.st_dev, info.st_ino, info.st_mode


def destination(value: Path):
    output = backup.local_path(value)
    studio.reject_links(output.parent)
    if not output.parent.is_dir():
        raise RestoreError("De bovenliggende doelmap moet al bestaan.")
    output = output.parent.resolve(strict=True) / output.name
    if not backup.archive_name_safe(Path(output.name)):
        raise RestoreError("Kies een veilige Windows-mapnaam voor het doel.")
    if os.path.lexists(output):
        raise RestoreError("De doelmap of het doelbestand bestaat al; kies een nieuwe map.")
    return output


@contextmanager
def source_file(value: Path):
    path = backup.local_path(value)
    studio.reject_links(path)
    path = path.resolve(strict=True)
    info = path.lstat()
    if (path.suffix.casefold() != ".zip" or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1 or info.st_size > MAX_ARCHIVE_BYTES):
        raise RestoreError("Gebruik een gewoon, voltooid ZIP-bestand van maximaal 128 MiB zonder hardlinks.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if backup.stamp(os.fstat(stream.fileno())) != backup.stamp(info):
            raise RestoreError("Archief is vervangen tijdens openen.")
        studio.reject_links(path)
        yield path, stream, backup.stamp(info)
        if (backup.stamp(os.fstat(stream.fileno())) != backup.stamp(info)
                or backup.stamp(path.lstat()) != backup.stamp(info)):
            raise RestoreError("Archief is gewijzigd tijdens de controle.")
        studio.reject_links(path)


def preflight(stream):
    """Begrens de centrale directory vóór ZipFile deze in geheugen laadt."""
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    if size > MAX_ARCHIVE_BYTES:
        raise RestoreError("Archief te groot.")
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    index = tail.rfind(b"PK\x05\x06")
    if index < 0 or index + EOCD.size > len(tail):
        raise RestoreError("ZIP-eindstructuur ontbreekt.")
    signature, disk, start_disk, disk_count, count, central_size, offset, comment = EOCD.unpack_from(tail, index)
    end_offset = size - len(tail) + index
    if (disk or start_disk or disk_count != count or count < 1 or count > backup.MAX_FILES + 1
            or central_size > MAX_CENTRAL_BYTES or count == 65535
            or offset + central_size != end_offset or index + EOCD.size + comment != len(tail)):
        raise RestoreError("Niet-ondersteunde of te grote ZIP-structuur; ZIP64 en meerdelige ZIP's zijn niet toegestaan.")
    if end_offset >= 20:
        stream.seek(end_offset - 20)
        if stream.read(4) == b"PK\x06\x07":
            raise RestoreError("ZIP64-verwijzingen zijn niet toegestaan.")
    stream.seek(offset)
    central = stream.read(central_size)
    position = 0
    for _ in range(count):
        if central[position:position + 4] != b"PK\x01\x02" or position + 46 > len(central):
            raise RestoreError("Ongeldige centrale ZIP-directory.")
        name_size, extra_size, comment_size = struct.unpack_from("<3H", central, position + 28)
        position += 46 + name_size + extra_size + comment_size
        if position > len(central):
            raise RestoreError("Onvolledige centrale ZIP-directory.")
    if position != len(central):
        raise RestoreError("Werkelijk ZIP-aantal wijkt af; archief geweigerd vóór laden.")
    stream.seek(0)
    return count, offset


def safe_name(name: str):
    if (not isinstance(name, str) or not name or name.startswith("/") or "\\" in name
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or not backup.archive_name_safe(Path(name)) or Path(name).as_posix() != name
            or any(unicodedata.category(c).startswith("C") for c in name)):
        raise RestoreError("Onveilig bestandspad in het archief.")
    return unicodedata.normalize("NFC", name).casefold()


def source_policy(name: str):
    """Alleen de broncode-selectie van de huidige Studio-back-ups ondersteunen."""
    path = Path(name)
    if not backup.allowed_file(path) or backup.sensitive(path):
        raise RestoreError("Archief bevat een bestand buiten het broncodeback-upbeleid.")
    for index, part in enumerate(path.parts[:-1]):
        if (part.casefold() in backup.EXCLUDED_DIRS or backup.sensitive(Path(part))
                or (part.startswith(".") and not (index == 0 and part == ".github"))):
            raise RestoreError("Archief bevat een uitgesloten map.")


def read_member(archive, name, size, deadline, *, target=None):
    digest, length = hashlib.sha256(), 0
    with archive.open(name, "r") as source:
        while True:
            backup.deadline_check(deadline)
            block = source.read(backup.CHUNK_SIZE)
            if not block:
                break
            length += len(block)
            if length > size:
                raise RestoreError("Uitgepakte inhoud overschrijdt de verwachte grootte.")
            digest.update(block)
            if target is not None:
                target.write(block)
    if length != size:
        raise RestoreError("Bestandsgrootte klopt niet.")
    return digest.hexdigest()


def archive_hash(stream, deadline):
    stream.seek(0)
    result, size = hashlib.sha256(), 0
    while True:
        backup.deadline_check(deadline)
        block = stream.read(backup.CHUNK_SIZE)
        if not block:
            break
        size += len(block)
        if size > MAX_ARCHIVE_BYTES:
            raise RestoreError("Archief is gegroeid.")
        result.update(block)
    stream.seek(0)
    return result.hexdigest()


def inspect_zip(archive, count, central_offset, deadline):
    infos = archive.infolist()
    if len(infos) != count:
        raise RestoreError("ZIP-aantallen komen niet overeen.")
    names, offsets = set(), set()
    for info in infos:
        backup.deadline_check(deadline)
        key = safe_name(info.filename)
        mode = info.external_attr >> 16
        if (key in names or info.orig_filename != info.filename or info.is_dir()
                or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                or info.external_attr & (0x400 | 0x10) or info.flag_bits & 1
                or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or info.header_offset in offsets or not 0 <= info.header_offset < central_offset
                or not 0 <= info.compress_size <= MAX_ARCHIVE_BYTES):
            raise RestoreError("Dubbele namen, koppelingen, bijzondere of niet-ondersteunde ZIP-items.")
        names.add(key)
        offsets.add(info.header_offset)
        maximum = MAX_MANIFEST_BYTES if info.filename == backup.MANIFEST_NAME else backup.MAX_FILE_BYTES
        if not 0 <= info.file_size <= maximum:
            raise RestoreError("Bestand in archief te groot.")
    # Onafhankelijk van de volgorde in de ZIP.
    for info in infos:
        for parent in Path(info.filename).parents:
            if parent != Path(".") and safe_name(parent.as_posix()) in names:
                raise RestoreError("Conflicterende bestanden en mappen.")
    if backup.MANIFEST_NAME not in archive.namelist():
        raise RestoreError("Studio-back-upmanifest ontbreekt.")
    info = archive.getinfo(backup.MANIFEST_NAME)
    # Begrensd lezen; open/read controleert tevens ZIP-CRC.
    with archive.open(info) as source:
        raw = source.read(MAX_MANIFEST_BYTES + 1)
    backup.deadline_check(deadline)
    if len(raw) != info.file_size or len(raw) > MAX_MANIFEST_BYTES:
        raise RestoreError("Manifest te groot of onvolledig.")
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=studio.unique_keys,
                      parse_constant=studio.reject_json_constant)
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1 or data.get("kind") != "source-backup"
            or type(data.get("excluded_count")) is not int or not 0 <= data["excluded_count"] <= backup.MAX_ENTRIES
            or not isinstance(data.get("files"), dict) or not 0 <= len(data["files"]) <= backup.MAX_FILES):
        raise RestoreError("Ongeldig of onbekend Studio-back-upmanifest.")
    if set(data["files"]) | {backup.MANIFEST_NAME} != set(archive.namelist()) or backup.MANIFEST_NAME in data["files"]:
        raise RestoreError("Manifest en archiefbestanden komen niet exact overeen.")
    files, total = [], 0
    for name, expected in sorted(data["files"].items()):
        safe_name(name)
        source_policy(name)
        if (not isinstance(expected, list) or len(expected) != 2 or type(expected[0]) is not int
                or not 0 <= expected[0] <= backup.MAX_FILE_BYTES or not isinstance(expected[1], str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected[1])):
            raise RestoreError("Ongeldige grootte of SHA-256-controlesom in manifest.")
        size, digest = expected
        total += size
        if total > backup.MAX_TOTAL_BYTES or archive.getinfo(name).file_size != size:
            raise RestoreError("Totale grootte te groot of bestandsgrootte ongelijk.")
        if read_member(archive, name, size, deadline) != digest:
            raise RestoreError("SHA-256-controlesom klopt niet; herstel geweigerd.")
        files.append(File(name, size, digest))
    return tuple(files), data["excluded_count"]


def inspect(value: Path, output: Path, *, deadline=None):
    deadline = time.monotonic() + backup.TIME_LIMIT if deadline is None else deadline
    output = destination(output)
    parent = directory_identity(output.parent)
    with source_file(value) as (path, stream, identity):
        count, offset = preflight(stream)
        digest = archive_hash(stream, deadline)
        with zipfile.ZipFile(stream) as archive:
            files, excluded_count = inspect_zip(archive, count, offset, deadline)
        if archive_hash(stream, deadline) != digest:
            raise RestoreError("Archief gewijzigd tijdens verificatie.")
    return Plan(path, identity, digest, output, parent, files, excluded_count)


def restore(plan: Plan):
    deadline = time.monotonic() + backup.TIME_LIMIT
    if inspect(plan.archive, plan.output, deadline=deadline) != plan:
        raise RestoreError("Archief of doelouder gewijzigd sinds het overzicht; begin opnieuw.")
    with source_file(plan.archive) as (path, stream, identity):
        count, offset = preflight(stream)
        if identity != plan.identity or archive_hash(stream, deadline) != plan.archive_digest:
            raise RestoreError("Archief gewijzigd na bevestiging.")
        with zipfile.ZipFile(stream) as archive:
            # Ook de heropende ZIP volledig valideren vóór de eerste schrijfactie.
            files, excluded = inspect_zip(archive, count, offset, deadline)
            if (files, excluded) != (plan.files, plan.excluded_count):
                raise RestoreError("Archiefselectie gewijzigd.")
            if destination(plan.output) != plan.output or directory_identity(plan.output.parent) != plan.parent_identity:
                raise RestoreError("Doelouder gewijzigd.")
            plan.output.mkdir()  # Bestaande map weigeren, ook bij concurrente aanmaak.
            studio.reject_links(plan.output)
            root_identity = directory_identity(plan.output)
            marker = plan.output / INCOMPLETE
            with marker.open("xb") as target:
                target.write(b"ONVOLLEDIG HERSTEL - gebruik deze map nog niet.\n")
            marker_identity = backup.stamp(marker.lstat())
            for item in files:
                backup.deadline_check(deadline)
                if directory_identity(plan.output) != root_identity:
                    raise RestoreError("Doelmap is vervangen.")
                target = plan.output / item.name
                current = plan.output
                for part in Path(item.name).parts[:-1]:
                    current = current / part
                    if not os.path.lexists(current):
                        current.mkdir()
                    studio.reject_links(current)
                    if not current.is_dir():
                        raise RestoreError("Onveilige doelstructuur.")
                studio.reject_links(target.parent)
                with target.open("xb") as destination_file:
                    digest = read_member(archive, item.name, item.size, deadline, target=destination_file)
                if digest != item.digest:
                    raise RestoreError("Controlesom tijdens schrijven ongelijk.")
            # Werkelijke geschreven bytes opnieuw controleren, zonder code uit te voeren.
            for item in files:
                target = plan.output / item.name
                studio.reject_links(target)
                if not stat.S_ISREG(target.lstat().st_mode) or target.stat().st_nlink != 1:
                    raise RestoreError("Hersteld bestand is vervangen door een koppeling.")
                digest, length = hashlib.sha256(), 0
                with target.open("rb") as content:
                    while True:
                        backup.deadline_check(deadline)
                        block = content.read(backup.CHUNK_SIZE)
                        if not block:
                            break
                        length += len(block)
                        if length > item.size:
                            raise RestoreError("Hersteld bestand is gegroeid.")
                        digest.update(block)
                if (length, digest.hexdigest()) != (item.size, item.digest):
                    raise RestoreError("Verificatie van herstelde bestanden mislukt.")
            if archive_hash(stream, deadline) != plan.archive_digest:
                raise RestoreError("Bronarchief gewijzigd tijdens herstellen.")
        # source_file voert zijn laatste identiteitscontrole uit vóór succes.
    studio.reject_links(plan.output)
    if directory_identity(plan.output) != root_identity or backup.stamp(marker.lstat()) != marker_identity:
        raise RestoreError("Doelmap of herstelmarkering gewijzigd.")
    marker.unlink()  # Alleen eigen markering verwijderen na volledig geverifieerd herstel.
    return plan.output


def run(archive: Path, output: Path, create: bool):
    try:
        plan = inspect(archive, output)
        out = lambda text: studio.print_output(studio.terminal_text(text))
        out("Gecontroleerd archief: " + str(plan.archive))
        out("Nieuwe doelmap: " + str(plan.output))
        for item in plan.files:
            out(f"  PASS SHA-256/CRC: {item.name} ({item.size} bytes)")
        out(f"Totaal: {len(plan.files)} bestanden, {sum(item.size for item in plan.files)} bytes; oorspronkelijke uitsluitingen: {plan.excluded_count}.")
        if not plan.files:
            out("Let op: dit archief bevat geen projectbestanden; herstel zou een lege nieuwe map maken.")
        out("Controlesommen bewijzen geen herkomst. Er wordt geen code uitgevoerd; ontbrekende gegevens/secrets komen niet terug.")
        if not create:
            out("Alleen controle en overzicht; niets aangemaakt. Gebruik --create voor herstel na bevestiging.")
            return 0
        if not sys.stdin.isatty():
            out("Geannuleerd: herstel vereist interactieve bevestiging.")
            return 0
        phrase = "HERSTEL " + plan.output.name
        out("Typ exact '" + phrase + "' om naar deze nieuwe map te herstellen; Enter of nee annuleert.")
        if input("Bevestiging: ") != phrase:
            out("Geannuleerd; niets aangemaakt.")
            return 0
        restore(plan)
        out("Hersteld en geverifieerd: " + str(plan.output))
        return 0
    except (KeyboardInterrupt, EOFError):
        studio.print_output("Herstel geannuleerd. Na de start kan een ONVOLLEDIGE nieuwe map achterblijven; niets automatisch verwijderd.")
        return 130
    except (OSError, ValueError, RecursionError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as error:
        detail = str(error) if isinstance(error, RestoreError) else "Archief, controlesommen of lokale paden zijn ongeldig/onveilig; controleer ook limieten en schrijfrechten."
        studio.print_output("Herstel geweigerd of mislukt: " + studio.terminal_text(detail), file=sys.stderr)
        studio.print_output("Als een nieuwe doelmap is aangemaakt, behandel die als ONVOLLEDIG. Bestaande bestanden worden niet overschreven; niets automatisch verwijderd.", file=sys.stderr)
        return 1
