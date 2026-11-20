"""Vaste veilige gebeurtenissen naar stderr; geen bestanden of exceptionteksten."""

import argparse
import logging
import sys

EVENTS = {
    "CLI_INVALID": (logging.ERROR, "Fout: ongeldige opdracht of opties. Gebruik --help; ingevoerde waarden worden niet herhaald."),
    "COMMAND_FAILED": (logging.ERROR, "Opdracht kon niet veilig worden afgerond. Bekijk --help en controleer invoer en toegangsrechten. Deel zo nodig deze gebeurteniscode; foutdetails zijn weggelaten."),
    "COMMAND_CANCELLED": (logging.WARNING, "Uitvoering geannuleerd. Eventueel gestarte tests kunnen bestanden hebben gewijzigd."),
    "CHECKS_FAILED": (logging.WARNING, "Een of meer controles zijn mislukt; zie de veilige resultaten op stdout."),
    "REPORT_TARGET_INVALID": (logging.ERROR, "Rapportdoel geweigerd. Kies een nieuwe lokale naam, passende extensie en bestaande oudermap."),
    "REPORT_TOO_LARGE": (logging.ERROR, "Volledig rapport kon niet veilig worden opgebouwd of overschrijdt de rapportlimiet."),
    "REPORT_SAVED": (logging.INFO, "Rapport opgeslagen op de expliciet gekozen bestemming."),
    "REPORT_WRITE_FAILED": (logging.ERROR, "Rapport niet veilig opgeslagen. Bestaande bestanden blijven behouden; eigen .incomplete-bestand kan achterblijven."),
    "REPORT_CLEANUP_FAILED": (logging.WARNING, "Rapport opgeslagen; eigen tijdelijk rapportbestand kon niet worden opgeruimd."),
    "REPORT_CANCELLED": (logging.WARNING, "Geen volledig rapport opgeslagen wegens annuleren."),
    "STDOUT_FAILED": (logging.ERROR, "Rapport kon niet naar stdout worden geschreven."),
    "PROJECT_ROOT_INVALID": (logging.ERROR, "Projectroot of lokaal manifest is niet veilig leesbaar. Gebruik --root voor de oudermap van je projecten; controleer of die bestaat. Symlinks en junctions kunnen worden geweigerd."),
    "PROJECT_SCAN_SKIPPED": (logging.WARNING, "Waarschuwing: onveilige, onleesbare of ongeldige projectmetadata overgeslagen; overzicht kan onvolledig zijn."),
    "GENERATOR_FAILED": (logging.ERROR, "Fout: project niet veilig aangemaakt. Controleer naam, manifest/template en schrijfrechten. --output is de oudermap; de projectmap mag niet bestaan. Een nieuw doel kan onvolledig zijn; gebruik create_project.py --help."),
    "BACKUP_FAILED": (logging.ERROR, "Back-up geweigerd of mislukt. Controleer het project met studio.py check PROJECT --root ROOT. Gebruik --output voor de back-upmap en controleer rechten en limieten. Een nieuw .incomplete-bestand kan achterblijven."),
    "RESTORE_FAILED": (logging.ERROR, "Herstel geweigerd of mislukt. Controleer het ZIP-archief en de controlesommen. --output moet een nog niet bestaande map met bestaande oudermap zijn. Controleer ook rechten en limieten; een nieuw doel kan ONVOLLEDIG zijn."),
    "DASHBOARD_START_FAILED": (logging.ERROR, "Dashboard kon niet veilig starten. Controleer lokale root, frontendbestanden en poorttoegang."),
    "DASHBOARD_SCAN_FAILED": (logging.WARNING, "Dashboardscan mislukt of begrensd. De API toont geen volledig projectoverzicht."),
    "DASHBOARD_HTTP_ERROR": (logging.WARNING, "Lokaal HTTP-verzoek kon niet veilig worden afgerond; verzoekinhoud niet gelogd."),
    "BENCHMARK_FAILED": (logging.ERROR, "Benchmark niet afgerond. Alleen eigen fictieve data kan zijn aangemaakt; zie het veilige resultaat."),
    "BENCHMARK_CLEANUP_FAILED": (logging.WARNING, "Eigen fictieve benchmarkmap kon niet veilig worden opgeruimd; geen ander opruimdoel gebruikt."),
    "UNKNOWN_EVENT": (logging.WARNING, "Onbekende loggebeurtenis weggelaten; inhoud niet opgenomen."),
}


