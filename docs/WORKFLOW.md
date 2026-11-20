# Werken aan een project met Codex Studio

Deze handleiding is voor Windows, VS Code en PowerShell. Gebruik bij iedere
taak de [projectchecklist](PROJECT_CHECKLIST.md). De afspraken uit
[AGENTS.md](../AGENTS.md) blijven gelden.

## 1. Kies het juiste project

Gebruik vanuit de studio `python .\studio.py menu --root "C:\App\Codex\Projects"`
voor een interactief overzicht van bestaande functies. Lees [MENU.md](MENU.md)
voor bevestigingen en annuleren; tests, herstel en schrijfacties worden nooit
automatisch bevestigd. Directe CLI-opdrachten blijven beschikbaar.

Open in VS Code de projectmap via **Bestand > Map openen**. Open daarna een
PowerShell-terminal via **Terminal > Nieuwe terminal**. Controleer waar je bent:

```powershell
Get-Location
Get-ChildItem -Force
python --version
git --version
```

Python-code in deze studio gebruikt Python 3.11 of hoger. Ontbreekt een
hulpmiddel, bespreek de installatie eerst. Activeer geen scripts en voer geen
code van een onbekend project uit voordat je het hebt onderzocht.

Lees de project-README en `AGENTS.md`, eventuele aanvullende instructies en
relevante tests. Onderzoek welke bestanden en gegevens de taak raakt. De
voorbeeldpaden hieronder gebruik je alleen als die op jouw computer bestaan.

## 2. Houd rekening met het projecttype

| Type | Beschikbaar op deze branch | Aandachtspunten |
| --- | --- | --- |
| Python | Template en generator werken. | `src`-layout, absolute imports en unittest-tests zonder pakketinstallatie. |
| Web | Template en generator werken. | Lokale HTML/CSS/JavaScript, veilige tekstweergave, toetsenbordbediening en browsertest. |
| AI | Offline-template en generator werken. | Configuratie via omgevingsvariabelen; tests met mocks of een nepclient, zonder echte sleutel of API-aanroep. |
| Automation | Template en generator werken. | Logging zonder gevoelige inhoud, veilige testmodus en bestandsbewerkingen in tijdelijke mappen. |

Voor bestaande web-, AI- en automation-projecten geldt deze werkwijze ook,
maar hun eigen README en aanwezige code bepalen de werkende startopdracht.
De generator ondersteunt `--type python`, `--type web`, `--type ai` en
`--type automation`. Zonder argumenten opent een menu; pas na bevestiging
wordt een nieuw project gemaakt. De standaardoudermap is `$HOME\Projects`.

Een nieuw Python-project kun je vanuit de studiohoofdmap maken met:

```powershell
python .\create_project.py mijn-notities --type python --output "C:\App\Codex\Projects"
```

Gebruik een nieuwe naam: bestaande doelmappen worden geweigerd. `--output`
maakt de keuze expliciet. De generator op deze branch gebruikt zonder die optie
`C:\App\Codex\Projects`, terwijl de studio-opdrachten standaard in
`$HOME\Projects` zoeken. De generator maakt momenteel geen `.codex-studio.json`;
een nieuw project verschijnt daardoor niet automatisch in de studio-overzichten.
Registreer metadata alleen bewust, met een onderzocht type en eerlijke versies.

## 3. Begin met een kleine opdracht en een branch

Beschrijf het gewenste gedrag, wat behouden moet blijven en hoe je succes
herkent. Een bruikbare opdracht aan Codex is:

> Lees eerst de instructies, README en relevante code. Onderzoek hoe deze taak
> past in het project. Stel bij groter werk een kort plan voor. Maak kleine
> wijzigingen en passende tests. Vraag toestemming voor installaties en
> destructieve opdrachten. Maak geen commit of push zonder mijn opdracht.

Controleer bij een Git-project eerst:

```powershell
git status
git branch --show-current
```

Bewaar bestaand werk; gebruik geen `reset --hard`, `clean -fd` of geforceerde
checkout om een melding op te lossen. Maak vanuit de afgesproken basis een
taakbranch, als er nog geen passende branch is:

```powershell
git switch -c feature/mijn-wijziging
```

Een branch is een eigen werklijn. Is de naam al in gebruik, onderzoek die branch
eerst. Zonder Git-repository kun je wel ontwikkelen en testen; initialiseert
Codex Git of GitHub, dan is daarvoor eerst toestemming nodig.

## 4. Wijzig en test in kleine stappen

