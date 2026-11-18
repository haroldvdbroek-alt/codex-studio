# Problemen oplossen

Lees foutmeldingen van boven naar beneden en controleer eerst de huidige map.
Installeer of verwijder niet op goed geluk iets om een melding te laten verdwijnen.

## Python of Git wordt niet herkend

Controleer in PowerShell:

```powershell
Get-Command python -ErrorAction SilentlyContinue
python --version
Get-Command py -ErrorAction SilentlyContinue
Get-Command git -ErrorAction SilentlyContinue
```

Werkt `py` maar `python` niet, controleer dan `py -3 --version`. Als dit Python
3.11 of hoger oplevert, kun je in de voorbeelden `python` vervangen door `py -3`.
Opent `python` alleen een winkelvenster of ontbreekt een geschikte versie,
bespreek dan eerst installatie of configuratie. Een ontbrekende VS Code-extensie
verhindert het uitvoeren van de terminalopdrachten niet.

## Het script of de tests worden niet gevonden

```powershell
Get-Location
Get-ChildItem -Force
```

Voor de generator moet de huidige map `create_project.py` bevatten. Voor de
projecttests moet de huidige map `tests` bevatten, plus `pyproject.toml` voor
Python/AI/automation of `public` voor web.
Open de juiste map in VS Code en een nieuwe PowerShell-terminal.
`Ran 0 tests` is geen bewijs dat het project werkt; controleer de gekozen testmap.

## De doelmap bestaat al

De generator overschrijft nooit een bestaand doel, ook geen lege map. Bekijk
bijvoorbeeld:

```powershell
Test-Path -LiteralPath "$HOME\Projects\mijn-notities"
Get-ChildItem -LiteralPath "$HOME\Projects\mijn-notities" -Force
```

Gebruik het bestaande project als dat de bedoeling was, of kies een nieuwe
projectnaam. Verwijder de map niet zonder eerst de inhoud en gevolgen te controleren.

## Het project staat op een onverwachte plek

De huidige code gebruikt zonder `--output` het vaste pad `C:/App/Codex/Projects`.
Helptekst en menu tonen die werkelijke standaard. De tests gebruiken een tijdelijk ingestelde doelmap; de standaard zelf is niet veranderd.
Gebruik vanuit de studio bijvoorbeeld:

```powershell
python .\create_project.py mijn-notities --type python --output "$HOME\Projects"
```

Een relatief uitvoerpad is relatief aan de huidige terminalmap, niet aan het
script. De generator print het volledige aangemaakte projectpad.

## Ongeldige naam of onbekend type

Gebruik bijvoorbeeld `mijn-notities`, geen pad of naam met spaties. De
packagenaam wordt `mijn_notities`, maar de projectnaam op de commandoregel houdt
het koppelteken. `--type python`, `--type web`, `--type ai` en `--type automation` werken.
Zie de volledige naamregels in [templates](TEMPLATES.md).

## `No module named mijn_notities`

Voor het starten van de app moet je vanuit de projectmap eerst naar `src`:

```powershell
Set-Location .\src
python -m mijn_notities
Set-Location ..
```

Voor de tests blijf je juist in de projecthoofdmap en gebruik je discovery.
Voeg bij nieuwe testmodules de bestaande voorbereiding van `sys.path` toe vóór
imports van de package. Installeer de package niet als omweg. De Python-optie
`-I` haalt de huidige map uit het gewone modulezoekpad en is daarom niet geschikt
voor bovenstaande app-opdracht; de tests maken hun bronpad zelf beschikbaar.

## Tests geven `FAIL`, `ERROR` of `skipped`

Lees de testnaam en de onderste foutmelding. `FAIL` duidt op een niet-gehaalde
verwachting; `ERROR` op een fout tijdens uitvoeren. Deel bij hulpvragen alleen
de relevante melding, zonder secrets of onnodige persoonlijke paden.

De oude standaardmap-test is vervangen door een controle met een tijdelijk
ingestelde doelmap. De generatorstandaard zelf is niet veranderd. Je hoeft geen
test meer uit te sluiten. Voer vanuit de studiohoofdmap de volledige controle uit:

```powershell
python -B run_tests.py
```

