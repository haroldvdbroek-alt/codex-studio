"""Genereer een Python-project zonder installaties of Git-opdrachten."""

import argparse
import keyword
import os
from pathlib import Path
import re
import stat
import sys


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "python-app"
# Alleen gecontroleerde templatebestanden. Nieuwe bestanden worden niet vanzelf
# meegenomen; breid deze lijst bewust uit als het template verandert.
TEMPLATE_FILES = (
    "AGENTS.md",
    "README.md",
    "pyproject.toml",
    ".gitignore",
    ".github/workflows/python-tests.yml",
    "src/project_package/__init__.py",
    "src/project_package/__main__.py",
    "src/project_package/greeting.py",
    "tests/test_greeting.py",
)
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


def render_template(project_name: str, package_name: str) -> dict[Path, str]:
    """Lees uitsluitend toegestane UTF-8-bestanden, vóór het doel wordt gemaakt."""
    rendered = {}
    replacements = {"PROJECT_NAME": project_name, "project_package": package_name}
    for relative_name in TEMPLATE_FILES:
        source = TEMPLATE_DIR / relative_name
        reject_links(source.absolute())
        if not source.is_file():
            raise ValueError(f"Verplicht templatebestand ontbreekt: {relative_name}")
        content = source.read_text(encoding="utf-8")
        # Eén vervangingsronde voorkomt dat nieuwe tekst opnieuw wordt vervangen.
        content = re.sub(
            r"PROJECT_NAME|project_package",
            lambda match: replacements[match.group()],
            content,
        )
        relative_target = Path(relative_name.replace("project_package", package_name))
        rendered[relative_target] = content
    return rendered


def create_project(project_name: str, output: Path | str | None = None) -> Path:
    """Maak een nieuw project onder output (standaard ~/Projects).

    Een bestaand doel wordt nooit hergebruikt. Bij een schrijffout kan een
    onvolledig nieuw project achterblijven; verwijder dit niet automatisch.
    """
    package_name = package_name_for(project_name)
#    parent = Path.home() / "Projects" if output is None else Path(output).expanduser()
    parent = "C:/App/Codex/Projects" if output is None else Path(output).expanduser()
    parent = Path(os.path.abspath(parent))
    reject_links(parent)
    parent = parent.resolve()
    target = parent / project_name
    # lexists detecteert ook een kapotte symbolische koppeling.
    if os.path.lexists(target):
        raise FileExistsError(f"De doelmap of het doelbestand bestaat al: {target}")
    rendered = render_template(project_name, package_name)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Maak een nieuw Python-project met alleen de standaardbibliotheek."
    )
    parser.add_argument("name", help="Projectnaam, bijvoorbeeld mijn-notities")
    parser.add_argument("--type", required=True, choices=("python",), help="Projecttype")
    parser.add_argument(
        "--output", type=Path,
        help="Bovenliggende doelmap (standaard: ~/Projects); ~ wordt ondersteund",
    )
    args = parser.parse_args(argv)
    try:
        target = create_project(args.name, args.output)
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Fout: {error}", file=sys.stderr)
        return 1
    print(f"Project aangemaakt: {target}")
    print("Ga naar deze map en voer uit: python -m unittest discover -s tests -v")
    print("Git is niet geïnitialiseerd; er is geen GitHub-repository aangemaakt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
