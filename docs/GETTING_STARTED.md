# Codex Studio: gebruikershandleiding in tien stappen

Deze handleiding is voor een beginnende ontwikkelaar met Windows, VS Code,
PowerShell, Python, Codex en GitHub. Ze beschrijft aanwezige functies; de
gekoppelde gidsen geven verdieping. Voer opdrachten regel voor regel uit.
Kopieer geen eventuele `PS ...>`-prompt mee.

De voorbeelden gebruiken onderstaande mappen. Pas deze paden aan als jouw
studio elders staat. Verander de bestaande PowerShell-variabele `$HOME` niet.

```powershell
$studioRoot = "C:\App\Codex\Projects\codex-studio"
$projectRoot = "C:\App\Codex\Projects"
$backupRoot = "C:\App\Codex\Projects\StudioBackups"
```

Deze variabelen gelden voor deze terminal; stel ze opnieuw in bij een nieuwe
terminal. Een voorbeeld met een schrijfactie voer je alleen uit als je die
actie bewust wilt. Paden met spaties zet je tussen aanhalingstekens.

## 1. De omgeving openen en controleren

Open in VS Code **Bestand > Map openen** en kies de studiomap. Open een
PowerShell-terminal en controleer de locatie en aanwezige hulpmiddelen:

```powershell
Set-Location -LiteralPath $studioRoot
Get-Location
Test-Path .\studio.py
python --version
git --version
node --version
```

Python 3.11+ is vereist. Node.js 22+ is nodig voor JavaScript-tests; Git is nodig
voor versiebeheer. VS Code en Codex helpen bij lezen en wijzigen, maar zijn
geen voorwaarde om de Python-opdrachten uit te voeren. De projecten gebruiken
geen externe Python-pakketten of frameworks. Ontbreekt iets, bespreek dan eerst
installatie of configuratie. Installeer niets automatisch om een fout te omzeilen.

Lees [AGENTS.md](../AGENTS.md) en de README en eigen instructies van je project.

## 2. Het menu en de hulp gebruiken

```powershell
Set-Location -LiteralPath $studioRoot
python .\studio.py menu --root $projectRoot
```

`python .\studio.py` opent hetzelfde menu. Zonder expliciete root vraagt het
menu bij projectacties om een map; de standaard is `$HOME\Projects`. Het menu
voert ??n gekozen actie uit. Start het opnieuw voor een volgende actie.

Enter, `0` of `q` stopt het hoofdmenu. Bij vervolgvragen annuleert `q`; Enter
kiest alleen een getoonde standaardwaarde. Ctrl+C en einde invoer annuleren ook.
Het menu vult nooit toestemming voor tests, herstel of schrijven voor je in.
Een reeds bevestigde actie kan bij onderbreken wijzigingen achterlaten.
Het menu vereist een interactieve terminal; scripts gebruiken de directe CLI:

```powershell
python .\studio.py --help
python .\studio.py backup --help
python .\create_project.py --help
```

`PROJECT` in een hulpvoorbeeld betekent ??n projectmapnaam. `--root` is de
oudermap waarin projecten staan. Hoofdletters in voorbeelden zijn
plaatsaanduidingen, geen namen die je letterlijk moet overnemen.
Zie [MENU.md](MENU.md) en [problemen oplossen](TROUBLESHOOTING.md).

## 3. Een nieuw project maken

De generator maakt uitsluitend een nieuw project; de doelmap mag nog niet
bestaan, ook niet leeg. Hij initialiseert geen Git of GitHub-repository.
Kies hieronder ??n regel voor het gewenste oefenproject:

```powershell
Set-Location -LiteralPath $studioRoot
python .\create_project.py mijn-notities --type python --output $projectRoot
python .\create_project.py mijn-website --type web --output $projectRoot
python .\create_project.py mijn-ai-app --type ai --output $projectRoot
python .\create_project.py mijn-taak --type automation --output $projectRoot
```

Deze directe opdrachten schrijven na geldige invoer een nieuw project; voer
ze alleen bewust uit. `python .\create_project.py` opent het generatormenu met
vooraf een overzicht en expliciete `ja`-bevestiging. Zonder `--output` is de
standaardoudermap `$HOME\Projects`.

