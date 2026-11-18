"""Begrensde lokale broncodeback-up; nooit schrijven tijdens het overzicht."""

import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import time
import zipfile

import studio

MAX_ENTRIES = 3000
MAX_FILES = 1000
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
TIME_LIMIT = 60
CHUNK_SIZE = 64 * 1024
MANIFEST_NAME = "_CODEX_BACKUP.json"
SOURCE_DIRS = {"src", "tests", "public", "docs", "dashboard"}
SOURCE_SUFFIXES = {".py", ".html", ".css", ".js", ".mjs", ".cjs", ".md", ".rst"}
ROOT_FILES = {"pyproject.toml", "package.json", "requirements.txt", "license", "copying",
              ".gitignore", ".gitattributes", ".codex-studio.json"}
EXCLUDED_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", ".cache",
                 ".aws", ".ssh", ".codex", ".agents", ".vscode", ".idea", "data", "gegevens",
                 "personal", "persoonlijk", "private", "uploads", "downloads", "documents",
                 "logs", "log", "backups", "backup", "output", "outputs", "dist", "build"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".crt", ".cer", ".pfx", ".p12", ".der", ".db",
                      ".sqlite", ".sqlite3", ".csv", ".xlsx", ".xls", ".log", ".zip",
                      ".7z", ".tar", ".gz", ".bak", ".incomplete"}


def deadline_check(deadline: float):
    if time.monotonic() > deadline:
        raise ValueError("Tijdslimiet overschreden.")


def local_path(value: Path) -> Path:
    """Geen UNC/devicepaden, drive-relative paden, ADS of remote schijven."""
    text = str(value.expanduser())
    if text.startswith(("\\\\", "//")) or "\x00" in text:
        raise ValueError("Gebruik een rechtstreeks lokaal schijfpad.")
    expanded = Path(text)
    if os.name == "nt" and (":" in text[len(expanded.drive):] or
                             (expanded.drive and not expanded.is_absolute())):
        raise ValueError("Gebruik een volledig lokaal pad zonder datastroom.")
    path = Path(os.path.abspath(text))
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
        api.GetDriveTypeW.restype = ctypes.c_uint
        if api.GetDriveTypeW(path.anchor) not in (2, 3, 6):
            raise ValueError("Geen lokale schijf.")
    return path


def stamp(info) -> tuple:
    # Windows/Python kan ctime bij lstat en fstat verschillend invullen.
    # Identiteit, grootte en mtime blijven op beide platforms verplicht gelijk.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns if os.name != "nt" else 0, info.st_nlink)


@dataclass(frozen=True)
class File:
    name: str
    size: int
    identity: tuple


@dataclass(frozen=True)
class Plan:
    root: Path
    source: Path
    output: Path
    archive: Path
    files: tuple[File, ...]
    excluded: tuple[tuple[str, str], ...]

    @property
    def total(self):
        return sum(item.size for item in self.files)


def sensitive(path: Path) -> bool:
    name = path.name.casefold()
    return (name.startswith(".env") or path.suffix.casefold() in SENSITIVE_SUFFIXES
            or name.startswith(("id_rsa", "id_ed25519", "id_ecdsa"))
            or any(word in name for word in ("secret", "credential", "password", "passwd",
                                             "token", "api_key", "apikey", "private")))


def allowed_file(relative: Path) -> bool:
    parts = relative.parts
    if len(parts) == 1:
        return relative.name.casefold() in ROOT_FILES or relative.suffix.casefold() in SOURCE_SUFFIXES
    if parts[0].casefold() == ".github":
        return (len(parts) == 3 and parts[1].casefold() == "workflows"
                and relative.suffix.casefold() in {".yml", ".yaml"})
    return parts[0].casefold() in SOURCE_DIRS and relative.suffix.casefold() in SOURCE_SUFFIXES


