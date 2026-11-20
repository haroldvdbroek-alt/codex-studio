# Templates en generator

Een template is een startpunt met code, tests en afspraken. Het is geen volledige
toepassing met alle mogelijke functies.

## Beschikbaarheid

| Template | Status | Wat werkt er nu? |
| --- | --- | --- |
| `python-app` | Beschikbaar | Python-package, begroetingsapp, unittest-tests, metadata en workflow. |
| `ai-app` | Beschikbaar | Python met configuratie, lokale nepclient en offline tests; geen echte AI-provider. |
| `automation` | Beschikbaar | Handmatige tekstverwerking met dry-run, logging en tests; geen scheduler. |
| `web-app` | Beschikbaar | HTML, CSS en JavaScript met teller, tests en workflow, zonder frameworks. |

`--type python`, `--type web`, `--type ai` en `--type automation` worden ondersteund. Er is geen installatie-, deployment-
of publicatiecommando in de generator.

## Genereren en namen vervangen

Vanuit de studiohoofdmap:

```powershell
python .\create_project.py mijn-notities --type python --output "$HOME\Projects"
```

`--output` is de bovenliggende map, niet de volledige nieuwe projectmap. Gebruik
de optie om een andere oudermap te kiezen. Standaard gebruikt de generator
`~/Projects`; de helptekst toont het werkelijke pad op jouw computer.

Projectnamen hebben 1 tot 64 tekens: kleine ASCII-letters, cijfers en enkele
koppeltekens. Ze beginnen met een letter en eindigen met een letter of cijfer.
Spaties, underscores, punten, padtekens en dubbele koppeltekens zijn niet
toegestaan. Gereserveerde Windows-namen, Python-woorden en namen uit de
standaardbibliotheek worden geweigerd.

De generator vervangt `PROJECT_NAME` door `mijn-notities` en `project_package`
door `mijn_notities`, zowel in bestandsinhoud als in de packagemap. Dit past ook
imports en tests aan. De workflow gebruikt geen packagenaam en blijft inhoudelijk
gelijk. In het oorspronkelijke template horen de placeholders te blijven staan.

## Wat komt er in het project?

```text
mijn-notities/
  AGENTS.md
  README.md
  pyproject.toml
  .gitignore
  .github/workflows/python-tests.yml
  src/mijn_notities/__init__.py
  src/mijn_notities/__main__.py
  src/mijn_notities/greeting.py
  tests/test_greeting.py
```

`src` houdt de app-code apart van tests en documentatie. `__init__.py` maakt de
map een package. `greeting.py` bevat de voorbeeldfunctie. `__main__.py` start de
app wanneer je vanuit `src` `python -m mijn_notities` uitvoert.

`pyproject.toml` bevat naam, versie, beschrijving en de minimale Python-versie.
`dependencies = []` betekent dat er geen externe projectpakketten nodig zijn.
Er is geen expliciete build-backend ingericht. Installeren met pip, bouwen en
publiceren zijn geen onderdeel van de ondersteunde werkwijze.

## Tests en imports

Vanuit de gegenereerde projecthoofdmap:

```powershell
python -m unittest discover -s tests -v
```

`unittest` hoort bij Python. Discovery zoekt hier naar `test*.py` in `tests`.
Iedere test controleert een verwachting met bijvoorbeeld `assertEqual` of
`assertRaises`. De vier tests controleren gewone invoer, witruimte, lege invoer
en de uitvoer van de app.

Het testbestand berekent het pad naar de eigen `src`-map vanaf `__file__` en
voegt dat toe aan `sys.path`, de zoeklijst voor imports. Daardoor werkt
`from mijn_notities.greeting import greet` zonder installatie. Nieuwe testmodules
die de package importeren moeten dezelfde voorbereiding krijgen. Vertrouw niet
op de uitvoervolgorde van andere testbestanden.

Het zelfstandige project heeft de studio niet nodig om te testen of te draaien.
De verwijzingen naar de studio in de documentatie zijn uitleg, geen codeafhankelijkheid.

## GitHub Actions

De workflow is bedoeld voor een zelfstandig project met `.github/workflows` in
de repositoryhoofdmap. Hij vraagt Python 3.11, 3.12, 3.13 en 3.14 op een
Linux-runner en voert dezelfde unittest-opdracht uit. Hij bevat triggers voor
push, pull request en handmatig starten. De laatste lokale controle alleen is
geen bewijs dat al die versies op GitHub geslaagd zijn.

Er is geen GitHub-repository nodig om lokaal te werken. Publiceren is een aparte,
bewuste stap; zie [de workflow](WORKFLOW.md).

## Webtemplate

Vanuit de studiohoofdmap:

```powershell
python .\create_project.py mijn-website --type web --output "$HOME\Projects"
Set-Location -LiteralPath "$HOME\Projects\mijn-website"
node --test tests/counter.test.cjs
python -m unittest discover -s tests -v
```

Het webproject bevat `public/index.html`, `public/styles.css`, `public/app.js`,
`tests/counter.test.cjs`, `tests/test_page.py`, README, AGENTS.md, `.gitignore`
en `.github/workflows/web-tests.yml`. Open `public/index.html` rechtstreeks in
een browser. De zes JavaScript-tests gebruiken Node.js 22+; de drie HTML-controles
gebruiken Python 3.11+. Er is geen installatie of build nodig. De knoptests
gebruiken een nagebootst document, geen volledige browser.

