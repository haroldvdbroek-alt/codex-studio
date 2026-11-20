# Codex Development Studio

Voor het samenvoegen na geslaagde CI en het bewust publiceren van een nieuwe
versie zie [de publicatiehandleiding](docs/RELEASING.md).

Codex Development Studio is een herbruikbare werkmap met afspraken voor samenwerken met Codex aan software. De afspraken zijn bruikbaar voor verschillende programmeertalen en soorten projecten.

Deze studio bevat ontwikkelafspraken, een Python-template en een generator voor nieuwe projecten. De generator gebruikt alleen de Python-standaardbibliotheek. Je hebt Python 3.11 of hoger nodig, maar hoeft geen pakketten te installeren.

Begin met de [workflowhandleiding voor Windows](docs/WORKFLOW.md) en gebruik de
[herbruikbare projectchecklist](docs/PROJECT_CHECKLIST.md) bij iedere taak.
Beide behandelen Python, web, AI en automation en maken onderscheid tussen
werkende functies en nog geplande templates.

## Eerst een back-upoverzicht bekijken

```powershell
python -B .\studio.py backup mijn-project --root "C:\App\Codex\Projects"
```

Deze opdracht toont alleen de selectie en maakt niets aan. Alleen met
`--create`, een opnieuw getoond overzicht en de exacte interactieve bevestiging
`BACKUP mijn-project` wordt een lokale ZIP gemaakt. Gevoelige bestanden,
gegevensmappen, Git-gegevens en tijdelijke bestanden worden standaard uitgesloten.
De ZIP is niet versleuteld en is geen volledige gegevensback-up.
Lees [back-ups maken](docs/BACKUPS.md) voor bestemming, selectie, limieten,
annuleren en foutafhandeling.

## Een back-up controleren en herstellen

```powershell
python -B .\studio.py restore "$HOME\StudioBackups\project.zip" --output "C:\App\Codex\Projects\project-herstel"
```

Gebruik de werkelijke archiefnaam. Zonder `--create` worden alleen structuur,
bestandslijst, CRC en SHA-256 gecontroleerd en wordt het overzicht getoond.
Herstel vereist `--create` plus de exacte interactieve bevestiging
`HERSTEL project-herstel`. De doelmap mag nog niet bestaan, ook niet leeg.
Er wordt geen projectcode uitgevoerd of iets geïnstalleerd.
Lees de [herstelhandleiding](docs/RESTORE.md) voor beperkingen en onvolledig herstel.
Controlesommen bewijzen geen herkomst; vertrouw de bron voordat je herstelde code start.

## Lokaal browserdashboard

Met `python -B studio.py benchmark` kun je `list`, `updates` en `check` meten
op uitsluitend tijdelijke fictieve projecten. Er wordt geen echte projectroot
gescand of aangepast. Zie [benchmark gebruiken](docs/BENCHMARK.md) voor omvang,
meetbereik, JSON/Markdown-uitvoer en opruimen.

Voor een lokale releasevoorcontrole is er `python -B studio.py release-check`.
Deze opdracht publiceert nooit. Ze toont lokale blokkades en welke externe
controles je nog handmatig moet verifiëren. Lees [release voorbereiden](docs/RELEASE.md)
en de [changelog](CHANGELOG.md); een lokaal rapport is geen publicatietoestemming.

Voor alleen-lezen onderhoud gebruik je `python studio.py maintenance`. Deze
opdracht controleert documentatie, templates, teststructuur, versiegegevens en
releasebestanden. Vaststellingen en aanbevelingen staan apart; testdekking wordt
niet afgeleid uit testbestanden. Er worden geen tests of reparaties gestart.
Zie [onderhoud controleren](docs/MAINTENANCE.md) voor JSON/Markdown en beperkingen.