class SafeStderrHandler(logging.Handler):
    def emit(self, record):
        # Gebruik nooit getMessage(), args, exc_info, stack_info of objectrepr.
        code = record.msg if type(record.msg) is str and record.msg in EVENTS else "UNKNOWN_EVENT"
        level, message = EVENTS[code]
        line = f"[{logging.getLevelName(level)}] {code}: {message}\n"
        try:
            stream = sys.stderr  # Volg redirect_stderr en de huidige CLI-stream.
            encoding = getattr(stream, "encoding", None)
            if encoding:
                line = line.encode(encoding, errors="backslashreplace").decode(encoding)
            stream.write(line)
            stream.flush()
        except Exception:
            # Logging mag geen traceback produceren of naar stdout terugvallen.
            pass

    def handleError(self, record):
        pass


# Een eigen logger, los van root/basicConfig en zonder File-/netwerkhandlers.
_LOGGER = logging.Logger("codex_studio", level=logging.INFO)
_LOGGER.propagate = False
_LOGGER.addHandler(SafeStderrHandler())


def log_event(code):
    selected = code if type(code) is str and code in EVENTS else "UNKNOWN_EVENT"
    _LOGGER.log(EVENTS[selected][0], selected)


HELP_EXAMPLES = {
    "studio.py": "python studio.py list --root PROJECTROOT",
    "studio.py menu": "python studio.py menu --root PROJECTROOT",
    "studio.py list": "python studio.py list --root PROJECTROOT",
    "studio.py check": "python studio.py check PROJECT --root PROJECTROOT",
    "studio.py updates": "python studio.py updates --root PROJECTROOT",
    "studio.py dashboard": "python studio.py dashboard --root PROJECTROOT",
    "studio.py quality": "python studio.py quality --format json",
    "studio.py maintenance": "python studio.py maintenance --format json",
    "studio.py backup": "python studio.py backup PROJECT --root PROJECTROOT --output BACKUPMAP",
    "studio.py restore": "python studio.py restore ARCHIEF.zip --output NIEUWE_MAP",
    "studio.py benchmark": "python studio.py benchmark --projects 12 --repeat 3",
    "studio.py release-check": "python studio.py release-check --version MAJOR.MINOR.PATCH",
    "create_project.py": "python create_project.py mijn-project --type python --output OUDERMAP",
    "dashboard.py": "python dashboard.py --root PROJECTROOT",
}


class DutchHelpFormatter(argparse.HelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix):
        return super()._format_usage(usage, actions, groups, "Gebruik: " if prefix is None else prefix)


class SafeArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", DutchHelpFormatter)
        super().__init__(*args, **kwargs)
        self._positionals.title = "Argumenten"
        self._optionals.title = "Opties"
        for action in self._actions:
            if isinstance(action, argparse._HelpAction):
                action.help = "Toon deze hulptekst en stop."
        example = HELP_EXAMPLES.get(self.prog)
        if example and self.epilog is None:
            self.epilog = "Voorbeeld: " + example + ". Vervang namen in hoofdletters door je eigen waarden."

    def parse_known_args(self, args=None, namespace=None):
        parsed, remaining = super().parse_known_args(args, namespace)
        # Onbekende opties komen bij argparse uiteindelijk bij de hoofdparser.
        # Bewaar alleen de reeds herkende, vertrouwde subparser voor diens hulp.
        for action in self._actions:
            if isinstance(action, argparse._SubParsersAction):
                selected = getattr(parsed, action.dest, None)
                if isinstance(selected, str) and selected in action.choices:
                    self._error_parser = action.choices[selected]
        return parsed, remaining

    def error(self, message):
        # Argparse kan geheime waarden uit ongeldige argumenten terugschrijven.
        log_event("CLI_INVALID")
        context = getattr(self, "_error_parser", self)
        context.print_usage(file=sys.stderr)
        if message.startswith("the following arguments are required:"):
            hint = "Er ontbreken verplichte argumenten of opties. Kijk bij Gebruik en bij --help."
        elif message.startswith("unrecognized arguments:"):
            hint = "Een optie of extra argument wordt niet ondersteund. Controleer de spelling met --help."
        elif "invalid choice:" in message:
            hint = "De gekozen opdracht, het type of het uitvoerformaat is niet beschikbaar. Gebruik een keuze uit --help."
        elif "expected one argument" in message:
            hint = "Een optie mist een waarde. Zet een pad met spaties tussen aanhalingstekens."
        else:
            hint = "Een argument heeft niet de verwachte vorm of waarde. Controleer de toegestane waarden met --help."
        self._print_message(hint + "\n", sys.stderr)
        if context.prog == "studio.py backup":
            self._print_message("De back-upbestemming heet --output; --destination wordt niet ondersteund. Zonder --create verschijnt alleen een overzicht.\n", sys.stderr)
        if context.prog == "studio.py restore":
            self._print_message("--output is verplicht en moet naar een nieuwe herstelmap wijzen. Zonder --create wordt alleen gecontroleerd.\n", sys.stderr)
        example = HELP_EXAMPLES.get(context.prog)
        if example:
            self._print_message("Voorbeeld: " + example + "\n", sys.stderr)
        self.exit(2)