Voeg een afgebakend stuk gedrag toe, schrijf een passende test en voer die uit.
Gebruik fictieve gegevens. Test normale invoer, ongeldige invoer en relevante
foutgevallen. Tests voeren projectcode uit en kunnen bestanden wijzigen; voer
ze alleen uit voor een project dat je vertrouwt.

Voor projecten met de gedocumenteerde unittest-tests voer je vanuit de
projecthoofdmap uit:

```powershell
python -B -m unittest discover -s tests -v
$LASTEXITCODE
```

`unittest` is meegeleverd met Python. Discovery zoekt testmodules in `tests`.
`-v` toont iedere test; `-B` voorkomt Python-bytecodecachebestanden, maar maakt
tests niet alleen-lezen. Exitcode `0` betekent succes; lees ook eventuele
`skipped`-meldingen. `FAILED`, `ERROR` of een andere exitcode vraagt onderzoek.
Nul gevonden tests is geen bewijs dat de app werkt.

Bij een `src`-layout maken de tests het eigen `src`-pad beschikbaar vóór de
absolute package-imports. Neem daarvoor de aanpak uit bestaande testmodules
over; installeer niet automatisch een pakket om een importfout te verbergen.

| Type | Aanvullende controle |
| --- | --- |
| Python | Test functies, invoervalidatie en het startpunt. Lees de README voor de eigen packagenaam. |
| Web | Als `tests/counter.test.cjs` aanwezig is: `node --test tests/counter.test.cjs`. Node moet vooraf beschikbaar zijn. Controleer daarnaast `public/index.html` handmatig in een browser, inclusief toetsenbord en foutmeldingen. |
| AI | Controleer dat de tests echte clients vervangen door mocks/nepclients en zonder echte API-sleutel slagen. Een unittest-opdracht alleen garandeert geen offline tests. |
| Automation | Gebruik tijdelijke bron- en doelmappen. Test dat de veilige modus niets wijzigt, bestaande doelen behouden blijven en fouten netjes worden gelogd. Gebruik alleen de testmodus/startvlag die de eigen README daadwerkelijk beschrijft. |

Voor AI en automation staan werkende startinstructies in hun eigen README.
De AI-demo gebruikt alleen een offline nepclient. Automation heeft standaard
dry-run; `--apply` vraagt echte uitvoer naar een nieuwe doelmap aan. Lees eerst
de [AI-handleiding](../templates/ai-app/README.md) of
[automation-handleiding](../templates/automation/README.md). Pas echte
bestandsbewerkingen pas toe nadat invoer, doel en gevolgen duidelijk zijn
en de gebruiker de schrijfactie heeft toegestaan.

## 5. Controleer via de studio

Voer de volgende opdrachten uit vanuit de studiohoofdmap. Het voorbeeldproject
moet rechtstreeks onder de opgegeven root staan en geldige metadata hebben:

```powershell
python -B .\studio.py list --root "C:\App\Codex\Projects"
python -B .\studio.py check mijn-notities --root "C:\App\Codex\Projects"
python -B .\studio.py updates --root "C:\App\Codex\Projects"
```

`check` controleert metadata, vereiste configuratie en lokale Git-status.
Zonder `--run-tests` voert het geen projecttests uit. `PASS` geldt alleen voor
de genoemde controle; `WARN` vraagt aandacht, `FAIL` is een mislukte controle en
`SKIP` betekent niet uitgevoerd. Geen eigen Git-repository geeft een waarschuwing.

Wil je de vaste toegestane testopdracht laten starten, gebruik dan expliciet:

```powershell
python -B .\studio.py check mijn-notities --root "C:\App\Codex\Projects" --run-tests
```

Lees eerst de waarschuwing en opdrachten. Alleen `ja` bevestigt; Enter of `nee`
annuleert. Deze toestemming geldt voor projectcode, niet voor installaties.
De policy ondersteunt de vier types bij versie `1.0.0`, maar kan uitvoering
weigeren bij ontbrekende configuratie, onbekende versies of onveilige paden.
Verzin geen versienummer om die controle te omzeilen.

`updates` vergelijkt alleen met het lokale manifest. `ACTUEEL` bewijst niet dat
tests slagen of dat de templatebron aanwezig is. Administratief op `1.0.0`
gezette metadata bewijst geen oorspronkelijke versie of compatibiliteit.

Je kunt ook het alleen-lezen dashboard starten:

```powershell
python .\studio.py dashboard --root "C:\App\Codex\Projects"
```

Open het getoonde `127.0.0.1`-adres. Tests blijven `NIET_UITGEVOERD`.
Stop in PowerShell met `Ctrl+C`. Lees de [beveiligingsuitleg](SECURITY.md)
voor limieten, netwerkpaden en veilig lokaal gebruik.