def archive_name_safe(relative: Path) -> bool:
    reserved = {"con", "prn", "aux", "nul", "clock$", "conin$", "conout$"}
    reserved |= {p + n for p in ("com", "lpt") for n in (*map(str, range(1, 10)), "¹", "²", "³")}
    return (len(relative.as_posix()) <= 300 and len(relative.parts) <= 25
            and all(part not in {".", ".."} and not part.endswith((".", " "))
                    and part.split(".")[0].casefold() not in reserved
                    and not any(c in '<>:"\\|?*' or not c.isprintable() for c in part)
                    for part in relative.parts))


def make_plan(root: Path, name: str, output: Path, *, archive_name=None, deadline=None) -> Plan:
    deadline = time.monotonic() + TIME_LIMIT if deadline is None else deadline
    root = local_path(root)
    studio.reject_links(root)
    root = root.resolve(strict=True)
    source = studio.check_path(root, name)
    if studio.read_project(source) is None:
        raise ValueError("Project heeft geen geldige .codex-studio.json.")
    output = local_path(output)
    # Eén nieuwe bestemmingsmap mag na bevestiging ontstaan; de ouder moet bestaan.
    studio.reject_links(output.parent)
    if not output.parent.is_dir():
        raise ValueError("Bovenliggende bestemmingsmap ontbreekt.")
    if os.path.lexists(output):
        studio.reject_links(output)
        if not output.is_dir():
            raise ValueError("Bestemming is geen map.")
        output = output.resolve(strict=True)
    else:
        output = output.parent.resolve(strict=True) / output.name
    # Vergelijk canonieke paden, ook bij Windows 8.3-aliasnamen.
    if output.is_relative_to(source.resolve(strict=True)):
        raise ValueError("Back-upbestemming mag niet in het project liggen.")
    if archive_name is None:
        date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_name = f"{name}-{date}-{secrets.token_hex(4)}.zip"
    if (Path(archive_name).name != archive_name or not archive_name.endswith(".zip")
            or not archive_name_safe(Path(archive_name))):
        raise ValueError("Ongeldige archiefnaam.")
    archive = output / archive_name
    for target in (archive, Path(str(archive) + ".incomplete")):
        if os.path.lexists(target):
            raise FileExistsError("Archief of onvolledig archief bestaat al.")
    files, excluded, pending, seen = [], [], [source], set()
    count, total = 0, 0
    while pending:
        current = pending.pop()
        studio.reject_links(current)
        with os.scandir(current) as entries:
            for entry in entries:
                deadline_check(deadline)
                count += 1
                if count > MAX_ENTRIES:
                    raise ValueError("Te veel projectitems; geen volledige veilige selectie mogelijk.")
                path = Path(entry.path)
                relative = path.relative_to(source)
                name_in_zip = relative.as_posix()
                # DirEntry.stat kan op Windows 0 voor inode/nlink teruggeven.
                # lstat levert de identiteit die ook bij het openen wordt vergeleken.
                info = path.lstat()
                reason = None
                if studio.is_link(info):
                    reason = "symlink of junction"
                elif not archive_name_safe(relative):
                    reason = "onveilige of te lange naam"
                elif sensitive(path):
                    reason = "mogelijk gevoelig bestand of archief"
                elif stat.S_ISDIR(info.st_mode):
                    first = relative.parts[0].casefold()
                    if (entry.name.casefold() in EXCLUDED_DIRS
                            or (entry.name.startswith(".") and name_in_zip != ".github")
                            or (first not in SOURCE_DIRS | {".github"})
                            or (first == ".github" and len(relative.parts) > 1
                                and name_in_zip.casefold() != ".github/workflows")):
                        reason = "gegevens, tijdelijke of niet-toegestane map (inhoud niet bekeken)"
                    else:
                        pending.append(path)
                        continue
                elif not stat.S_ISREG(info.st_mode):
                    reason = "geen gewoon bestand"
                elif info.st_nlink != 1:
                    reason = "hardlink"
                elif not allowed_file(relative):
                    reason = "niet op de lijst met broncode/documentatie/configuratie"
                if reason:
                    excluded.append((name_in_zip, reason))
                    continue
                if info.st_size > MAX_FILE_BYTES:
                    raise ValueError("Toegestaan bestand te groot; geen stilzwijgende gedeeltelijke back-up.")
                key = name_in_zip.casefold()
                if key in seen:
                    raise ValueError("Conflicterende archiefnamen.")
                seen.add(key)
                total += info.st_size
                if len(files) >= MAX_FILES or total > MAX_TOTAL_BYTES:
                    raise ValueError("Bestands- of groottelimiet bereikt.")
                files.append(File(name_in_zip, info.st_size, stamp(info)))
    return Plan(root, source, output, archive, tuple(sorted(files, key=lambda f: f.name)),
                tuple(sorted(excluded)))


