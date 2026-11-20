"""Vaste veilige gebeurtenissen naar stderr; geen bestanden of exceptionteksten."""

import argparse
import logging
import sys

EVENTS = {
    "CLI_INVALID": (logging.ERROR, "Fout: ongeldige opdracht of opties. Gebruik --help; ingevoerde waarden worden niet herhaald."),
    "COMMAND_FAILED": (logging.ERROR, "Uitvoering kon niet veilig worden afgerond. Geen exceptiontekst of traceback getoond."),
    "COMMAND_CANCELLED": (logging.WARNING, "Uitvoering geannuleerd. Eventueel gestarte tests kunnen bestanden hebben gewijzigd."),
    "CHECKS_FAILED": (logging.WARNING, "Een of meer controles zijn mislukt; zie de veilige resultaten op stdout."),
    "REPORT_TARGET_INVALID": (logging.ERROR, "Rapportdoel geweigerd. Kies een nieuwe lokale naam, passende extensie en bestaande oudermap."),
    "REPORT_TOO_LARGE": (logging.ERROR, "Volledig rapport kon niet veilig worden opgebouwd of overschrijdt de rapportlimiet."),
    "REPORT_SAVED": (logging.INFO, "Rapport opgeslagen op de expliciet gekozen bestemming."),
    "REPORT_WRITE_FAILED": (logging.ERROR, "Rapport niet veilig opgeslagen. Bestaande bestanden blijven behouden; eigen .incomplete-bestand kan achterblijven."),
    "REPORT_CLEANUP_FAILED": (logging.WARNING, "Rapport opgeslagen; eigen tijdelijk rapportbestand kon niet worden opgeruimd."),
    "REPORT_CANCELLED": (logging.WARNING, "Geen volledig rapport opgeslagen wegens annuleren."),
    "STDOUT_FAILED": (logging.ERROR, "Rapport kon niet naar stdout worden geschreven."),
    "PROJECT_ROOT_INVALID": (logging.ERROR, "Projectroot of lokaal manifest ontbreekt, is onleesbaar, ongeldig of onveilig."),
    "PROJECT_SCAN_SKIPPED": (logging.WARNING, "Waarschuwing: onveilige, onleesbare of ongeldige projectmetadata overgeslagen; overzicht kan onvolledig zijn."),
    "GENERATOR_FAILED": (logging.ERROR, "Fout: project niet veilig aangemaakt. Controleer naam, template, doelmap en schrijfrechten; een nieuw doel kan onvolledig zijn."),
    "BACKUP_FAILED": (logging.ERROR, "Back-up geweigerd of mislukt. Controleer metadata, paden, limieten en rechten; een nieuw .incomplete-bestand kan achterblijven."),
    "RESTORE_FAILED": (logging.ERROR, "Herstel geweigerd of mislukt. Controleer archief, controlesommen, nieuwe doelmap en rechten. Behandel een eventueel nieuw doel als ONVOLLEDIG."),
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


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # Argparse kan geheime waarden uit ongeldige argumenten terugschrijven.
        log_event("CLI_INVALID")
        self.print_usage(file=sys.stderr)
        self.exit(2)
