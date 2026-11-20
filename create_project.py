"""Genereer Python-, web-, AI- en automation-projecten zonder installaties of Git."""

import argparse
import keyword
import json
import os
from pathlib import Path
import re
import stat
import sys

_previous_bytecode_setting = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from studio_logging import log_event, SafeArgumentParser
        from studio import read_bytes_file, unique_keys, reject_json_constant
    finally:
        sys.path.pop(0)
finally:
    sys.dont_write_bytecode = _previous_bytecode_setting

DEFAULT_OUTPUT = Path.home() / "Projects"
PROJECT_TYPES = {"1": "python", "2": "web", "3": "ai", "4": "automation"}
MANIFEST_PATH = Path(__file__).resolve().parent / "templates" / "manifest.json"
TEMPLATES_ROOT = MANIFEST_PATH.parent
GENERATOR_VERSION = "1.0.0"
METADATA_FILE = ".codex-studio.json"
RESERVED_NAMES = {"con", "prn", "aux", "nul", "clock$", "conin$", "conout$"} | {
    f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
}


def package_name_for(project_name: str) -> str:
    """Valideer een draagbare projectnaam en geef de packagenaam terug."""
    if not isinstance(project_name, str) or not re.fullmatch(
        r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", project_name, flags=re.ASCII
    ) or len(project_name) > 64:
        raise ValueError(
            "Gebruik 1 tot 64 kleine letters, cijfers en enkele koppeltekens; "
            "begin met een letter en eindig met een letter of cijfer."
        )
    package_name = project_name.replace("-", "_")
    if (
        project_name in RESERVED_NAMES
        or not package_name.isidentifier()
        or keyword.iskeyword(package_name)
        or keyword.issoftkeyword(package_name)
        or package_name in sys.stdlib_module_names
    ):
        raise ValueError(
            "Deze naam is gereserveerd door het besturingssysteem of Python; "
            "kies een andere projectnaam."
        )
    return package_name


def reject_links(path: Path) -> None:
    """Weiger symlinks en Windows-junctions, ook in bovenliggende mappen."""
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ValueError(f"Symbolische koppelingen zijn niet toegestaan: {part}")


def safe_manifest_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Manifestpaden moeten veilige relatieve paden zijn.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or part.endswith((".", " ")) for part in parts):
        raise ValueError("Onveilig manifestpad.")
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
        raise ValueError("Ongeldige tekens in manifestpad.")
    if any(part.casefold() in {".git", ".venv", "__pycache__", "node_modules", METADATA_FILE, ".codex-project.json"}
           or (part.casefold().startswith(".env") and value != ".env.example")
           for part in parts):
        raise ValueError("Lokale of gereserveerde bestanden zijn niet toegestaan in het manifest.")
    return value


