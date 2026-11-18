# Ontwikkelregels voor PROJECT_NAME

Deze regels vullen de instructies van Codex Development Studio aan. Ook wanneer
dit template los wordt gebruikt, gelden de volgende afspraken.

- Communiceer in begrijpelijk Nederlands. Onderzoek eerst de README, code, tests,
  eventuele bovenliggende instructies en Git-status.
- Stel bij grotere wijzigingen eerst een kort plan voor. Houd wijzigingen klein
  en beperk ze tot dit project.
- Werk in een Git-repository op een aparte taakbranch. Maak alleen een commit of
  push als de gebruiker dat uitdrukkelijk vraagt. Initialiseer Git niet ongevraagd.
- Gebruik Python 3.11 of hoger en uitsluitend de Python-standaardbibliotheek.
  Voeg geen externe afhankelijkheden of buildhulpmiddelen toe zonder toestemming.
- Houd productiecode onder `src/project_package` en tests onder `tests`.
  Gebruik absolute imports zoals `from project_package.greeting import greet`.
- De tests maken `src` beschikbaar via `sys.path`, relatief aan het testbestand.
  Nieuwe testmodules die rechtstreeks door discovery worden geladen, moeten dit
  ook doen voordat ze de package importeren. Vertrouw niet op de importvolgorde
  van andere testmodules of op een lokaal geïnstalleerde package.
- Schrijf passende `unittest`-tests voor nieuw gedrag en foutoplossingen.
  Voer vanuit de projectmap `python -m unittest discover -s tests -v` uit.
- Houd de workflow en README in overeenstemming met de lokale testopdracht.
- Controleer invoervalidatie, toegang en omgang met gegevens waar relevant.
  Gebruik fictieve testgegevens; voeg geen gebruikersgegevens of secrets toe.
- Vraag vooraf expliciete toestemming voor installaties, updates en destructieve
  opdrachten. Leg de concrete handeling en gevolgen uit. Laat bestaande lokale
  omgevingen en werk van de gebruiker ongemoeid.
- Meld bij afronding de wijzigingen, uitgevoerde controles en beperkingen.