## 6. Bekijk het resultaat voordat je iets vastlegt

Werk je aan de studio zelf, voer dan vanuit de studiohoofdmap
`python -B .\studio.py quality` uit. Voor de vaste studio-testsuite gebruik je
`python -B .\studio.py quality --run-tests` en bevestig je na de waarschuwing
met `ja`. Quality controleert de studio, niet automatisch je andere projecten.
Lees [quality gebruiken](QUALITY.md) voor wat wel en niet gecontroleerd wordt.
Voor overdracht kun je `--format json` of `--format markdown` kiezen en met
`--output` expliciet een nieuw rapportbestand bewaren. Controleer de exitcode;
bij exitcode 3 is de rapportage niet veilig afgerond. Bewaar geen rapport over
een bestaand bestand heen en behandel een overgeslagen test niet als geslaagd.
Voor eventuele herhaling is er een [PowerShell-script met handleiding](TASK_SCHEDULER.md).
Test het eerst handmatig; alleen jij maakt daarna desgewenst de Windows-taak aan.

Ga voor Git-opdrachten terug naar de projectmap die je hebt gewijzigd:

```powershell
git diff --check
git diff
git status
```

Controleer ook nieuwe bestanden: die staan niet in een gewone `git diff`.
Kijk naar secrets, persoonsgegevens, onbedoelde caches, logs en lokale gegevens.
Een `.gitignore` verwijdert geen bestanden die Git al volgt. Een gelekte sleutel
moet worden ingetrokken; alleen de tekst uit de laatste versie wissen is niet genoeg.

Vul de [checklist](PROJECT_CHECKLIST.md) in. Noteer uitgevoerde opdrachten,
resultaten, overgeslagen tests en beperkingen. Bij alleen documentatie volstaan
controle van inhoud, links en voorbeelden; nieuwe programmatests zijn dan niet nodig.

## Optioneel: eerst een broncodeback-up

Lees [back-ups maken](BACKUPS.md) en bekijk eerst de selectie met
`studio.py backup`. Alleen `--create` plus de exacte interactieve bevestiging
maakt een archief. Een broncodeback-up sluit gegevens en secrets uit en vervangt
geen afzonderlijk gegevensback-upbeleid. Een back-up maken vereist eigen
toestemming; een opdracht om code te wijzigen is daarvoor niet voldoende.

Een herstelproef begint eveneens met een alleen-lezen overzicht. Volg de
[herstelhandleiding](RESTORE.md): controleer CRC en SHA-256, kies een nog niet
bestaande map en bevestig herstel afzonderlijk. Bekijk de herstelde code voordat
je tests start. Uitgesloten gegevens en Git-geschiedenis komen niet terug.

## 7. Commit, samenvoegen en publiceren blijven bewuste stappen

De onderstaande stappen zijn voor wanneer jij besluit de wijziging vast te
leggen. Codex voert ze alleen uit na een expliciete opdracht.

Selecteer in VS Code bij **Broncodebeheer** met het plusje alleen de gewenste
bestanden. Controleer vervolgens wat in de commit zal komen:

```powershell
git diff --cached
git commit -m "Beschrijf het afgeronde resultaat"
```

Een commit bewaart de geselecteerde wijzigingen lokaal. Controleer daarna
`git status`. Alleen als de werkmap schoon is en de afgesproken basis `main` is,
kun je de taakbranch samenvoegen:

```powershell
git switch main
git merge feature/mijn-wijziging
```

Los eventuele conflicten bewust op en test opnieuw. Een alternatief is een
pull request op GitHub, als er al een afgesproken remote en publicatiewerkwijze
is. Een push verstuurt code naar die remote: controleer daarvoor `git remote -v`
en vraag apart toestemming wanneer Codex die actie uitvoert. Forceer geen push
en wijzig geen Git-geschiedenis zonder expliciete toestemming.

Wanneer een workflowbestand onder `.github/workflows/` in de repositoryhoofdmap
staat, kan GitHub Actions na publicatie testen. Een workflow die alleen in een
templatemap staat, test het gegenereerde project niet automatisch. Controleer
de echte Actions-uitvoer; lokale tests bewijzen geen geslaagde GitHub-run.
Publiceren, releases en installaties gebeuren niet automatisch door deze checklist.

Gebruik vóór een eventuele release de [lokale releasecontrole](RELEASE.md).
Een schone werkmap, kandidaatversie en lokale tests vervangen geen GitHub Actions,
reviews, branchbescherming of publicatietoestemming. Het rapport laat die controles
expliciet open en publiceert nooit zelf iets.