| Type | Werkende voorbeeldfunctie | Grens |
| --- | --- | --- |
| Python | Begroetingsapp, src-layout en unittest. | Geen pakketinstallatie nodig. |
| Web | Lokale HTML/CSS/JavaScript-pagina met teller. | Geen framework of publieke hosting. |
| AI | Offline nepclient en voorbeeldconfiguratie. | Geen AI-model, provider, echte sleutel of betaalde API-aanroep. |
| Automation | Tekstbestanden verwerken met logging en dry-run. | Schrijven vraagt expliciet `--apply`; geen automatische planning. |

De generator valideert namen, weigert koppelingen en leest alleen gedeclareerde
bestanden uit het manifest. Onbekende templateversies worden geweigerd.
Nieuwe projecten krijgen `.codex-studio.json` met herkomst- en versiegegevens.
Bestaande projecten worden niet bijgewerkt. Zie [TEMPLATES.md](TEMPLATES.md).

## 4. Projecten vinden en controleren

Vervang `mijn-notities` door de directe mapnaam van je eigen project:

```powershell
Set-Location -LiteralPath $studioRoot
python .\studio.py list --root $projectRoot
python .\studio.py check mijn-notities --root $projectRoot
python .\studio.py updates --root $projectRoot
```

`list` herkent projecten via `.codex-studio.json`. Zonder geldige metadata is
niet elke map een geregistreerd project. Maak geen metadata met verzonnen
versies; bestaande projecten worden niet automatisch geregistreerd.

`check` leest metadata, configuratie en Git-status; standaard voert het geen
projectcode of tests uit. `updates` vergelijkt de opgeslagen templateversie met
het lokale manifest en installeert niets. `ACTUEEL` bewijst geen werkende app
of compatibiliteit. Project-, template- en studioversies zijn verschillende gegevens.

PASS betekent dat de genoemde controle slaagt; WARN is een aandachtspunt,
FAIL een vastgestelde fout en SKIP een niet-uitgevoerde controle. Een ontbrekende
Git-repository kan WARN geven; initialiseert Codex Git, dan is daarvoor eerst
apart toestemming nodig. Zie [WORKFLOW.md](WORKFLOW.md).

## 5. Apps starten en tests uitvoeren

Doe dit alleen met vertrouwde code. Tests voeren code uit en kunnen bestanden
wijzigen, processen starten of netwerk gebruiken. De studio is geen sandbox.
Vanuit de projecthoofdmap werkt voor ieder template:

```powershell
Set-Location -LiteralPath "$projectRoot\mijn-notities"
python -B -m unittest discover -s tests -v
```

Kies voor web, AI of automation de eigen projectmap. `unittest` zit in Python;
`discover` zoekt testmodules en `-v` toont testnamen. `-B` voorkomt bytecodecache,
maar maakt tests niet alleen-lezen. De tests maken het eigen `src` beschikbaar,
zodat absolute package-imports zonder installatie werken. Een gegenereerd
project kan zelfstandig buiten de studio werken.

Start het Python-voorbeeld vanuit zijn src-map:

```powershell
Push-Location -LiteralPath "$projectRoot\mijn-notities\src"
try { python -m mijn_notities } finally { Pop-Location }
```

Dit toont `Hallo, Voorbeeld!`. De packagenaam gebruikt underscores. Voor het
AI-voorbeeld gebruik je `mijn-ai-app\src` en `python -m mijn_ai_app`. De
standaardmodus is `mock`; er is geen echte sleutel nodig. `.env.example` is
voorbeeldconfiguratie en wordt niet automatisch ingelezen.

Voor web, vanuit de projecthoofdmap:

```powershell
Set-Location -LiteralPath "$projectRoot\mijn-website"
node --test tests/counter.test.cjs
python -m http.server 8000 --bind 127.0.0.1 --directory public
```

Open `http://127.0.0.1:8000` en stop met Ctrl+C. Dit is uitsluitend een lokale
ontwikkelserver. Voor automation toont deze opdracht de werkelijke argumenten:

```powershell
Push-Location -LiteralPath "$projectRoot\mijn-taak\src"
try { python -m mijn_taak --help } finally { Pop-Location }
```

Volg voor een dry-run met fictieve invoer de
[automation-handleiding](../templates/automation/README.md). Gebruik `--apply`
alleen bewust na controle van bron, nieuwe doelmap en gevolgen.

De studio zelf heeft een volledige testworkflow:

