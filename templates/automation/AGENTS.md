# Ontwikkelregels voor PROJECT_NAME

- Communiceer in begrijpelijk Nederlands; onderzoek README, code, tests,
  toepasselijke instructies en Git-status voordat je wijzigingen maakt.
- Maak kleine wijzigingen, stel bij groter werk eerst een plan voor en gebruik
  in een Git-project een taakbranch. Behoud bestaand werk van de gebruiker.
- Gebruik Python 3.11+ en alleen de standaardbibliotheek. Code staat in
  `src/project_package`, tests in `tests`; gebruik absolute package-imports.
- Houd dry-run de standaard. Dry-run schrijft geen bestanden, mappen of logs
  naar schijf. Alleen expliciete `--apply` mag nieuwe bestanden aanmaken.
- Verander of verwijder geen bronbestanden. Weiger bestaande doelmappen en
  bestanden, overlappende paden, symlinks en Windows-junctions.
- Log geen inhoud, secrets of persoonlijke paden. Gebruik alleen tijdelijke,
  fictieve bestanden in tests en test ook foutgevallen en dry-run.
- Test vanuit de projectmap met `python -m unittest discover -s tests -v`.
  Nieuwe testmodules maken het eigen src-pad beschikbaar vóór package-imports.
- Vraag toestemming voor installaties en destructieve opdrachten. Voeg geen
  automatische planning, netwerkverkeer of achtergrondtaak toe zonder opdracht.
  Initialiseer Git/GitHub niet ongevraagd; commit/push alleen op expliciet verzoek.
- Rapporteer uitgevoerde controles en beperkingen eerlijk.
