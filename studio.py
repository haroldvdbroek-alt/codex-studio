"""Alleen-lezen projectoverzicht op basis van .codex-studio.json."""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tomllib
import unicodedata

from process_runner import OutputLimitExceeded, run_bounded

METADATA_FILE = ".codex-studio.json"
MAX_METADATA_BYTES = 64 * 1024
PROJECT_TYPES = {"python", "web", "ai", "automation"}
MANIFEST_PATH = Path(__file__).resolve().parent / "templates" / "manifest.json"
GIT_TIMEOUT = 10
TEST_TIMEOUT = 60
# Vertrouwde lokale beleidslijst, nooit opdrachten uit een projectbestand lezen.
TRUSTED_TESTS = {
    (kind, "1.0.0"): (("python", "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"),)
    for kind in ("python", "ai", "automation")
}
TRUSTED_TESTS[("web", "1.0.0")] = (
    ("python", "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"),
    ("node", "--test", "tests/counter.test.cjs"),
)


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


def read_bytes_file(path: Path, limit: int = MAX_METADATA_BYTES) -> bytes:
    """Begrensd alleen-lezen, zonder koppelingen of bijzondere bestanden."""
    before = path.lstat()
    reject_links(path)
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError("Metadata moet een gewoon bestand van maximaal 64 KiB zijn.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise UnsafePathError("Metadata is tijdens het lezen vervangen.")
        reject_links(path)
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Metadata is te groot.")
    reject_links(path)
    return raw


def read_project(directory: Path) -> Project | None:
    """Open uitsluitend de begrensde metadata, nooit broncode of configuratie."""
    try:
        raw = read_bytes_file(directory / METADATA_FILE)
    except FileNotFoundError:
        return None
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


@dataclass(frozen=True)
class CheckResult:
    status: str
    label: str
    message: str


def check_path(root: Path, name: str) -> Path:
    """PROJECT is een directe mapnaam; geen pad, ADS of Windows-apparaatnaam."""
    reserved = {"con", "prn", "aux", "nul"} | {f"{p}{i}" for p in ("com", "lpt") for i in range(1, 10)}
    reserved |= {prefix + digit for prefix in ("com", "lpt") for digit in ("\u00b9", "\u00b2", "\u00b3")}
    if (not isinstance(name, str) or len(name) > 100 or not re.fullmatch(r"[^\W_][\w-]*", name)
            or name.casefold() in reserved or any(unicodedata.category(c).startswith("C") for c in name)):
        raise ValueError("Gebruik een directe projectmapnaam zonder padtekens of gereserveerde namen.")
    root = Path(os.path.abspath(root.expanduser()))
    reject_links(root)
    if not root.is_dir():
        raise ValueError("Projectroot ontbreekt.")
    directory = root / name
    reject_links(directory)
    if not directory.is_dir() or directory.parent != root:
        raise ValueError("Onbekende of onveilige projectmap.")
    return directory


def safe_relative_path(value: object) -> Path:
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or any(not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*|\.[A-Za-z][A-Za-z0-9_.-]*", part)
                   or part in {".", ".."} or part.endswith((".", " ")) for part in value.split("/"))):
        raise ValueError("Onveilig manifestpad.")
    if any(part.casefold() in {".git", ".venv", "__pycache__", "node_modules", ".env"}
           or (part.casefold().startswith(".env.") and part != ".env.example")
           for part in value.split("/")):
        raise ValueError("Lokale configuratie hoort niet bij de controle.")
    return Path(value)


def template_spec(kind: str) -> dict:
    manifest = json.loads(read_bytes_file(MANIFEST_PATH).decode("utf-8-sig"), object_pairs_hook=unique_keys)
    if (not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 1):
        raise ValueError("Onbekende manifestversie.")
    templates = manifest.get("templates")
    if not isinstance(templates, dict) or kind not in templates:
        raise ValueError("Geen lokale templatebeschrijving beschikbaar.")
    spec = templates[kind]
    if not isinstance(spec, dict) or metadata_version(spec) is None:
        raise ValueError("Templatebeschrijving mist een versie.")
    files = spec.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Templatebeschrijving mist bestanden.")
    paths = [safe_relative_path(value) for value in files]
    if len({str(path).casefold() for path in paths}) != len(paths):
        raise ValueError("Dubbele manifestpaden.")
    return spec


