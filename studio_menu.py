"""Interactieve keuzelaag; bestaande opdrachten bepalen uitvoering en veiligheid."""

from pathlib import Path
import sys

import studio

OPTIONS = {
    "1": ("list", "Projecten bekijken"),
    "2": ("check", "Project controleren (geen tests)"),
    "3": ("updates", "Templateversies vergelijken"),
    "4": ("dashboard", "Lokaal alleen-lezen dashboard starten"),
    "5": ("quality", "Studio controleren (geen tests of rapportbestand)"),
    "6": ("maintenance", "Onderhoud controleren (alleen lezen)"),
    "7": ("backup", "Back-upoverzicht; aanmaken uitsluitend na bevestiging"),
    "8": ("restore", "Herstel controleren; herstellen uitsluitend na bevestiging"),
    "9": ("project-tests", "Projecttests aanvragen (voeren code uit)"),
    "10": ("studio-tests", "Studiotests aanvragen (voeren code uit)"),
    "11": ("release-check", "Lokale releasevoorcontrole (geen tests/publicatie)"),
    "12": ("benchmark", "Benchmark (maakt en verwijdert eigen fictieve tijdelijke bestanden)"),
    "13": ("new", "Nieuw project via bestaand generatormenu"),
}


class Cancelled(Exception):
    """Geen actie aanvragen wanneer invoer wordt geannuleerd."""


def ask(prompt, *, default=None):
    value = input(prompt).strip()
    if value.casefold() in {"q", "annuleren"}:
        raise Cancelled
    if not value:
        if default is None:
            raise Cancelled
        return default
    return value


def yes(prompt):
    return ask(prompt, default="nee").casefold() == "ja"


def project_root(root):
    if root is not None:
        return Path(root)
    default = str(Path.home() / "Projects")
    return Path(ask("Projectroot [Enter = " + studio.terminal_text(default) + "]: ", default=default))


def run(root=None):
    if not sys.stdin.isatty():
        studio.print_output("Het menu vereist een interactieve terminal. Gebruik studio.py --help voor CLI-opdrachten.", file=sys.stderr)
        return 2
    try:
        studio.print_output("Codex Studio — menu")
        studio.print_output("Enter, 0 of q stopt. Bij vervolgvragen annuleert q/Ctrl+C/einde invoer.")
        for number, (_, label) in OPTIONS.items():
            studio.print_output(number + ". " + label)
        while True:
            choice = ask("Kies een nummer: ")
            if choice == "0":
                raise Cancelled
            if choice in OPTIONS:
                break
            studio.print_output("Onbekende keuze. Kies een getoond nummer; er is niets gestart.")
        command = OPTIONS[choice][0]
        if command == "new":
            # De generator toont zelf het doel en schrijft pas na exact 'ja'.
            import create_project
            return create_project.main([])
        if command == "benchmark":
            studio.print_output("De benchmark maakt en verwijdert eigen fictieve tijdelijke bestanden; geen echte projectmap wordt gebruikt.")
            if not yes("12 fictieve projecten, 3 metingen. Starten? Typ ja [nee]: "):
                raise Cancelled
            return studio.main(["benchmark"])
        if command in {"quality", "maintenance", "release-check"}:
            return studio.main([command])
        if command == "studio-tests":
            # De bestaande quality-opdracht toont waarschuwing, werkmap en vaste
            # testopdracht en vraagt zelf 'ja', pas na geslaagde voorcontroles.
            return studio.main(["quality", "--run-tests"])
        if command == "restore":
            archive = ask("Bestaand Studio-ZIP-archief (volledig pad): ")
            output = ask("Nieuwe herstelmap die nog niet bestaat (volledig pad): ")
            arguments = ["restore", archive, "--output=" + output]
            studio.print_output("Standaard worden alleen archief en controlesommen gelezen; geen herstel.")
            if yes("Wil je herstel aanvragen? Daarna volgt nog een overzicht en de exacte HERSTEL-bevestiging [nee]: "):
                arguments.append("--create")
            return studio.main(arguments)
        selected_root = project_root(root)
        arguments = [command, "--root=" + str(selected_root)]
        if command in {"check", "backup", "project-tests"}:
            name = ask("Directe projectmapnaam: ")
            studio.check_path(selected_root, name)  # Bestaande naam-/padvalidatie.
            if command == "project-tests":
                arguments = ["check", "--root=" + str(selected_root), "--run-tests"]
            arguments.insert(1, name)
        if command == "backup":
            default = str(Path.home() / "StudioBackups")
            output = ask("Back-upoudermap [Enter = " + studio.terminal_text(default) + "]: ", default=default)
            arguments.append("--output=" + output)
            studio.print_output("Standaard verschijnt alleen het back-upoverzicht; er wordt niets aangemaakt.")
            if yes("Wil je aanmaken aanvragen? Daarna volgt nog een overzicht en de exacte BACKUP-bevestiging [nee]: "):
                arguments.append("--create")
        return studio.main(arguments)
    except (Cancelled, EOFError, KeyboardInterrupt):
        studio.print_output("Geannuleerd; geen verdere actie gestart. Een al bevestigde actie kan bestanden hebben gewijzigd.")
        return 0
    except Exception:
        studio.log_event("COMMAND_FAILED")
        return 1