def same_plan(plan: Plan, deadline):
    current = make_plan(plan.root, plan.source.name, plan.output, archive_name=plan.archive.name,
                        deadline=deadline)
    if current != plan:
        raise ValueError("Project/selectie is gewijzigd sinds het overzicht; begin opnieuw.")


def open_source(plan: Plan, item: File):
    path = plan.source / item.name
    studio.reject_links(path)
    if stamp(path.lstat()) != item.identity:
        raise ValueError("Bronbestand gewijzigd.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    stream = os.fdopen(os.open(path, flags), "rb")
    try:
        if stamp(os.fstat(stream.fileno())) != item.identity:
            raise ValueError("Bronbestand vervangen.")
        studio.reject_links(path)
    except BaseException:
        stream.close()
        raise
    return stream


def verify(stream, expected: dict[str, tuple[int, str]], deadline):
    stream.seek(0)
    with zipfile.ZipFile(stream, "r") as archive:
        if set(archive.namelist()) != set(expected):
            raise ValueError("Archiefinhoud wijkt af.")
        for name, (size, digest) in expected.items():
            result, length = hashlib.sha256(), 0
            with archive.open(name) as source:
                while True:
                    deadline_check(deadline)
                    block = source.read(CHUNK_SIZE)
                    if not block:
                        break
                    length += len(block)
                    if length > size:
                        raise ValueError("Archiefbestand te groot.")
                    result.update(block)
            if (length, result.hexdigest()) != (size, digest):
                raise ValueError("Archiefverificatie mislukt.")


def create_archive(plan: Plan) -> Path:
    """Alleen aanroepen na toestemming. Exclusief aanmaken; fouten blijven zichtbaar."""
    deadline = time.monotonic() + TIME_LIMIT
    same_plan(plan, deadline)
    if not os.path.lexists(plan.output):
        plan.output.mkdir()  # Geen ouders en geen exist_ok: concurrente aanmaak weigeren.
    studio.reject_links(plan.output)
    incomplete = Path(str(plan.archive) + ".incomplete")
    expected = {}
    # Exclusieve open weigert ook bestanden en kapotte symlinks op de doelnaam.
    with incomplete.open("x+b") as destination:
        identity = os.fstat(destination.fileno())
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for item in plan.files:
                digest, length = hashlib.sha256(), 0
                with open_source(plan, item) as source, archive.open(item.name, "w") as target:
                    while True:
                        deadline_check(deadline)
                        block = source.read(CHUNK_SIZE)
                        if not block:
                            break
                        length += len(block)
                        if length > item.size:
                            raise ValueError("Bronbestand is gegroeid.")
                        digest.update(block)
                        target.write(block)
                    if length != item.size or stamp(os.fstat(source.fileno())) != item.identity:
                        raise ValueError("Bronbestand gewijzigd tijdens kopiëren.")
                studio.reject_links(plan.source / item.name)
                expected[item.name] = (length, digest.hexdigest())
            content = json.dumps({"schema_version": 1, "kind": "source-backup",
                                  "files": expected, "excluded_count": len(plan.excluded),
                                  "note": "Geen volledige data-, secrets- of Git-back-up; niet versleuteld."},
                                 ensure_ascii=True, indent=2).encode("ascii")
            archive.writestr(MANIFEST_NAME, content)
            expected[MANIFEST_NAME] = (len(content), hashlib.sha256(content).hexdigest())
        destination.flush()
        os.fsync(destination.fileno())
        verify(destination, expected, deadline)
        # Nogmaals scannen vóór publiceren. De tijdelijke doelnaam bestaat nu bewust.
        current = make_plan(plan.root, plan.source.name, plan.output,
                            archive_name="validation-" + secrets.token_hex(8) + ".zip", deadline=deadline)
        if (current.source, current.files, current.excluded) != (plan.source, plan.files, plan.excluded):
            raise ValueError("Project gewijzigd tijdens back-up.")
        deadline_check(deadline)
        studio.reject_links(incomplete)
        if (incomplete.stat().st_dev, incomplete.stat().st_ino) != (identity.st_dev, identity.st_ino):
            raise ValueError("Tijdelijk archief vervangen.")
    studio.reject_links(plan.output)
    # link() publiceert zonder een bestaand doel te vervangen, ook op POSIX.
    # Geen onveilige rename-fallback: FAT/exFAT zonder hardlinks geeft een fout.
    os.link(incomplete, plan.archive, follow_symlinks=False)
    if not os.path.samefile(incomplete, plan.archive):
        raise ValueError("Archiefpublicatie mislukt.")
    incomplete.unlink()  # Uitsluitend het eigen geverifieerde tijdelijke archief.
    return plan.archive


def print_plan(plan: Plan):
    out = lambda value: studio.print_output(studio.terminal_text(value))
    out("Bron: " + str(plan.source))
    out("Voorgesteld ZIP-archief: " + str(plan.archive))
    out("OPNEMEN:")
    for item in plan.files:
        out(f"  {item.name} ({item.size} bytes)")
    out("UITSLUITEN:")
    for name, reason in plan.excluded:
        out(f"  {name}: {reason}")
    out(f"Totaal: {len(plan.files)} bestanden, {plan.total} bytes ongecomprimeerd; {len(plan.excluded)} uitgesloten items/mappen.")
    out("Let op: namen herkennen niet alle secrets. Controleer de selectie. Dit ZIP-bestand is niet versleuteld.")


def run(root: Path, name: str, output: Path | None, create: bool) -> int:
    plan = None
    try:
        plan = make_plan(root, name, Path.home() / "StudioBackups" if output is None else output)
        print_plan(plan)
        if not create:
            studio.print_output("Alleen overzicht; niets aangemaakt. Gebruik --create om na een nieuw overzicht toestemming te geven.")
            return 0
        if not sys.stdin.isatty():
            studio.print_output("Geannuleerd: aanmaken vereist een interactieve bevestiging.")
            return 0
        phrase = "BACKUP " + name
        studio.print_output("Typ exact '" + phrase + "' om alleen deze selectie op deze bestemming te bewaren; Enter of nee annuleert.")
        if input("Bevestiging: ") != phrase:
            studio.print_output("Geannuleerd; niets aangemaakt.")
            return 0
        archive = create_archive(plan)
        studio.print_output("Back-up gemaakt en geverifieerd: " + studio.terminal_text(str(archive)))
        return 0
    except (KeyboardInterrupt, EOFError):
        studio.print_output("Geannuleerd. Zonder bevestiging is niets aangemaakt; na de start kan een onvolledig archief bestaan.")
        return 130
    except (OSError, ValueError, RecursionError, zipfile.BadZipFile, RuntimeError):
        studio.print_output("Back-up geweigerd of mislukt: controleer projectmetadata, paden, limieten en schrijfrechten.", file=sys.stderr)
        if plan is not None:
            studio.print_output("Een eventueel bestand op " + studio.terminal_text(str(plan.archive)) +
                                ".incomplete is ONVOLLEDIG en geen geslaagde back-up; bij een publicatiefout kan ook de ZIP bestaan. Er is niets automatisch verwijderd.", file=sys.stderr)
        return 1
