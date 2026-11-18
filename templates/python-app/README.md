# PROJECT_NAME

Een klein herbruikbaar Python-project met alleen de standaardbibliotheek:
de modules die met Python worden meegeleverd. Er zijn geen externe pakketten
nodig. Gebruik Python 3.11 of hoger.

## Bestanden

```text
.
├── src/
│   └── project_package/
│       ├── __init__.py     # Maakt de map een Python-package
│       ├── __main__.py     # Startpunt van de voorbeeldapp
│       └── greeting.py     # Voorbeeldfunctie
├── tests/
│   └── test_greeting.py    # Tests met unittest
├── .github/workflows/python-tests.yml
├── .gitignore
├── AGENTS.md
├── pyproject.toml
└── README.md
```

Een package is een verzameling Python-modules. Bij deze `src`-layout staat
de package in `src`, apart van tests en documentatie.

## Beginnen met een eigen project

De studio-generator kan deze stappen automatisch uitvoeren. Als dit project al
door de generator is gemaakt, zijn de projectnaam en packagenaam al ingevuld.
Je kunt dan direct doorgaan naar de tests. Voor handmatig kopiëren:

1. Kopieer de inhoud van deze templatemap naar een nieuwe projectmap. Neem ook
   `.github` en `.gitignore` mee, maar geen lokale `.venv` of `__pycache__`-mappen.
2. Vervang `PROJECT_NAME` in de metadata en documentatie door je projectnaam,
   bijvoorbeeld `voorbeeld-app`. De projectnaam mag afwijken van de packagenaam.
3. Hernoem desgewenst `src/project_package` en vervang dan ook `project_package`
   in imports, instructies en opdrachten. Gebruik voor een packagenaam kleine
   letters en underscores, bijvoorbeeld `voorbeeld_app`.
4. Voer de tests hieronder uit voordat je de voorbeeldcode uitbreidt.

Er zijn bewust geen auteursgegevens, externe afhankelijkheden of secrets ingevuld.
`pyproject.toml` bevat alleen projectmetadata; er is geen build-backend ingericht.
Het template is dus bedoeld voor rechtstreeks uitvoeren en testen, niet voor
`pip install` of publicatie. Kies zo'n uitbreiding later bewust en vraag eerst
toestemming voor eventuele installaties.

## Tests uitvoeren zonder installatie

Open een terminal in de projectmap: de map met deze README en `pyproject.toml`.
Voer uit:

```text
python -m unittest discover -s tests -v
```

Op systemen waar Python `python3` heet, vervang je `python` door `python3`.
De vier tests controleren de begroeting, spaties rondom de naam, lege invoer
en de uitvoer van de app. Bij succes eindigt de uitvoer met `OK`.

Python vindt een package onder `src` niet vanzelf vanuit de projectmap.
Daarom voegt `tests/test_greeting.py` het absolute pad naar `src` toe aan
`sys.path`, de lijst met plaatsen waar Python modules zoekt. Het pad wordt
berekend vanaf het testbestand. Daarna werken absolute imports zoals
`from project_package.greeting import greet` zonder installatie of `PYTHONPATH`.
Neem deze voorbereiding over in iedere nieuwe testmodule voordat je de package
importeert; vertrouw niet op de volgorde waarin testmodules worden geladen.

## De voorbeeldapp starten

Vanuit de projectmap kun je tijdelijk naar `src` gaan, zodat Python de package
kan vinden. Dit werkt in PowerShell en gangbare Linux/macOS-shells:

```text
cd src
python -m project_package
cd ..
```

Verwachte uitvoer: `Hallo, Voorbeeld!`. Een lege naam geeft in de voorbeeldfunctie
een `ValueError`: een foutmelding voor een ongeldige waarde.

## Automatisch testen op GitHub

Wanneer de gekopieerde projectinhoud de hoofdmap van een GitHub-repository vormt,
staat de workflow op `.github/workflows/python-tests.yml`. GitHub Actions voert
dezelfde testopdracht uit bij een push, een pull request of handmatig starten.
De workflow test Python 3.11 tot en met 3.14 op Linux, zonder projectpakketten
te installeren. De GitHub-runner stelt wel de gekozen Python-versie beschikbaar.
Er zijn geen eigen secrets nodig; de repositoryrechten zijn beperkt tot lezen.

GitHub ontdekt deze workflow niet zolang hij alleen onder
`templates/python-app/.github/workflows` in de studio staat. Kopieer voor een
zelfstandig project dus de volledige template-inhoud naar de repositoryhoofdmap.
De gebruikte acties volgen de officiële documentatie van
[setup-python](https://github.com/actions/setup-python) en
[GitHub Actions voor Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

## Verder ontwikkelen

Lees eerst `AGENTS.md`. Voeg kleine stukken gedrag toe en schrijf daarbij tests.
Bewaar nooit wachtwoorden of toegangssleutels in het project. `.gitignore` helpt
lokale bestanden buiten Git te houden, maar vervangt geen controle op geheimen.