```powershell
Set-Location -LiteralPath $studioRoot
python -B run_tests.py
```

Die controleert de studio, alle vier templates en JavaScript; Node.js 22+ moet
vooraf beschikbaar zijn. `OK` betekent geen mislukte tests. Lees ook `skipped`:
overgeslagen tests bewijzen niets over dat gedrag. `FAILED` met een traceback
vraagt onderzoek. Nul tests of alleen testbestanden bewijzen geen testdekking.
Zie [QUALITY.md](QUALITY.md).

## 6. Met Codex aan een wijziging werken

Open het bedoelde project in VS Code. Een bruikbare opdracht aan Codex:

> Lees eerst AGENTS.md en onderzoek dit project. Stel een plan voor een kleine
> wijziging aan de voorbeeldapp voor en leg de bijbehorende tests uit. Wacht op
> mijn goedkeuring. Installeer niets en maak geen commit of push.

Laat Codex bestaande wijzigingen behouden, op een taakbranch werken en kleine
stappen maken. Controleer de diff en uitgevoerde tests. Vraag vooraf toestemming
voor installaties en destructieve handelingen. Een algemene verbeteropdracht
is geen toestemming om gegevens te verwijderen.

Gebruik fictieve gegevens. Zet geen secrets in prompts, projectnamen, code,
metadata, logs of Git. De studio is geen volledige geheimenscanner. Gebruik de
[projectchecklist](PROJECT_CHECKLIST.md) en [SECURITY.md](SECURITY.md).

## 7. Dashboard, quality en maintenance gebruiken

```powershell
Set-Location -LiteralPath $studioRoot
python .\studio.py dashboard --root $projectRoot
```

Open het getoonde `http://127.0.0.1:poort/`-adres. De startpagina toont de
projecten, zoeken, filters en details. De browser gebruikt de laatste scan en
kan geen tests, herstel of bestandswijzigingen starten. Tests blijven
`NIET_UITGEVOERD`. Lees meldingen bij onvolledige scans. Stop de server met
Ctrl+C; herstart hem na gewijzigde frontendbestanden.

```powershell
python .\studio.py quality
python .\studio.py maintenance
```

Deze controleren de studio zelf, standaard alleen-lezen. Maintenance scheidt
vaststellingen van aanbevelingen en stelt geen testdekking vast uit bestanden.
Quality kan apart met `--run-tests` om toestemming vragen; mislukte
voorcontroles kunnen een optionele teststart blokkeren.

Voor JSON in PowerShell:

```powershell
$qualityJson = python .\studio.py quality --format json
$qualityExit = $LASTEXITCODE
$qualityReport = $qualityJson | ConvertFrom-Json
$qualityReport.summary
$qualityExit
```

Logging staat op stderr; voeg dit niet met `2>&1` samen met JSON op stdout.
Er ontstaan standaard geen log- of rapportbestanden. Alleen expliciet
`--output` bij een rapportopdracht vraagt een nieuw bestand aan; bestaande
bestanden worden geweigerd. Invoerfouten geven exitcode 2 en geen JSON.
Lees de opdrachten-specifieke codes in [QUALITY.md](QUALITY.md) en
[MAINTENANCE.md](MAINTENANCE.md).

Een benchmark is optioneel: `python .\studio.py benchmark` maakt en verwijdert
eigen fictieve tijdelijke bestanden. Start die alleen bewust of bevestig de
menuvraag. Zie [BENCHMARK.md](BENCHMARK.md). Voor handmatige planning van een
quality-controle bestaat [TASK_SCHEDULER.md](TASK_SCHEDULER.md); er wordt nooit
zelfstandig een Windows-taak aangemaakt of uitvoerbeleid aangepast.

## 8. Eerst een back-upoverzicht, daarna bewust aanmaken

```powershell
Set-Location -LiteralPath $studioRoot
python .\studio.py backup mijn-notities --root $projectRoot --output $backupRoot
```

Dit toont selectie en bestemming; het schrijft niets. De bestemmingsoptie
heet `--output`, niet `--destination`. Controleer opgenomen en uitgesloten
bestanden. Gevoelige namen, `.env`, gegevensmappen, Git en caches worden
standaard uitgesloten; niet alle secrets zijn herkenbaar. De ZIP is niet
versleuteld en is geen volledige gegevensback-up.