Controleer de studio eerst met `python -B studio.py quality`. Deze opdracht
controleert bestanden, manifest/templates, Python-syntaxis, lokale documentatielinks
en Git-status zonder de onderzochte code uit te voeren. Met `--run-tests` vraagt
ze na de controles toestemming voor de vaste studio-testsuite. Zie
[quality gebruiken](docs/QUALITY.md) voor statussen, limieten en beperkingen.
Gebruik `--format json` of `--format markdown` voor dezelfde resultaten in een
andere vorm. Alleen met bijvoorbeeld `--format json --output quality-rapport.json`
wordt een nieuw rapportbestand gemaakt; bestaande bestanden worden geweigerd.
Voor een eventuele terugkerende controle zijn er een
[PowerShell-script en Taakplanner-handleiding](docs/TASK_SCHEDULER.md).
Er wordt geen taak automatisch aangemaakt: je test het script eerst handmatig
en besluit daarna zelf of je een taak in Windows Taakplanner opslaat.

Start vanuit deze hoofdmap in PowerShell:

```powershell
python studio.py dashboard --root "C:\App\Codex\Projects"
```

Zonder `--root` wordt `$HOME\Projects` gebruikt. Open het getoonde
`http://127.0.0.1:poort/`-adres in je browser. Stop de server met `Ctrl+C` in
PowerShell; opruimen kan circa 17 seconden duren.

Het dashboard toont projecten, templateversies, update-status en configuratie-
en Git-status. Tests staan op `NIET_UITGEVOERD`: er worden geen projecttests
of installaties gestart. De achtergrondcontrole gebruikt alleen-lezen
controles en vaste Git-opdrachten. De browser kan uitsluitend het laatste
overzicht ophalen en kan geen opdrachten uitvoeren of projectbestanden wijzigen.
Er zijn geen externe pakketten, CDN's of externe browserverzoeken nodig.

Lees [veilig gebruik en beperkingen](docs/SECURITY.md) voor routes,
beveiligingsheaders, scanlimieten en uitleg van de statussen. Dit dashboard is
bedoeld voor lokaal gebruik en mag niet via een tunnel of proxy worden gedeeld.

## Projecten bekijken

Gebruik vanuit de studiohoofdmap:

```powershell
python -B .\studio.py list
python -B .\studio.py list --root "D:\Projecten"
```

De standaardroot is `$HOME\Projects`, onafhankelijk van de standaardmap van de
generator. Alleen directe projectmappen met `.codex-studio.json` worden herkend.
Het overzicht toont naam, type, studioversie, templateversie en locatie. Een
ontbrekende root wordt niet aangemaakt; het commando geeft dan een foutmelding.
Een lege root geeft een leeg overzicht. Er is geen recursieve zoekactie.

Verwachte UTF-8-metadata, met of zonder BOM (maximaal 64 KiB):

```json
{
  "schema_version": 1,
  "project": {"name": "mijn-project"},
  "generator": {"version": "1.0.0"},
  "template": {"id": "python", "version": "1.0.0"}
}
```

Types zijn `python`, `web`, `ai` en `automation`; versies gebruiken drie getallen
zoals `1.0.0`. Bij handmatige registratie mag een versie expliciet `null` zijn:
het overzicht toont dan `onbekend`, zonder een historische versie te verzinnen.
Ontbrekende versievelden blijven ongeldig. Andere velden worden niet getoond. Ongeldige of onleesbare metadata
en koppelingen worden overgeslagen met een waarschuwing zonder metadata-inhoud.
Bij waarschuwingen is de exitcode 1: het overzicht kan onvolledig zijn. Zonder
problemen is de exitcode 0; ongeldige commandoregelargumenten geven 2.

Unicode blijft behouden bij UTF-8-uitvoer. Bij een beperktere terminalcodering,
zoals CP1252, worden niet-ondersteunde tekens zichtbaar ge-escaped (bijvoorbeeld
`\u6d4b`) zodat ook omgeleide uitvoer niet crasht. Dit wijzigt de metadata niet.

Symlinks en Windows-junctions in root, bovenliggende mappen, projectmappen of
metadata worden geweigerd. Gebruik rechtstreekse, vertrouwde mappen die niet
gelijktijdig door andere processen worden vervangen. Leescontrole en bestandstoegang
zijn geen transactionele momentopname. Het commando voert geen projectcode uit
en leest geen `.env`, broncode of andere projectbestanden.

