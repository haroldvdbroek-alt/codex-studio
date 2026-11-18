# Codex Development Studio

Codex Development Studio is een herbruikbare werkmap met afspraken voor samenwerken met Codex aan software. De afspraken zijn bruikbaar voor verschillende programmeertalen en soorten projecten.

Deze studio bevat ontwikkelafspraken, templates voor Python, web, offline AI en bestandsautomatisering, en een generator voor nieuwe projecten. De generator gebruikt alleen de Python-standaardbibliotheek. Je hebt Python 3.11 of hoger nodig, maar hoeft geen pakketten te installeren. Voor JavaScript-tests gebruik je daarnaast Node.js 22 of hoger.

## Documentatie

- [Beginnen op Windows met VS Code en PowerShell](docs/GETTING_STARTED.md)
- [Dagelijkse workflow, tests, Git en GitHub](docs/WORKFLOW.md)
- [Veiligheid, secrets en persoonlijke gegevens](docs/SECURITY.md)
- [Beschikbare en geplande templates](docs/TEMPLATES.md)
- [Problemen oplossen en bekende beperkingen](docs/TROUBLESHOOTING.md)
- [Een release voorbereiden en handmatig publiceren](docs/RELEASING.md)
- [Changelog](CHANGELOG.md)

## Wat staat waar?

| Onderdeel | Doel |
| --- | --- |
| `AGENTS.md` | Instructies voor Codex bij het onderzoeken, wijzigen en controleren van projecten. |
| `README.md` | Deze uitleg voor jou als gebruiker. |
| `docs/` | Handleidingen voor beginnen, ontwikkelen, veiligheid, templates en problemen oplossen. |
| `create_project.py` | Maakt een zelfstandig Python-, web- of AI-project op basis van een template. |
| `tests/` | Automatische tests voor de generator. |
| `templates/` | Werkende startsjablonen voor Python, web en offline AI-voorbereiding. |
| `templates/ai-app/` | Python met omgevingsconfiguratie, lokale nepclient en offline tests; geen echte providerkoppeling. |
| `templates/automation/` | Bestandsverwerking met dry-run, logging, tests en expliciete uitvoering via `--apply`. |
| `templates/python-app/` | Werkend Python-template met src-layout, tests en GitHub Actions. |
| `templates/web-app/` | HTML, CSS en JavaScript zonder frameworks, met tests en GitHub Actions. |

## Hoe werk je met de studio?

1. Open deze map in Codex en geef aan aan welk project je wilt werken. Geef bij een bestaand project het juiste pad op.
2. Beschrijf het gewenste resultaat in gewone taal. Vermeld wat wel en niet mag veranderen.
3. Codex onderzoekt eerst het project en de instructies. Bij grotere wijzigingen stelt Codex een kort plan voor.
4. Codex maakt kleine wijzigingen en gebruikt bij een Git-project een aparte branch: een eigen werklijn voor de taak.
5. Codex schrijft passende tests voor veranderd gedrag en controleert het resultaat. Bij documentatie controleert Codex de tekst en verwijzingen.
6. Je krijgt een Nederlandse samenvatting van de wijzigingen, controles en eventuele openstaande punten.

Codex maakt alleen een commit of push als je daar uitdrukkelijk om vraagt. De projectgenerator initialiseert zelf geen Git-repository en maakt geen GitHub-repository aan.

## Een Python-project genereren

Zonder argumenten start je nu een interactief menu:

```powershell
python .\create_project.py
```

Kies Python, Web, AI (offline demo) of Automation. Voer een geldige projectnaam
en een bovenliggende doelmap in. Het menu toont het volledige doelpad en vraagt
om bevestiging: alleen `ja` maakt het project aan. Een lege bevestiging of `nee`
annuleert. Met `q`, `annuleren`, Ctrl+C of einde invoer annuleer je tijdens iedere
invoerstap zonder projectbestanden of doelmappen aan te maken. Einde invoer is
in PowerShell doorgaans Ctrl+Z gevolgd door Enter.

Een bestaande doelmap of ongeldig pad wordt geweigerd; je kunt een andere
bovenliggende map kiezen. Bij afbreken nadat het aanmaken al gestart is kan een
gedeeltelijk project achterblijven; het script meldt dit en verwijdert niets.

Enter bij de doelmap kiest de bestaande standaard `C:/App/Codex/Projects`.
Kies expliciet een ander pad als je dat wilt. De bestaande CLI hieronder blijft
zonder vragen werken; ook onvolledige CLI-argumenten starten niet automatisch het menu.

Open een terminal in de hoofdmap van deze studio en voer uit:

```text
python .\create_project.py mijn-notities --type python --output "$HOME\Projects"
```