def configuration_checks(project: Project, spec: dict) -> list[CheckResult]:
    results = []
    package = project.location.name.replace("-", "_")
    # Alleen configuratie en test-startpunten; overige code wordt niet ingelezen.
    required = [name for name in spec["files"] if not name.startswith("src/")]
    for name in required:
        path = project.location / safe_relative_path(name.replace("project_package", package))
        try:
            reject_links(path)
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError("Geen gewoon bestand.")
            results.append(CheckResult("PASS", name, "Aanwezig, gewoon bestand en geen koppeling."))
        except UnsafePathError:
            results.append(CheckResult("FAIL", name, "Onveilige koppeling; bestand wordt niet gelezen."))
        except (OSError, ValueError):
            results.append(CheckResult("FAIL", name, "Vereist bestand ontbreekt of is onleesbaar."))
    if project.kind != "web" and not any(r.status == "FAIL" and r.label == "pyproject.toml" for r in results):
        try:
            config = tomllib.loads(read_bytes_file(project.location / "pyproject.toml").decode("utf-8-sig"))
            details = config.get("project")
            if not isinstance(details, dict):
                raise ValueError("Projectmetadata ontbreekt.")
            metadata_field(details, "name")
            results.append(CheckResult("PASS", "pyproject-inhoud", "Geldige TOML met projectnaam."))
        except (OSError, ValueError):
            results.append(CheckResult("FAIL", "pyproject-inhoud", "Ongeldige of onleesbare projectconfiguratie."))
    return results


def trusted_executable(name: str, root: Path) -> str | None:
    """Zoek vaste executable-namen buiten projectroot; geen cwd/PATHEXT-scripts."""
    candidates = (name + ".exe",) if os.name == "nt" else (name,)
    for item in os.environ.get("PATH", "").split(os.pathsep):
        if not item or not Path(item).is_absolute():
            continue
        for filename in candidates:
            path = Path(item) / filename
            try:
                if path.resolve().is_relative_to(root.resolve()):
                    continue
                reject_links(path)
                if path.is_file() and os.access(path, os.X_OK):
                    return str(path)
            except (OSError, ValueError):
                continue
    return None


def child_environment() -> dict[str, str]:
    # Geen geerfde Git-configuratie/injectie en geen Python- of Node-startuphooks.
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(("GIT_", "PYTHON", "NODE_"))}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0",
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return env


def reject_tree_links(directory: Path) -> None:
    """Een onleesbaar pad is geen bewijs dat een boom veilig is."""
    reject_links(directory)
    def unreadable(error: OSError) -> None:
        raise error
    for current, directories, files in os.walk(directory, followlinks=False, onerror=unreadable):
        reject_links(Path(current))
        for name in (*directories, *files):
            if is_link((Path(current) / name).lstat()):
                raise UnsafePathError("Koppeling in gecontroleerde map.")