De opdracht meldt een fout als Node.js ontbreekt of een suite mislukt. Echte
symlink-tests kunnen op Windows nog `skipped` tonen als koppelingen niet zijn
toegestaan. Controleer daarom ook de Linux-resultaten van GitHub Actions.
Verander geen beveiligingsinstellingen alleen om een test groen te krijgen.

De oorspronkelijke app kun je onafhankelijk controleren. Start vanuit de
studiohoofdmap:

```powershell
Push-Location .\templates\python-app
python -m unittest discover -s tests -v
Pop-Location
```

## Symbolische koppeling, toegang geweigerd of onvolledig project

Gebruik een rechtstreeks pad zonder symlinks of junctions, ook in bovenliggende
mappen. Kies een uitvoermap waarin je normale gebruiker mag schrijven; start
niet meteen als administrator. Bij een schrijffout kan een gedeeltelijke
projectmap achterblijven. Bekijk het gemelde pad en vraag hulp voordat je opruimt.

## GitHub Actions start niet

Controleer of `.github/workflows/python-tests.yml` echt in de hoofdmap van de
GitHub-repository staat. Voor web heet dit bestand `web-tests.yml`. Onder een
templatemap in de studio wordt de workflow niet
ontdekt. Bekijk na een bewuste push of pull request het tabblad **Actions**;
controleer ook of Actions voor de repository is toegestaan. Lokale tests blijven
zonder GitHub werken. Een fout op GitHub moet afzonderlijk worden onderzocht;
een lokale `OK` bewijst niet dat iedere workflowversie slaagt.

## Webtests of de teller werken niet

Controleer `node --version`: de JavaScript-tests vereisen Node.js 22 of hoger.
Er is geen `npm install` nodig. Voer vanuit de webprojectmap zowel
`node --test tests/counter.test.cjs` als de Python-unittest-opdracht uit.
Een ontbrekende Node-opdracht betekent dat de JavaScript-controle niet is gedaan.

Open de pagina onder `public` en zorg dat JavaScript in de browser is toegestaan.
Controleer of `app.js` en `styles.css` naast `index.html` staan. Bij lokaal serveren
gebruik je `python -m http.server 8000 --bind 127.0.0.1 --directory public` vanuit
de webprojectmap. Is poort 8000 bezet, kies 8001 en bezoek dezelfde poort in de URL.
De teller begint na vernieuwen bewust opnieuw bij nul.

## AI-configuratie of demo geeft een fout

Het AI-template ondersteunt alleen `AI_MODE=mock`. Een echte API-sleutel instellen
activeert geen provider. `AI_MODEL` mag niet leeg zijn. Controleer de modus en
modelnaam zonder de API-sleutel af te drukken:

```powershell
Get-Item Env:AI_MODE -ErrorAction SilentlyContinue
Get-Item Env:AI_MODEL -ErrorAction SilentlyContinue
```

Een `.env` of `.env.example` wordt niet automatisch geladen; de app gebruikt
procesomgevingsvariabelen. De tests geven hun eigen fictieve configuratie door,
dus ze horen ook zonder sleutel te slagen. Netwerkfouten met de tekst
`Netwerk verboden in tests` betekenen dat een test code probeert uit te voeren
die niet offline is; haal die API-aanroep uit de test in plaats van echte
sleutels toe te voegen. Zie [het AI-template](../templates/ai-app/README.md).

## Automation schrijft niets of weigert het doel

Zonder `--apply` is dit de bedoeling: dry-run toont alleen het plan. Een lege
bron maakt ook bij uitvoeren geen doelmap aan. Alleen directe `.txt`-bestanden
worden verwerkt, geen submappen. De hele doelmap moet nieuw zijn; ook een lege
bestaande map wordt geweigerd. Kies voor een nieuwe uitvoering een nieuwe doelmap.

Gebruik geldige UTF-8-tekst en een bron en doel die niet in elkaar liggen.
Bij een schrijffout kan een gedeeltelijk nieuw doel achterblijven; bekijk dat
voordat je opruimt. De opdracht is geen transactionele batch en ondersteunt geen
gelijktijdige padwijzigingen. Zie [de automation-handleiding](../templates/automation/README.md).

Ga terug naar [beginnen](GETTING_STARTED.md) of [de hoofdhandleiding](../README.md).
