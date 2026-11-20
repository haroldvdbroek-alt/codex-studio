# Ontwikkelregels voor PROJECT_NAME

- Communiceer in begrijpelijk Nederlands. Lees eerst README, code, tests en
  toepasselijke bovenliggende instructies. Onderzoek de Git-status.
- Stel bij grotere wijzigingen een plan voor. Maak kleine wijzigingen en gebruik
  in een Git-project een taakbranch. Behoud bestaand werk van de gebruiker.
- Gebruik Python 3.11+ en alleen de standaardbibliotheek. Houd code in
  `src/project_package`, tests in `tests` en gebruik absolute package-imports.
- Voer vanuit de projectmap `python -m unittest discover -s tests -v` uit.
  Tests maken zelf het eigen src-pad beschikbaar, zonder installatie.
- Houd tests volledig offline: geef fictieve configuratiewaarden door, lees geen
  echte API-sleutels en behoud de netwerkblokkade. Gebruik een lokale nepclient.
- Er is geen providerkoppeling. Voeg geen echte of betaalde API-aanroepen toe
  zonder aparte opdracht en toestemming. Tests mogen die nooit nodig hebben.
- Bewaar geen secrets of persoonsgegevens in code, fixtures, logs of Git.
  Houd de sleutel buiten repr en foutmeldingen; log configuratie niet integraal.
- Alleen `.env.example` met lege/fictieve waarden mag worden gedeeld. `.env`
  wordt niet automatisch ingelezen; de app leest procesomgevingsvariabelen.
- Vraag toestemming voor installaties, updates en destructieve handelingen.
  Initialiseer Git of GitHub niet ongevraagd. Maak alleen een commit of push
  als de gebruiker dit uitdrukkelijk vraagt. Rapporteer controles en beperkingen.