def git_check(project: Project) -> CheckResult:
    gitdir = project.location / ".git"
    if not os.path.lexists(gitdir):
        return CheckResult("WARN", "Git", "Geen eigen Git-repository; bovenliggende repositories worden niet gebruikt.")
    try:
        reject_links(gitdir)
        if not gitdir.is_dir():
            return CheckResult("WARN", "Git", "Git-worktrees/gitdir-verwijzingen worden niet gevolgd.")
        # Weiger ook koppelingen binnen .git vóór Git deze kan volgen.
        reject_tree_links(gitdir)
        # Git kan tekstverwijzingen volgen zonder symlink of junction. Lees deze
        # niet en weiger de constructie vóór zelfs de eerste Git-opdracht.
        for pointer in ("commondir", "gitdir", "config.worktree", "objects/info/alternates",
                        "objects/info/http-alternates"):
            if os.path.lexists(gitdir / pointer):
                return CheckResult("FAIL", "Git", "Git-administratie bevat een niet-ondersteunde verwijzing; geen Git-opdracht gestart.")
        executable = trusted_executable("git", project.location.parent)
        if executable is None:
            return CheckResult("WARN", "Git", "Geen vertrouwde Git-executable gevonden.")
        prefix = [executable, "--no-optional-locks", "-c", "core.fsmonitor=false",
                  "-c", "core.untrackedCache=false", "-c", "core.hooksPath=" + os.devnull,
                  "-c", "core.attributesFile=" + os.devnull,
                  "-c", "core.quotePath=true", "-C", str(project.location)]
        options = dict(cwd=project.location, env=child_environment(), shell=False,
                       capture_output=True, timeout=GIT_TIMEOUT)
        # git status kan clean/process-filters starten. Lees eerst uitsluitend
        # lokale sleutelnamen zonder includes en schakel iedere filter uit.
        config = run_bounded([*prefix, "config", "--local", "--no-includes", "--null",
                                 "--name-only", "--list"], **options)
        if config.returncode:
            return CheckResult("FAIL", "Git", "Lokale Git-configuratie kon niet veilig worden gecontroleerd.")
        keys = [os.fsdecode(key) for key in config.stdout.split(b"\0") if key]
        if any(key.lower() in {"core.worktree", "extensions.worktreeconfig"} for key in keys):
            return CheckResult("WARN", "Git", "Git-status overgeslagen: aangepaste worktree-verwijzingen niet vertrouwd.")
        if any(key.lower().startswith(("include.", "includeif.")) for key in keys):
            return CheckResult("WARN", "Git", "Git-status overgeslagen: externe configuratie-includes niet vertrouwd.")
        drivers = set()
        for key in keys:
            if key.lower().startswith("filter."):
                driver = key[7:].rsplit(".", 1)[0]
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", driver):
                    return CheckResult("WARN", "Git", "Git-status overgeslagen: onbekende filterconfiguratie.")
                drivers.add(driver)
        overrides = []
        for driver in sorted(drivers):
            overrides.extend(["-c", f"filter.{driver}.clean=", "-c", f"filter.{driver}.process=",
                              "-c", f"filter.{driver}.required=false"])
        prefix = [*prefix[:1], *overrides, *prefix[1:]]
        top = run_bounded([*prefix, "rev-parse", "--show-toplevel"], **options)
        if top.returncode or Path(os.fsdecode(top.stdout).strip()).resolve() != project.location.resolve():
            return CheckResult("FAIL", "Git", "Repository hoort niet bij deze projectmap of is ongeldig.")
        status = run_bounded([*prefix, "status", "--porcelain=v1", "--untracked-files=normal",
                                 "--ignore-submodules=all"], **options)
        if status.returncode:
            return CheckResult("FAIL", "Git", "Git-status kon niet veilig worden bepaald.")
        if status.stdout.strip():
            return CheckResult("WARN", "Git", "Gewijzigde of nieuwe bestanden aanwezig; niets aangepast.")
        return CheckResult("PASS", "Git", "Schone werkmap (submodules niet onderzocht).")
    except UnsafePathError:
        return CheckResult("FAIL", "Git", "Onveilige koppeling in Git-administratie.")
    except subprocess.TimeoutExpired:
        return CheckResult("FAIL", "Git", "Git-controle overschreed de tijdslimiet.")
    except OutputLimitExceeded:
        return CheckResult("FAIL", "Git", "Uitvoerlimiet overschreden; Git-procesboom gestopt.")
    except (OSError, ValueError):
        return CheckResult("FAIL", "Git", "Git-controle mislukt; geen projectwijzigingen uitgevoerd.")


def test_commands(project: Project) -> list[list[str]]:
    policy = TRUSTED_TESTS.get((project.kind, project.template_version))
    if policy is None:
        return []
    commands = []
    for command in policy:
        executable = sys.executable if command[0] == "python" else trusted_executable(command[0], project.location.parent)
        if not executable:
            raise FileNotFoundError("Benodigd testhulpmiddel ontbreekt.")
        commands.append([executable, *command[1:]])
    return commands


def run_project_tests(project: Project, commands: list[list[str]]) -> list[CheckResult]:
    print_output("WAARSCHUWING: tests voeren projectcode uit en kunnen bestanden wijzigen. Dit is geen sandbox.")
    print_output("Werkmap: " + terminal_text(str(project.location)))
    for command in commands:
        print_output("Opdracht: " + terminal_text(subprocess.list2cmdline(command)))
    try:
        print_output("Typ ja om tests uit te voeren; Enter, nee of q annuleert.")
        answer = input("Doorgaan? ").strip().casefold()
        if answer != "ja":
            return [CheckResult("SKIP", "Tests", "Geannuleerd; geen tests gestart.")]
    except (EOFError, KeyboardInterrupt):
        return [CheckResult("SKIP", "Tests", "Geannuleerd; geen tests gestart.")]
    results = []
    for command in commands:
        try:
            reject_tree_links(project.location)
            # Herhaal de statische padcontroles na bevestiging.
            current = read_project(project.location)
            if current != project:
                raise ValueError("Metadata is gewijzigd.")
            spec = template_spec(project.kind)
            if spec["version"] != project.template_version or test_commands(project) != commands:
                raise ValueError("Templateversie, testpolicy of executable is gewijzigd.")
            paths = configuration_checks(project, spec)
            if any(item.status == "FAIL" for item in paths):
                raise ValueError("Projectconfiguratie is gewijzigd of onveilig.")
            result = run_bounded(command, cwd=project.location, env=child_environment(), shell=False,
                                    capture_output=True, timeout=TEST_TIMEOUT)
            results.append(CheckResult("PASS" if result.returncode == 0 else "FAIL", "Tests",
                                       "Opdracht geslaagd." if result.returncode == 0 else
                                       f"Testopdracht mislukt (exitcode {result.returncode}); uitvoer niet getoond om gegevenslekken te voorkomen."))
        except subprocess.TimeoutExpired:
            results.append(CheckResult("FAIL", "Tests", "Tijdslimiet overschreden; testprocesboom gestopt."))
            break
        except OutputLimitExceeded:
            results.append(CheckResult("FAIL", "Tests", "Uitvoerlimiet overschreden; testprocesboom gestopt."))
            break
        except KeyboardInterrupt:
            results.append(CheckResult("SKIP", "Tests", "Onderbroken; eerder gestarte tests kunnen bestanden hebben gewijzigd."))
            break
        except (OSError, ValueError, RecursionError):
            previous = bool(results)
            results.append(CheckResult("FAIL", "Tests", "Testopdracht kon niet veilig worden gestart. " +
                                       ("Eerder gestarte tests kunnen bestanden hebben gewijzigd." if previous
                                        else "Geen testopdracht gestart.")))
            break
    return results