Alleen als je de selectie echt wilt bewaren:

```powershell
python .\studio.py backup mijn-notities --root $projectRoot --output $backupRoot --create
```

Bekijk het nieuwe overzicht en typ bij de vraag exact `BACKUP mijn-notities`.
De ouder van de back-upmap moet bestaan; de back-upmap zelf mag na toestemming
worden aangemaakt. Zonder bevestiging ontstaat niets. Een `.incomplete`-bestand
is geen geslaagde back-up. Zie [BACKUPS.md](BACKUPS.md).

## 9. Controleren en uitsluitend naar een nieuwe map herstellen

Kies zelf de werkelijke ZIP; selecteer niet automatisch het nieuwste bestand:

```powershell
Set-Location -LiteralPath $studioRoot
Get-ChildItem -LiteralPath $backupRoot -Filter "*.zip"
$archivePath = Read-Host "Volledig pad van de gewenste ZIP, zonder extra aanhalingstekens"
python .\studio.py restore $archivePath --output "$projectRoot\mijn-notities-herstel"
```

Dit controleert structuur en controlesommen zonder herstel. SHA-256 controleert
of inhoud overeenkomt met het manifest, niet wie de afzender is. Vertrouw de bron
voordat je herstelde code uitvoert. Uitgesloten gegevens en secrets komen niet terug.

Alleen voor bewust herstel, naar een doelmap die nog niet bestaat:

```powershell
python .\studio.py restore $archivePath --output "$projectRoot\mijn-notities-herstel" --create
```

Typ na controle exact `HERSTEL mijn-notities-herstel`. Ook een bestaande lege
doelmap wordt geweigerd; de oudermap moet bestaan. Herstel start geen tests en
wijzigt geen bestaand project. Onderbreken kan een onvolledige nieuwe map
achterlaten; niets wordt automatisch verwijderd. Test alleen vertrouwde
herstelde code. Zie [RESTORE.md](RESTORE.md).

## 10. Git, een Pull Request en een handmatige release

Werk in de juiste bestaande repository en bekijk eerst de status:

```powershell
Set-Location -LiteralPath $studioRoot
git status
git branch --show-current
```

Begin een passende taakbranch vanaf de afgesproken basis. Wissel niet van
branch als bestaand werk daardoor gevaar loopt. Gebruik geen geforceerde
checkout, `reset --hard` of `clean -fd` om een melding weg te werken.

```powershell
git switch -c feature/mijn-wijziging
```

Bestaat die naam al, onderzoek de branch. Review de diff en voer passende tests
uit. Alleen wanneer je bewust wilt vastleggen en delen, kun je bijvoorbeeld
deze gewijzigde handleiding selecteren:

```powershell
git add -- docs/GETTING_STARTED.md
git commit -m "Werk de gebruikershandleiding bij"
git push -u origin feature/mijn-wijziging
```

Open in GitHub een Pull Request (PR) naar `main`, ook als een andere branch de
standaard is. Wacht op geslaagde CI voor de actuele commit en eventuele vereiste
reviews. Merge zonder branchbescherming te omzeilen; controleer ook de CI op de
uiteindelijke main-commit. Zie [WORKFLOW.md](WORKFLOW.md).

Publiceren is een afzonderlijke bewuste stap. Bekijk lokale tags met
`git tag --list --sort=-v:refname` en controleer GitHub Releases voor de echte
publicatiegeschiedenis. Kies PATCH voor compatibele fixes, MINOR voor nieuwe
compatibele functies en MAJOR voor incompatibele wijzigingen. Neem niet zomaar
een groot versienummer of een bestaande tag over. Leg de gekozen kandidaat met
beoordeelde notities in de changelog vast.

```powershell
$candidateVersion = Read-Host "Bewust gekozen kandidaatversie MAJOR.MINOR.PATCH"
python .\studio.py release-check --version $candidateVersion
```

De voorcontrole publiceert nooit. Een rapport zonder FAIL laat externe
controles open en geeft geen algemene vrijgave. Verifieer commit, CI, reviews,
versie en artefacten volgens [RELEASE.md](RELEASE.md). Publiceer alleen na
expliciete toestemming volgens [RELEASING.md](RELEASING.md). Verplaats nooit
stilzwijgend een bestaande releasetag. Bestaande projecten en templateversies
worden niet automatisch bijgewerkt.