Dit PowerShell-voorbeeld maakt `Projects/mijn-notities` onder je thuismap.
Gebruik voorlopig altijd `--output`: de huidige code gebruikt zonder die optie
`C:/App/Codex/Projects`. De helptekst toont nu die werkelijke standaard;
de test controleert de ingestelde standaard nu veilig met een tijdelijke map.
De package heet
`mijn_notities`: koppeltekens worden underscores, zodat Python de naam kan importeren.

Je kunt een andere bovenliggende map kiezen:

```text
python create_project.py mijn-notities --type python --output ./projecten
```

Het resultaat staat dan in `./projecten/mijn-notities`. Een relatief pad is relatief
aan je huidige terminalmap. Gebruik aanhalingstekens rond paden met spaties.
De generator vindt het template relatief aan zijn eigen script, ook als je hem
vanuit een andere map aanroept. `--output` ondersteunt ook `~` voor je thuismap.

Projectnamen bevatten maximaal 64 kleine letters, cijfers en enkele koppeltekens.
Begin met een letter en eindig met een letter of cijfer. Spaties, underscores,
punten, padtekens en dubbele koppeltekens zijn niet toegestaan. Namen die door
Windows of Python worden gereserveerd en namen van standaardbibliotheekmodules
(zoals `unittest`) worden geweigerd om conflicten te voorkomen.

De generator vervangt de template-namen in de package, imports, tests, metadata
en documentatie. Alleen de expliciet toegestane templatebestanden worden gelezen
en gekopieerd. Lokale omgevingen, caches, Git-gegevens, `.env`-bestanden en andere
onbekende bestanden worden niet meegenomen. Zet ook in de toegestane
templatebestanden nooit persoonlijke gegevens of secrets: de generator kan de
inhoud daarvan niet automatisch als gevoelig herkennen.

Bestaande doelen worden altijd geweigerd, ook lege mappen, bestanden en kapotte
symbolische koppelingen. Symbolische koppelingen en Windows-junctions in bron-
en doelpaden worden niet gevolgd. Gebruik een rechtstreeks pad. Bij een
schrijffout kan een onvolledige nieuwe projectmap achterblijven; de generator
meldt dit en verwijdert niets automatisch. Gebruik de generator in een map die
je zelf beheert; gelijktijdige wijzigingen aan doelpaden door andere processen
zijn niet ondersteund.

Na het genereren kun je het project meteen testen:

```text
cd projecten/mijn-notities
python -m unittest discover -s tests -v
```

Dit voorbeeld gebruikt de uitvoermap `./projecten` van hierboven. Bij het eerste
voorbeeld met `--output "$HOME\Projects"` ga je in PowerShell naar
`Set-Location -LiteralPath "$HOME\Projects\mijn-notities"`.
Lees de gegenereerde README voor het starten van de app. De meegeleverde workflow
kan op GitHub testen zodra dit project de hoofdmap van een repository vormt;
het uitvoeren van de generator publiceert niets.

## Een webproject genereren

Vanuit de studiohoofdmap in PowerShell:

```powershell
python .\create_project.py mijn-website --type web --output "$HOME\Projects"
Set-Location -LiteralPath "$HOME\Projects\mijn-website"
node --test tests/counter.test.cjs
python -m unittest discover -s tests -v
```

Open daarna `public/index.html` in je browser, of start lokaal met
`python -m http.server 8000 --bind 127.0.0.1 --directory public` en bezoek
`http://127.0.0.1:8000`. Stop de server met Ctrl+C. Het project werkt zonder
studio of pakketinstallaties. Dezelfde naamregels en uitvoermapbeperkingen gelden
voor alle types. Zie [het webtemplate](templates/web-app/README.md) voor details.

## Een AI-startproject genereren

Vanuit de studiohoofdmap in PowerShell:

```powershell
python .\create_project.py mijn-ai-app --type ai --output "$HOME\Projects"
Set-Location -LiteralPath "$HOME\Projects\mijn-ai-app"
python -m unittest discover -s tests -v
Push-Location .\src
python -m mijn_ai_app
Pop-Location
```

De app geeft een lokaal demoantwoord; er wordt geen AI-model of API aangeroepen.
Omgevingsvariabelen bereiden een latere koppeling voor. `.env.example` bevat een
lege sleutel en wordt niet automatisch ingelezen. De tests gebruiken uitsluitend
fictieve configuratie en blokkeren netwerkverbindingen. Lees
[het AI-template](templates/ai-app/README.md) voor configuratie en beperkingen.

## Een automation-project genereren

Vanuit de studiohoofdmap in PowerShell:

```powershell
python .\create_project.py mijn-taak --type automation --output "$HOME\Projects"
Set-Location -LiteralPath "$HOME\Projects\mijn-taak"
python -m unittest discover -s tests -v
```

De voorbeeldtaak verwerkt UTF-8 `.txt`-bestanden naar een nieuwe doelmap.
Dry-run is standaard; alleen `--apply` schrijft. Bronbestanden blijven behouden
en bestaande doelen worden geweigerd. Lees [de automation-handleiding](templates/automation/README.md)
voor een veilige demo met fictieve gegevens. Er wordt geen planning of achtergrondtaak ingericht.