De huidige generator op deze branch schrijft deze metadata nog niet. Ook
`.codex-project.json` wordt niet als alternatief gelezen. Er worden geen bestanden
hernoemd, toegevoegd of gemigreerd in bestaande projecten. Alleen-lezen betekent
hier geen inhouds- of configuratiewijzigingen; het besturingssysteem kan bij lezen
wel toegangstijden bijwerken. `-B` voorkomt Python-importcachebestanden.

Test het lijstcommando met `python -B -m unittest discover -s tests -p test_studio.py -v`.

## Een project controleren

```powershell
python -B .\studio.py check mijn-project
python -B .\studio.py check mijn-project --root "C:\App\Codex\Projects"
```

De standaardroot is ook hier `$HOME\Projects`. `PROJECT` is de directe mapnaam,
niet een willekeurig pad. Gebruik `--root` voor een andere bovenliggende map.
Padnavigatie, absolute projectpaden, Windows-apparaatnamen en alternatieve
datastromen worden geweigerd. Koppelingen en junctions worden niet gevolgd,
ook niet wanneer ze naar een andere projectmap verwijzen.

Iedere controle toont een status:

| Status | Betekenis |
| --- | --- |
| PASS | De genoemde controle slaagde; dit is geen algemene veiligheidsgarantie. |
| WARN | Er is een aandachtspunt, bijvoorbeeld onbekende versies, wijzigingen of geen eigen Git-repository. |
| FAIL | De controle mislukte of een pad/configuratie is onveilig of onvolledig. |
| SKIP | Een controle is niet uitgevoerd, bijvoorbeeld tests zonder expliciet verzoek. |

De samenvatting telt de statussen. Exitcode 1 betekent minimaal een FAIL; alleen
waarschuwingen of bewust overgeslagen tests geven 0. Ongeldige CLI-argumenten
geven 2. Ctrl+C tijdens de gewone controle geeft 130.

De standaardcontrole voert geen projectcode uit en maakt of wijzigt geen
projectbestanden. Ze leest `.codex-studio.json`, de lokale templatebeschrijving
en bij Python/AI/automation de begrensde `pyproject.toml` om TOML en de projectnaam
te controleren. Ze controleert de aanwezigheid en veilige paden van README,
AGENTS.md, `.gitignore`, workflow- en testbestanden uit het manifest. Bij AI wordt
alleen de aanwezigheid van `.env.example` gecontroleerd; echte `.env`-bestanden
worden niet geopend. Python-code en YAML-workflows worden niet uitgevoerd of
inhoudelijk als programma gevalideerd.

`templates/manifest.json` is voor deze opdracht hersteld uit de eerdere
studioversie. De bestaande generator op deze branch is daarbij niet gewijzigd.
Een onbekende project-templateversie geeft een WARN: de bestandscontrole gebruikt
dan alleen de huidige basiseisen. Bestaande metadata wordt nooit aangepast.

Git wordt uitsluitend gebruikt voor lokale sleutelnamen zonder includes,
`rev-parse --show-toplevel` en `status --porcelain=v1`, met vaste argumenten,
`shell=False` en een limiet van 10 seconden per opdracht. Optionele indexwrites,
fsmonitor, hooks, clean/process-filters en submoduleonderzoek worden uitgeschakeld.
Externe configuratie-includes, worktree-verwijzingen en een ontbrekende Git-tool
geven een WARN en geen verzonnen schone status. Onveilige Git-koppelingen of een
onleesbare/onbetrouwbare repository geven FAIL. De opdracht verandert geen
`safe.directory`-instellingen en maakt geen repository aan. Alleen `git.exe` of
`git` uit absolute PATH-mappen buiten de projectroot wordt als hulpmiddel gebruikt;
geen lokaal `git.cmd` of gelijknamig programma uit het project.

Ook tekstverwijzingen in `.git` worden gecontroleerd. `commondir`, `gitdir`,
`config.worktree`, `objects/info/alternates` en `objects/info/http-alternates`
geven FAIL vóór de eerste Git-opdracht. Ze worden conservatief ook geweigerd
als ze intern zouden verwijzen; deze constructies worden nog niet ondersteund.
Zo kan Git geen externe administratie of objectmap openen via een gewoon tekstbestand.