def check_project(root: Path, name: str, run_tests: bool = False) -> list[CheckResult]:
    try:
        directory = check_path(root, name)
        project = read_project(directory)
        if project is None:
            raise ValueError("Geen studiometadata.")
    except (OSError, ValueError, RecursionError):
        return [CheckResult("FAIL", "Project", "Onbekend project, ongeldige metadata of onveilig pad."),
                CheckResult("SKIP", "Overige controles", "Geen vertrouwd project vastgesteld.")]
    results = [CheckResult("PASS", "Metadata", "Geldige .codex-studio.json; geen projectcode ingelezen.")]
    if project.studio_version is None:
        results.append(CheckResult("WARN", "Studioversie", "Onbekend; niet geraden of gewijzigd."))
    try:
        spec = template_spec(project.kind)
        known = project.template_version == spec["version"]
        results.append(CheckResult("PASS" if known else "WARN", "Templateversie",
                                   "Bekende lokale versie." if known else
                                   "Onbekende/niet-lokale versie; configuratie vergeleken met huidige basiseisen."))
        results.extend(configuration_checks(project, spec))
    except (OSError, ValueError, RecursionError):
        results.append(CheckResult("FAIL", "Template", "Lokale templatebeschrijving ontbreekt of is onveilig."))
        known = False
    results.append(git_check(project))
    if not run_tests:
        results.append(CheckResult("SKIP", "Tests", "Niet gevraagd; geen projectcode uitgevoerd."))
    elif not known or any(item.status == "FAIL" for item in results):
        results.append(CheckResult("SKIP", "Tests", "Onbekende versie of falende veiligheids-/configuratiecontrole."))
    else:
        try:
            commands = test_commands(project)
            results.extend(run_project_tests(project, commands) if commands else
                           [CheckResult("SKIP", "Tests", "Geen expliciet toegestane testopdracht voor dit type en deze versie.")])
        except (OSError, ValueError):
            results.append(CheckResult("FAIL", "Tests", "Een vertrouwd testhulpmiddel ontbreekt."))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bekijk studio-projecten zonder ze te wijzigen.")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="Toon projecten met .codex-studio.json")
    listing.add_argument("--root", type=Path, default=None, help="Projectroot (standaard: ~/Projects)")
    checking = commands.add_parser("check", help="Controleer metadata, templateconfiguratie en Git-status")
    checking.add_argument("project", help="Directe projectmapnaam onder de root")
    checking.add_argument("--root", type=Path, default=None, help="Projectroot (standaard: ~/Projects)")
    checking.add_argument("--run-tests", action="store_true", help="Vraag bevestiging voor een toegestane testopdracht")
    args = parser.parse_args(argv)
    root = Path.home() / "Projects" if args.root is None else args.root
    if args.command == "check":
        try:
            results = check_project(root, args.project, args.run_tests)
        except KeyboardInterrupt:
            print_output("SKIP Controle geannuleerd.")
            return 130
        for result in results:
            print_output(f"{result.status} {terminal_text(result.label)}: {terminal_text(result.message)}")
        counts = {status: sum(item.status == status for item in results) for status in ("PASS", "WARN", "FAIL", "SKIP")}
        print_output("Samenvatting: " + ", ".join(f"{count} {status}" for status, count in counts.items()))
        return 1 if counts["FAIL"] else 0
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
