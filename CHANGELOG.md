# Changelog

Hier staan wijzigingen die voor gebruikers van Codex Development Studio relevant
zijn. Een vermelding hieronder is geen bewijs dat iets al gepubliceerd is.
De eerste release moet nog handmatig worden vastgesteld.

## Nog niet uitgebracht

### Toegevoegd

- Templates voor Python, web zonder frameworks, offline AI-voorbereiding en
  bestandsautomatisering met dry-run en logging.
- Een generator met bestaande CLI-opdrachten en een interactief menu met
  validatie, bevestiging en annulering.
- Een centraal template-manifest, exacte versiecontrole en `.codex-project.json`
  met herkomstinformatie voor nieuwe projecten.
- Nederlandse beginnershandleidingen en een handmatige releaseprocedure.
- `run_tests.py` voor generator-, menu-, manifest-, template- en integratietests.
- Een GitHub Actions-testmatrix voor Windows/Linux, Python 3.11/3.14 en Node.js
  22/24, zonder automatisch publiceren.

### Verbeterd

- De standaardmap-test gebruikt nu een tijdelijke ingestelde doelmap, zodat de
  volledige suite veilig kan draaien. De standaardmap van de generator is niet gewijzigd.
- De testopdracht faalt als Node.js ontbreekt of een suite mislukt.

### Bekende beperkingen

- Zonder `--output` blijft de standaard `C:/App/Codex/Projects`.
- Echte symlink-tests kunnen zonder geschikte Windows-rechten worden overgeslagen.
- Er is één lokale versie per template; geen downloadarchief, updater of migratie
  voor bestaande projecten.
- De AI-demo is offline; de webtests gebruiken geen volledige browser.
- Automation is geen scheduler en schrijft geen transactionele batches.

## Nieuwe release noteren

Verplaats bij een echte release de relevante punten naar een sectie met het
daadwerkelijke versienummer en de publicatiedatum. Laat bovenaan een nieuwe
sectie **Nog niet uitgebracht** staan. Zie [de releasehandleiding](docs/RELEASING.md).
