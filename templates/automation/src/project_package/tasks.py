"""Verwerk directe UTF-8 .txt-bestanden naar een nieuwe doelmap."""

import logging
import os
from pathlib import Path
import stat


def reject_links(path: Path) -> None:
    """Weiger symlinks en Windows-reparsepunten, ook in bovenliggende mappen."""
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError("Gebruik rechtstreekse paden zonder koppelingen.")


def process_files(source: Path | str, destination: Path | str, *, apply: bool = False,
                  logger: logging.Logger | None = None) -> int:
    """Zet tekst om naar hoofdletters; standaard alleen een plan, zonder writes.

    Bron en doel mogen niet overlappen. De hele doelmap moet nieuw zijn.
    Gebruik alleen vertrouwde mappen; gelijktijdige padwijzigingen zijn niet ondersteund.
    """
    log = logger if logger is not None else logging.getLogger(__name__)
    source = Path(os.path.abspath(Path(source).expanduser()))
    destination = Path(os.path.abspath(Path(destination).expanduser()))
    reject_links(source)
    reject_links(destination)
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir():
        raise ValueError("De bron moet een bestaande map zijn.")
    if source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError("Bron en doel mogen niet gelijk zijn of in elkaar liggen.")
    if os.path.lexists(destination):
        raise FileExistsError("De doelmap of het doelbestand bestaat al; kies een nieuw doel.")
    files = []
    for entry in sorted(source.iterdir()):
        reject_links(entry)
        if entry.is_file() and entry.suffix.lower() == ".txt":
            files.append(entry)
    for number, _ in enumerate(files, 1):
        log.info("%s: tekstbestand %d naar een nieuw bestand met hoofdletters",
                 "UITVOEREN" if apply else "DRY-RUN", number)
    if not apply or not files:
        log.info("%d bestand(en) gepland; niets geschreven.", len(files))
        return len(files)
    # Lees en valideer alles vóór de eerste schrijfopdracht; geen inhoud in logs.
    prepared = []
    for entry in files:
        reject_links(entry)
        try:
            prepared.append((entry.name, entry.read_text(encoding="utf-8").upper()))
        except UnicodeError:
            raise ValueError("Een bronbestand is geen geldige UTF-8-tekst.") from None
    reject_links(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    reject_links(destination)
    destination.mkdir()  # Geen exist_ok: een inmiddels bestaand doel wordt geweigerd.
    for name, text in prepared:
        target = destination / name
        reject_links(target)
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    log.info("%d bestand(en) verwerkt; bronbestanden behouden.", len(prepared))
    return len(prepared)