## Optioneel projecttests uitvoeren

```powershell
python -B .\studio.py check mijn-project --root "C:\App\Codex\Projects" --run-tests
```

**Let op: tests voeren projectcode uit en kunnen bestanden wijzigen, netwerkverkeer
starten of andere processen aanmaken. Dit is geen sandbox.** Vertrouw het project
zelf voordat je instemt: metadata met een bekend type is geen bewijs van veilige code.

De opdracht doet eerst alle statische controles. Bij toegestane testuitvoering
toont ze de werkmap, de waarschuwing en de testopdrachten; het volledige
resultaatoverzicht volgt daarna. Alleen `ja` geeft toestemming. Enter, `nee`, `q`, Ctrl+C
en einde invoer annuleren de bevestiging zonder een testproces te starten.
Andere antwoorden starten evenmin tests. Een fout in de voorafgaande controles,
onbekende templateversie of ontbrekende lokale testpolicy voorkomt testuitvoering.

De lokale, vaste policy ondersteunt uitsluitend templateversie `1.0.0`:

| Type | Toegestane opdrachten, vanuit de projectmap |
| --- | --- |
| Python, AI, automation | Huidige Python-interpreter met `-I -B -m unittest discover -s tests -v` |
| Web | Dezelfde unittest-opdracht en de vertrouwde Node-executable met `--test tests/counter.test.cjs` |

Er worden nooit opdrachten uit projectmetadata, scripts in `package.json` of
workflowbestanden overgenomen. Geen pip- of npm-installaties. Node moet buiten
de projectroot beschikbaar zijn via een rechtstreeks absoluut PATH-pad.
Onbekende versies blijven SKIP; vul geen historische versies op goed geluk in
om deze controle te omzeilen.