## Templateversies en projectmetadata

Het centrale [manifest](templates/manifest.json) bevat per type de templateversie,
map, naam en expliciete bestandslijst. Alle vier templates beginnen bij `1.0.0`.
De versie van het gegenereerde project in `pyproject.toml` staat daar los van.

Zonder versieoptie gebruikt de generator de huidige lokale templateversie. Je
kunt ook een exacte versie eisen:

```powershell
python .\create_project.py versie-demo --type python --template-version 1.0.0 --output "$HOME\Projects"
```

Een niet-beschikbare versie wordt vóór het aanmaken geweigerd. Er is geen
download, versiearchief, automatische upgrade of migratie. Het menu toont de
versie vóór bevestiging en houdt die keuze vast.

Elk nieuw project krijgt `.codex-project.json` met de metadata-schemaversie,
generatornaam en -versie, projectnaam, eventuele packagenaam en template-id en
-versie. Er worden geen gebruikersnamen, absolute paden of secrets opgenomen.
Bestaande projecten, inclusief projecten zonder metadata, worden niet aangepast.
Een manifestwijziging geldt uitsluitend voor volgende aanmaakopdrachten.

## De studio testen

Voer vanuit de studiohoofdmap uit:

```powershell
python -B run_tests.py
```

Dit voert alle generator-, menu-, manifest-, integratie- en templatetests uit,
plus de JavaScript-tests. Gebruik Python 3.11+ en Node.js 22+. Er wordt niets
geinstalleerd. Een ontbrekende Node-opdracht of falende suite geeft exitcode 1.
De standaardmap-test gebruikt een tijdelijk ingestelde doelmap; er wordt geen
test uitgesloten. Symlink-tests kunnen op Windows worden overgeslagen.

De workflow `.github/workflows/studio-tests.yml` voert dezelfde opdracht uit
op Windows en Linux met Python 3.11/3.14 en Node.js 22/24. Hij publiceert niets.
Zie [release voorbereiden](docs/RELEASING.md) en [de changelog](CHANGELOG.md).

Test het oorspronkelijke template vanuit de studiohoofdmap met:

```text
Push-Location .\templates\python-app
python -m unittest discover -s tests -v
Pop-Location
```

Controleer vanuit de studiohoofdmap ook het webtemplate:

```powershell
Push-Location .\templates\web-app
node --test tests/counter.test.cjs
python -m unittest discover -s tests -v
Pop-Location
```

Controleer vanuit de studiohoofdmap ook het AI-template:

```powershell
Push-Location .\templates\ai-app
python -m unittest discover -s tests -v
Pop-Location
```

Controleer vanuit de studiohoofdmap ook het automation-template:

```powershell
Push-Location .\templates\automation
python -m unittest discover -s tests -v
Pop-Location
```

## Een eerste opdracht

Bijvoorbeeld:

> Onderzoek project [pad naar mijn project]. Leg in eenvoudig Nederlands uit hoe het werkt en hoe ik de bestaande tests kan uitvoeren. Wijzig nog geen bestanden en installeer niets.

Voor een wijziging kun je daarna vragen:

> Voeg [gewenst gedrag] toe aan dit project. Stel eerst een kort plan voor, houd de wijzigingen klein en test het resultaat. Vraag toestemming voor installaties en destructieve opdrachten. Maak geen commit of push.

Vervang tekst tussen vierkante haken door je eigen gegevens. Deel geen wachtwoorden of toegangssleutels.

## Afspraken hergebruiken

De instructies in [AGENTS.md](AGENTS.md) gelden voor deze map en onderliggende projectmappen. Een project kan aanvullende instructies in een eigen `AGENTS.md` hebben; Codex leest die ook voordat het daar wijzigingen maakt.

Wil je de afspraken gebruiken in een project buiten deze studio, laat Codex dan eerst het bestaande project en eventuele instructies onderzoeken. Je kunt daarna vragen de afspraken passend over te nemen. Overschrijf een bestaand instructiebestand niet zomaar. Alleen verwijzen naar een externe projectmap zorgt er niet automatisch voor dat dit bestand daar geldt.

## Waarvoor vraagt Codex toestemming?

Codex vraagt vooraf toestemming voor installaties en voor opdrachten die gegevens kunnen verwijderen of overschrijven. Het verzoek legt uit wat er gaat veranderen en wat de gevolgen zijn. Een al expliciet toegestane handeling hoeft niet opnieuw te worden goedgekeurd zolang die hetzelfde blijft.

Een test controleert of software zich gedraagt zoals bedoeld. Tests geven vertrouwen, maar sluiten niet alle fouten uit. Codex vermeldt daarom ook welke controles niet zijn uitgevoerd. Jij kunt de wijzigingen bekijken voordat je besluit ze vast te leggen of te delen.