`PROJECT_NAME` wordt vervangen in paginatitel, kop en documentatie. Er is geen
Python-package in het webproject. Dezelfde strikte projectnaamvalidatie geldt
voor alle types. De websectie van het manifest bepaalt welke bestanden worden gekopieerd.
De webworkflow test Node.js 22 en 24 op Windows en Linux met Python 3.11. Hij
publiceert niets. Zie [de volledige webhandleiding](../templates/web-app/README.md).

## AI-template: offline voorbereiding

Vanuit de studiohoofdmap:

```powershell
python .\create_project.py mijn-ai-app --type ai --output "$HOME\Projects"
Set-Location -LiteralPath "$HOME\Projects\mijn-ai-app"
python -m unittest discover -s tests -v
Push-Location .\src
python -m mijn_ai_app
Pop-Location
```

Dit is een Python-project met dezelfde src-layout en metadata-aanpak, plus
`config.py`, `client.py` en `service.py`. Het gebruikt alleen de standaardbibliotheek.
`AI_MODE=mock` en `AI_MODEL=demo-model` zijn de standaardwaarden. `AI_API_KEY`
is optioneel en wordt door de lokale nepclient niet gebruikt. Andere modi worden
geweigerd; er is nog geen netwerkcode, provideradapter of echt model.

De generator neemt alleen de expliciet toegestane `.env.example` met lege sleutel
mee, geen `.env`, lokale varianten of onbekende bestanden. Python leest deze
bestanden niet automatisch. Gebruik procesomgevingsvariabelen zoals uitgelegd in
[de AI-handleiding](../templates/ai-app/README.md).

De 13 tests gebruiken fictieve configuratie en blokkeren sockets en DNS tijdens
de tests. De workflow `ai-tests.yml` draait ze met Python 3.11 en 3.14 op Windows
en Linux, zonder secrets of projectinstallatie. Het gegenereerde project werkt
ook zelfstandig zonder de studio. Een echte provider toevoegen vraagt een
aparte opdracht; behoud de offline tests als vaste controle.

## Automation-template

Vanuit de studiohoofdmap:

```powershell
python .\create_project.py mijn-taak --type automation --output "$HOME\Projects"
Set-Location -LiteralPath "$HOME\Projects\mijn-taak"
python -m unittest discover -s tests -v
```

De package bevat `tasks.py` en een CLI in `__main__.py`, naast metadata,
ontwikkelregels, README, `.gitignore`, tests en `automation-tests.yml`.
De voorbeeldtaak verwerkt uitsluitend directe UTF-8 `.txt`-bestanden naar
hoofdletters in een nieuwe doelmap. Bronbestanden blijven behouden.

Dry-run is standaard en schrijft niets. Alleen `--apply` voert de taak uit.
Een bestaande doelmap, overlappende paden en koppelingen worden geweigerd.
De taak leest bij uitvoeren alle tekst eerst in; gebruik kleine bestanden.
Logging gaat naar stderr zonder inhoud, namen of persoonlijke paden.
Zie [de automation-handleiding](../templates/automation/README.md) voor een
uitvoerbare demo, loguitleg en beperkingen bij gedeeltelijke schrijffouten.

Tests gebruiken tijdelijke mappen; de workflow draait ze op Windows en Linux
met Python 3.11 en 3.14. Een echte symlink-test kan lokaal overgeslagen worden.
Het script kan handmatig herhaald worden met een nieuwe doelmap; het template
installeert geen scheduler of achtergrondservice.

## Templates uitbreiden

Onderzoek eerst de projectregels in
[het Python-template](../templates/python-app/AGENTS.md) of
[het webtemplate](../templates/web-app/AGENTS.md) of
[het AI-template](../templates/ai-app/AGENTS.md) of
[het automation-template](../templates/automation/AGENTS.md). Voeg gedrag met tests toe en
test daarna ook een nieuw gegenereerd project. Nieuwe templatebestanden worden
niet automatisch gekopieerd: de expliciete lijsten staan centraal in
[`templates/manifest.json`](../templates/manifest.json). De oude constanten in de
generator worden daarvan afgeleid voor compatibiliteit. Breid de lijsten alleen uit met gecontroleerde bestanden zonder
persoonlijke gegevens; zie [veilig werken](SECURITY.md).

## Versies en herkomst

Het manifest gebruikt `schema_version: 1` en per template een versie in de vorm
`MAJOR.MINOR.PATCH`, aanvankelijk `1.0.0`. Verhoog de templateversie wanneer je
de geleverde template wijzigt; een versienummer bewaart zelf geen oude bestanden.
De generator ondersteunt één huidige lokale versie per type. Hij voert geen
netwerkdownloads of updates van bestaande projecten uit.

`--template-version 1.0.0` eist een exacte overeenkomst met het manifest. Zonder
de optie wordt de huidige lokale versie gebruikt. Een onbekende versie, ongeldig
schema of onveilig pad wordt vóór writes geweigerd. Het menu toont de versie en
weigert een gewijzigde versie na bevestiging in plaats van stilzwijgend door te gaan.

De gegenereerde `.codex-studio.json` legt de gebruikte template-id en -versie,
generatorversie en projectnamen vast. Dit bestand is herkomstinformatie, geen
installatiebestand of automatische updater. De projectversie in `pyproject.toml`
is een apart begrip en blijft door de ontwikkelaar beheerd. Bestaande projecten
krijgen niet achteraf metadata en worden niet aangepast bij een manifestwijziging.