def load_manifest() -> dict:
    """Valideer vóór writes; onbekende schema's of versies worden niet geraden."""
    reject_links(MANIFEST_PATH.absolute())
    try:
        data = json.loads(read_bytes_file(MANIFEST_PATH).decode("utf-8-sig"),
                          object_pairs_hook=unique_keys, parse_constant=reject_json_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Het template-manifest kan niet worden gelezen.") from error
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("Niet-ondersteunde manifestversie; verwacht schema_version 1.")
    templates = data.get("templates")
    if not isinstance(templates, dict) or set(templates) != set(PROJECT_TYPES.values()):
        raise ValueError("Het manifest moet precies de vier ondersteunde templates bevatten.")
    for spec in templates.values():
        if not isinstance(spec, dict):
            raise ValueError("Ongeldige templatedefinitie.")
        version = spec.get("version")
        if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
            raise ValueError("Templateversie moet de vorm MAJOR.MINOR.PATCH hebben.")
        if not isinstance(spec.get("label"), str) or not spec["label"].strip() or any(ord(c) < 32 for c in spec["label"]):
            raise ValueError("Ongeldig templatelabel.")
        safe_manifest_path(spec.get("directory"))
        files = spec.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Een template moet een expliciete bestandslijst bevatten.")
        paths = [safe_manifest_path(value) for value in files]
        folded = [value.casefold() for value in paths]
        if len(set(folded)) != len(folded):
            raise ValueError("Dubbele manifestpaden zijn niet toegestaan.")
        if any(p.startswith(other + "/")
               for p in folded for other in folded if p != other):
            raise ValueError("Een manifestbestand mag geen bovenliggende map van een ander bestand zijn.")
    return data


# Compatibele namen voor bestaande tests en Python-gebruikers; de lijsten zelf
# staan uitsluitend in het manifest. Afwijkende waarden kunnen tests injecteren.
try:
    _INITIAL_MANIFEST = load_manifest()
except ValueError as _error:
    if __name__ == "__main__":
        log_event("GENERATOR_FAILED")
        raise SystemExit(1)
    raise
_ALIASES = {"python": ("TEMPLATE_DIR", "TEMPLATE_FILES"),
            "web": ("WEB_TEMPLATE_DIR", "WEB_TEMPLATE_FILES"),
            "ai": ("AI_TEMPLATE_DIR", "AI_TEMPLATE_FILES"),
            "automation": ("AUTOMATION_TEMPLATE_DIR", "AUTOMATION_TEMPLATE_FILES")}
_INITIAL_VALUES = {}
for _kind, (_dir_alias, _files_alias) in _ALIASES.items():
    _spec = _INITIAL_MANIFEST["templates"][_kind]
    for _alias, _value in ((_dir_alias, TEMPLATES_ROOT / _spec["directory"]),
                           (_files_alias, tuple(_spec["files"]))):
        globals()[_alias] = _value
        _INITIAL_VALUES[_alias] = _value


def render_template(
    project_name: str, package_name: str, *, project_type: str = "python",
    template_version: str | None = None,
) -> dict[Path, str]:
    """Lees uitsluitend toegestane UTF-8-bestanden, vóór het doel wordt gemaakt."""
    rendered = {}
    replacements = {"PROJECT_NAME": project_name, "project_package": package_name}
    manifest = load_manifest()
    if project_type not in manifest["templates"]:
        raise ValueError("Onbekend projecttype; kies python, web, ai of automation.")
    spec = manifest["templates"][project_type]
    if template_version is not None and template_version != spec["version"]:
        raise ValueError(f"Templateversie {template_version!r} is niet beschikbaar voor {project_type}; beschikbaar: {spec['version']}.")
    dir_alias, files_alias = _ALIASES[project_type]
    template_dir = (globals()[dir_alias] if globals()[dir_alias] != _INITIAL_VALUES[dir_alias]
                    else TEMPLATES_ROOT / spec["directory"])
    files = (globals()[files_alias] if globals()[files_alias] != _INITIAL_VALUES[files_alias]
             else spec["files"])
    for relative_name in files:
        source = template_dir / relative_name
        reject_links(source.absolute())
        if not source.is_file():
            raise ValueError(f"Verplicht templatebestand ontbreekt: {relative_name}")
        content = read_bytes_file(source).decode("utf-8")
        # Eén vervangingsronde voorkomt dat nieuwe tekst opnieuw wordt vervangen.
        content = re.sub(
            r"PROJECT_NAME|project_package",
            lambda match: replacements[match.group()],
            content,
        )
        relative_target = Path(relative_name.replace("project_package", package_name))
        if any(str(path).casefold() == str(relative_target).casefold() for path in rendered):
            raise ValueError("Naamvervanging veroorzaakt dubbele doelbestanden.")
        rendered[relative_target] = content
    metadata = {
        "schema_version": 1,
        "generator": {"name": "Codex Development Studio", "version": GENERATOR_VERSION},
        "project": {"name": project_name, "package": None if project_type == "web" else package_name},
        "template": {"id": project_type, "version": spec["version"]},
    }
    rendered[Path(METADATA_FILE)] = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    return rendered


def project_destination(project_name: str, output: Path | str | None = None) -> Path:
    """Controleer het doel zonder iets aan te maken, ook bruikbaar vóór bevestiging."""
    package_name_for(project_name)
    parent = DEFAULT_OUTPUT if output is None else Path(output).expanduser()
    parent = Path(os.path.abspath(parent))
    reject_links(parent)
    for part in (parent, *parent.parents):
        if part.exists() and not part.is_dir():
            raise NotADirectoryError("De bovenliggende doelmap bevat een bestand als padonderdeel.")
    parent = parent.resolve()
    target = parent / project_name
    # lexists detecteert ook een kapotte symbolische koppeling.
    if os.path.lexists(target):
        raise FileExistsError(f"De doelmap of het doelbestand bestaat al: {target}")
    return target


def create_project(
    project_name: str, output: Path | str | None = None, *, project_type: str = "python",
    template_version: str | None = None,
) -> Path:
    """Maak een nieuw project; standaard onder ~/Projects.

    Een bestaand doel wordt nooit hergebruikt. Bij een schrijffout kan een
    onvolledig nieuw project achterblijven; verwijder dit niet automatisch.
    """
    package_name = package_name_for(project_name)
    target = project_destination(project_name, output)
    parent = target.parent
    # Behoud de bestaande Python-aanroep voor gebruikers van deze functie.
    rendered = render_template(project_name, package_name, project_type=project_type,
                               template_version=template_version) if template_version is not None else (
        render_template(project_name, package_name)
        if project_type == "python"
        else render_template(project_name, package_name, project_type=project_type)
    )
    parent.mkdir(parents=True, exist_ok=True)
    reject_links(parent)
    # Zonder exist_ok: ook als het doel inmiddels is aangemaakt, weigeren we het.
    target.mkdir()
    try:
        for relative_path, content in rendered.items():
            destination = target / relative_path
            reject_links(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
    except (OSError, ValueError) as error:
        raise OSError(
            f"Schrijven mislukt; mogelijk onvolledig project in {target}. "
            "Er is niets automatisch verwijderd."
        ) from error
    return target


class MenuCancelled(Exception):
    """De gebruiker heeft vóór het schrijven geannuleerd."""


def menu_input(prompt: str) -> str:
    value = input(prompt).strip()
    if value.casefold() in {"q", "annuleren"}:
        raise MenuCancelled
    return value


def interactive_arguments() -> argparse.Namespace | None:
    """Verzamel en controleer keuzes; pas na bevestiging mag main schrijven."""
    print("Codex Development Studio — nieuw project")
    manifest = load_manifest()
    for number, kind in PROJECT_TYPES.items():
        print(f"{number}. {manifest['templates'][kind]['label']}")
    print("Typ q of annuleren om te stoppen. Ctrl+C en einde invoer annuleren ook.")
    while True:
        choice = menu_input("Projecttype [1-4]: ").casefold()
        project_type = PROJECT_TYPES.get(choice, choice)
        if project_type in PROJECT_TYPES.values():
            break
        print("Kies 1, 2, 3 of 4 (of python, web, ai, automation).")
    while True:
        name = menu_input("Projectnaam (bijvoorbeeld mijn-project): ")
        try:
            package_name = package_name_for(name)
        except ValueError:
            print("Ongeldige naam: gebruik kleine letters, cijfers en enkele koppeltekens; vermijd gereserveerde namen.")
            continue
        break
    # Ontbrekende/onveilige bronbestanden falen vóór bevestiging en vóór writes.
    preview = render_template(name, package_name, project_type=project_type)
    version = json.loads(preview[Path(METADATA_FILE)])["template"]["version"]
    while True:
        output_text = menu_input(f"Bovenliggende doelmap [Enter = {DEFAULT_OUTPUT}]: ")
        output = Path(output_text).expanduser() if output_text else DEFAULT_OUTPUT
        try:
            target = project_destination(name, output)
        except (OSError, ValueError):
            print("Ongeldig doel: kies een veilige lokale oudermap en een nog niet bestaande projectmap.")
            continue
        break
    print(f"\nType: {project_type}\nTemplateversie: {version}\nProjectnaam: {name}\nDoel: {target}")
    if project_type != "web":
        print(f"Python-package: {package_name}")
    print("Er wordt geen Git- of GitHub-repository aangemaakt.")
    while True:
        confirmation = menu_input("Aanmaken? Typ ja om te bevestigen [nee]: ").casefold()
        if confirmation == "ja":
            return argparse.Namespace(name=name, type=project_type, output=target.parent, template_version=version)
        if confirmation in {"", "nee", "n"}:
            return None
        print("Typ ja om aan te maken, of nee om te annuleren.")


def main(argv: list[str] | None = None) -> int:
    parser = SafeArgumentParser(prog="create_project.py",
        description="Maak een Python-, web-, AI- of automation-project zonder externe pakketten."
    )
    parser.add_argument("name", help="Projectnaam, bijvoorbeeld mijn-notities")
    parser.add_argument("--type", required=True, choices=("python", "web", "ai", "automation"), help="Projecttype")
    parser.add_argument("--template-version", help="Eis exact de lokaal beschikbare templateversie")
    parser.add_argument(
        "--output", type=Path,
        help=f"Bovenliggende doelmap (standaard: {DEFAULT_OUTPUT}); ~ wordt ondersteund",
    )
    arguments = sys.argv[1:] if argv is None else argv
    try:
        if not arguments:
            args = interactive_arguments()
            if args is None:
                print("Geannuleerd; niets aangemaakt.")
                return 0
        else:
            args = parser.parse_args(arguments)
    except (MenuCancelled, EOFError, KeyboardInterrupt):
        print("\nGeannuleerd; niets aangemaakt.")
        return 0
    except Exception:
        log_event("GENERATOR_FAILED")
        return 1
    try:
        target = create_project(args.name, args.output, project_type=args.type,
                                template_version=args.template_version)
    except KeyboardInterrupt:
        log_event("COMMAND_CANCELLED")
        return 130
    except Exception:
        log_event("GENERATOR_FAILED")
        return 1
    print(f"Project aangemaakt: {target}")
    print("Ga naar deze map en voer uit: python -m unittest discover -s tests -v")
    if args.type == "web":
        print("Voer ook uit: node --test tests/counter.test.cjs")
    print("Git is niet geïnitialiseerd; er is geen GitHub-repository aangemaakt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