Na bevestiging worden vóór iedere testopdracht metadata, lokale templateversie,
testpolicy, executable, vereiste paden en projectkoppelingen opnieuw gecontroleerd.
Een onleesbare submap wordt niet stilzwijgend overgeslagen: de controle stopt
veilig. Een gewijzigde projectnaam, type, versie, executable of koppeling blokkeert
starten. Als een eerdere opdracht al draaide, blijft het resultaat daarvan zichtbaar;
de melding maakt duidelijk dat eerdere tests bestanden kunnen hebben gewijzigd.
Iedere testopdracht heeft een limiet van 60 seconden; voor Git blijft dat 10 seconden.
De gedeelde runner in `process_runner.py` bewaart per opdracht maximaal **1 MiB
voor stdout en stderr samen**. Bij overschrijding volgt FAIL en stopt de procesboom.
Er worden geen uitvoerbestanden in het project aangemaakt. De testprocessen geven
PASS, FAIL of SKIP bij onderbreken; hun ruwe uitvoer wordt niet getoond om secrets
en persoonsgegevens niet onbedoeld af te drukken. Voor gedetailleerde testuitvoer
kun je de getoonde opdracht zelf in het vertrouwde project uitvoeren.
Op Windows koppelt de runner eerst een geisoleerde Python-wrapper aan een
anoniem Job Object. Pas na succesvolle koppeling mag de wrapper de opdracht
starten. Bij mislukte koppeling start geen projectcode. Het Job Object staat geen
gewone breakaway toe en wordt bij succes, time-out, uitvoeroverschrijding of
annulering gesloten om ook achtergebleven kindprocessen te stoppen.
Op POSIX gebruikt de runner hiervoor een eigen sessie/procesgroep.
Zie de [Microsoft-uitleg over Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

De deadline omvat wachten op proces en uitvoerpijpen, zodat geerfde pijpen geen
onbegrensde wachttijd meer veroorzaken. Opruimen krijgt maximaal 2 extra seconden;
onvolledige opruiming wordt als fout gemeld. OS-procescreatie zelf is niet hard
onderbreekbaar. Na een time-out, uitvoeroverschrijding of annulering worden geen
volgende testopdrachten gestart.

Dit is procesbeheer, geen beveiligingssandbox: code die via een externe dienst
processen laat starten of op POSIX bewust de procesgroep verlaat, kan daarbuiten
vallen. Bestandswijzigingen worden niet teruggedraaid. Gebruik vertrouwde mappen
zonder gelijktijdige padwijzigingen; padcontroles en bestandstoegang blijven
afzonderlijke stappen. De subprocessdeadline begrenst ook geen blokkerende
bestandssysteemoproepen tijdens de voorafgaande padcontrole.

Test de nieuwe controles met:

```powershell
python -B -m unittest discover -s tests -p "test_studio*.py" -v
```

## Wat staat waar?

| Onderdeel | Doel |
| --- | --- |
| `AGENTS.md` | Instructies voor Codex bij het onderzoeken, wijzigen en controleren van projecten. |
| `README.md` | Deze uitleg voor jou als gebruiker. |
| `docs/` | Workflowhandleiding, herbruikbare projectchecklist en beveiligingsuitleg. |
| `create_project.py` | Maakt een zelfstandig Python-project op basis van het template. |
| `tests/` | Automatische tests voor de generator. |
| `templates/` | Startsjablonen; alleen het Python-template is al ingevuld. |
| `templates/ai-app/` | Gereserveerd voor toepassingen met AI. |
| `templates/automation/` | Gereserveerd voor automatiseringen. |
| `templates/python-app/` | Werkend Python-template met src-layout, tests en GitHub Actions. |
| `templates/web-app/` | Gereserveerd voor webtoepassingen. |

## Hoe werk je met de studio?

1. Open deze map in Codex en geef aan aan welk project je wilt werken. Geef bij een bestaand project het juiste pad op.
2. Beschrijf het gewenste resultaat in gewone taal. Vermeld wat wel en niet mag veranderen.
3. Codex onderzoekt eerst het project en de instructies. Bij grotere wijzigingen stelt Codex een kort plan voor.
4. Codex maakt kleine wijzigingen en gebruikt bij een Git-project een aparte branch: een eigen werklijn voor de taak.
5. Codex schrijft passende tests voor veranderd gedrag en controleert het resultaat. Bij documentatie controleert Codex de tekst en verwijzingen.
6. Je krijgt een Nederlandse samenvatting van de wijzigingen, controles en eventuele openstaande punten.

Codex maakt alleen een commit of push als je daar uitdrukkelijk om vraagt. De projectgenerator initialiseert zelf geen Git-repository en maakt geen GitHub-repository aan.

## Een Python-project genereren

Open een terminal in de hoofdmap van deze studio en voer uit:

```text
python create_project.py mijn-notities --type python
```

Deze generator gebruikt op deze branch standaard `C:\App\Codex\Projects`.
Gebruik `--output` om de bovenliggende map expliciet te kiezen. De package heet
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

Dit voorbeeld gebruikt de uitvoermap `./projecten` van hierboven. Bij de
standaarduitvoer ga je eerst naar `C:\App\Codex\Projects\mijn-notities`.
Lees de gegenereerde README voor het starten van de app. De meegeleverde workflow
kan op GitHub testen zodra dit project de hoofdmap van een repository vormt;
het uitvoeren van de generator publiceert niets.

## Lokale templateversies vergelijken

Voer vanuit de studiohoofdmap uit:

```powershell
python -B studio.py updates
python -B studio.py updates --root "C:\App\Codex\Projects"
```

Zonder `--root` zoekt de opdracht in `Projects` onder je Windows-gebruikersmap
(`$HOME\Projects`). De tweede opdracht kiest expliciet een andere projectroot.
`-B` voorkomt dat Python bij het starten bytecodebestanden aanmaakt.

De opdracht bekijkt alleen directe projectmappen met `.codex-studio.json` en
vergelijkt hun templateversie met `templates/manifest.json` in deze studio.
Je ziet de projectnaam, het templatetype, de huidige versie, de lokale versie
en een van deze resultaten:

| Resultaat | Betekenis |
| --- | --- |
| `ACTUEEL` | Beide versies zijn gelijk. |
| `NIEUW_BESCHIKBAAR` | Lokaal staat een hogere patch- of minorversie. |
| `GROTE_WIJZIGING` | Lokaal staat een hoger majorversienummer; controleer mogelijke gevolgen voordat je handmatig bijwerkt. |
| `PROJECT_LOOPT_VOOR` | Het project heeft een hogere versie dan het lokale manifest. |
| `ONBEKEND` | Een betrouwbare vergelijking is niet mogelijk; lees de toelichting. |

Versies moeten drie getallen bevatten, bijvoorbeeld `1.10.2`. De vergelijking
is numeriek: `1.10.0` komt na `1.9.0`. Voorloopnullen, achtervoegsels zoals
`-beta` en onvolledige versies worden als ongeldig gemeld. Een expliciete JSON-waarde
`null` betekent **onbekend**; een afwezig versieveld betekent **ontbreekt**.
Deze gevallen worden niet stilzwijgend vervangen door een verzonnen versie.
Onbekende templatetypes en ongeldige metadata krijgen `ONBEKEND` met toelichting.
Mappen zonder metadata worden overgeslagen en geteld; de scan zoekt niet verder
in hun onderliggende mappen.

Deze controle wijzigt geen projecten of metadata, installeert niets, start geen
projectcode of Git en doet geen netwerkverzoeken. Het is een vergelijking met
het lokale manifest, geen controle van online releases en geen automatische
migratie. De aanwezigheid van een template in het manifest bewijst niet dat de
bijbehorende templatebestanden aanwezig of compleet zijn; gebruik daarvoor
`check`. Symlinks en Windows-junctions worden geweigerd, ook binnen de root.
Gebruik een projectroot die je zelf beheert; gelijktijdige wijzigingen door
andere processen zijn niet ondersteund.

De afsluitcode is `0` bij een volledige controle, ook als een update beschikbaar
is of een projectversie expliciet onbekend is. Ontbrekende of ongeldige vereiste
gegevens, een onveilig pad of een onvolledige scan geven `1`. Annuleren met
`Ctrl+C` tijdens de controle geeft `130`. In PowerShell kun je de afsluitcode
bekijken met `$LASTEXITCODE`.

## De studio testen

Voer vanuit de studiohoofdmap de generator-tests uit:

```text
python -m unittest discover -s tests -v
```

De tests gebruiken tijdelijke mappen, controleren veiligheidsgevallen en testen
ook een volledig gegenereerd project. Ze schrijven niet naar je echte
`Projects`-map. Symlink-tests worden overgeslagen als het systeem geen koppelingen
toestaat. Test daarna ook het oorspronkelijke template:

```text
cd templates/python-app
python -m unittest discover -s tests -v
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

## Logging en JSON

De studio schrijft centrale logmeldingen naar stderr en maakt standaard geen
logbestanden. Resultaten blijven op stdout, zodat bijvoorbeeld
`python -B .\studio.py quality --format json` geldige JSON oplevert.
Voeg stderr niet samen met stdout als je de JSON automatisch verwerkt.
Fouten krijgen een vaste gebeurteniscode zonder ruwe exceptiontekst of
gevoelige invoer. Lees de [beveiligingsafspraken](docs/SECURITY.md) en
de [uitleg over rapportuitvoer](docs/QUALITY.md) voor voorbeelden en beperkingen.

## Waarvoor vraagt Codex toestemming?

Codex vraagt vooraf toestemming voor installaties en voor opdrachten die gegevens kunnen verwijderen of overschrijven. Het verzoek legt uit wat er gaat veranderen en wat de gevolgen zijn. Een al expliciet toegestane handeling hoeft niet opnieuw te worden goedgekeurd zolang die hetzelfde blijft.

Een test controleert of software zich gedraagt zoals bedoeld. Tests geven vertrouwen, maar sluiten niet alle fouten uit. Codex vermeldt daarom ook welke controles niet zijn uitgevoerd. Jij kunt de wijzigingen bekijken voordat je besluit ze vast te leggen of te delen.
