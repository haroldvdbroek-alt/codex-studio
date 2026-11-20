# Quality handmatig voorbereiden voor Windows Taakplanner

De studio maakt **geen geplande taak** aan. Het script
[`scripts/run-quality.ps1`](../scripts/run-quality.ps1) voert alleen een controle
uit wanneer jij het handmatig start of later zelf een taak in Windows Taakplanner
aanmaakt. Downloaden, openen of opslaan van deze bestanden plant niets in.

Het script start uitsluitend `quality --format json --output ...`, zonder
`--run-tests`. Het maakt geen back-up, doet geen herstel, installeert niets,
publiceert niets en registreert geen taak. De controle is alleen-lezen;
het expliciet gevraagde rapport is de enige schrijfactie.

## 1. Kies Python en een rapportmap

Gebruik Python 3.11 of hoger, met het volledige pad naar de echte `python.exe`.
Een leescontrole in PowerShell is:

```powershell
Get-Command python | Select-Object -ExpandProperty Source
```

Controleer dat dit jouw vertrouwde installatie is, niet een WindowsApps-alias,
symlink, junction of `pythonw.exe`. Onderstaande voorbeelden gebruiken
`C:\App\Software\Python\python.exe` en de studio op
`C:\App\Codex\Projects\codex-studio`. Pas de paden aan als jouw installatie
elders staat. Houd het script onder `scripts` in de studio; de studiomap wordt
vanaf die locatie bepaald, niet vanaf de huidige terminalmap.

Kies een bestaande lokale rapportmap buiten de broncode en buiten gevoelige
administratie zoals `.git`, `.ssh` en `.aws`. Het script maakt geen mappen aan.
Wil je een nieuwe map en bestaat deze nog niet, maak die dan bewust zelf:

```powershell
New-Item -ItemType Directory -Path "C:\App\Codex\QualityReports"
```

Een bestaande map hoef je niet opnieuw te maken. Gebruik geen `-Force` om
onverwachte bestaande bestanden weg te werken. Controleer de rapportmap en de
toegangsrechten; rapporten zijn niet versleuteld en kunnen relatieve
bestandsnamen bevatten. Gebruik geen netwerkpad of automatisch gesynchroniseerde
map als je uitsluitend lokaal wilt werken.

## 2. Controleer de uitvoerpolicy en test handmatig

Lees eerst het script en de [quality-handleiding](QUALITY.md). Bekijk eventueel
het geldende PowerShell-beleid:

```powershell
Get-ExecutionPolicy
Get-ExecutionPolicy -List
```

Als het beleid het script blokkeert, verander het niet automatisch en voeg
geen `-ExecutionPolicy Bypass` toe. Gebruik een door jou of je organisatie
goedgekeurde aanpak, bijvoorbeeld een correct ondertekend script. Vraag bij
beheerde apparaten de beheerder om advies. Deze handleiding wijzigt geen
uitvoerpolicy en verwijdert geen beveiligingsmarkeringen van bestanden.

Voer pas daarna handmatig uit, vanuit een gewone PowerShell-terminal:

```powershell
powershell.exe -NoProfile -NonInteractive -File "C:\App\Codex\Projects\codex-studio\scripts\run-quality.ps1" -PythonPath "C:\App\Software\Python\python.exe" -ReportDirectory "C:\App\Codex\QualityReports"
$LASTEXITCODE
```

Het script gebruikt vaste native argumenten, negeert Python-omgevingsvariabelen,
laadt geen Python-site/startuphooks en voorkomt bytecodecaches. Het vraagt nooit
om testtoestemming: tests worden niet gestart. Er is geen instelling om in dit
script toch tests, willekeurige opdrachten of andere projecten uit te voeren.

Elke uitvoering kiest een nieuwe JSON-naam met UTC-tijd en een willekeurig ID,
bijvoorbeeld `quality-20261119T090000000Z-....json`. De Python-rapportfunctie
controleert de bestemming en voorkomt overschrijven. De rapportinhoud staat
ook op stdout; de melding over bewaren gaat naar stderr. Het script controleert
vervolgens of het verwachte rapport aanwezig is en `tests_requested` op `false`
staat. De machineleesbare bestandsinhoud is betrouwbaarder te verwerken dan
consolekleuren of de samengevoegde stdout/stderr-weergave.

Controleer de resultaten voordat je verdergaat. Een quality-rapport kan WARN
tonen voor geplande templates of een gewijzigde Git-werkmap; dat is niet
hetzelfde als een mislukte controle. Een groene taakstatus betekent evenmin
dat alle projecttests geslaagd zijn: die zijn hier bewust niet uitgevoerd.

## 3. Maak de taak uitsluitend zelf in de interface

Doe dit alleen wanneer je bewust besluit de controle terugkerend te starten.
Codex voert deze stappen niet voor je uit.

1. Open **Windows Taakplanner** vanuit het Startmenu.
2. Kies **Taak maken** en geef een herkenbare naam, bijvoorbeeld
   `Codex Studio - Quality`.
3. Kies op **Algemeen** je eigen gebruikersaccount. Begin met **Alleen uitvoeren
   als gebruiker is aangemeld** en laat **Met meeste bevoegdheden uitvoeren**
   uitgevinkt. De controle heeft geen administratorrechten nodig.
4. Voeg op **Triggers** zelf het gewenste tijdstip of de gewenste herhaling toe.
   Deze handleiding kiest of activeert geen schema voor je.
5. Voeg op **Acties** een actie **Programma starten** toe met onderstaande velden.
6. Kies bij **Instellingen**, voor een al actieve taak: **Geen nieuw exemplaar
   starten**. Stel desgewenst een limiet van bijvoorbeeld vijf minuten in om een
   vastgelopen uitvoering te stoppen. Dit kan een tijdelijk `.incomplete`-rapport
   achterlaten; dat is geen voltooid rapport.
7. Controleer de instellingen, voorwaarden en toegang tot de rapportmap. Pas
   wanneer jij de taak opslaat, bestaat de planning.

Gebruik voor deze voorbeeldinstallatie:

| Veld | Waarde |
| --- | --- |
| Programma/script | `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` |
| Argumenten toevoegen | `-NoProfile -NonInteractive -File "C:\App\Codex\Projects\codex-studio\scripts\run-quality.ps1" -PythonPath "C:\App\Software\Python\python.exe" -ReportDirectory "C:\App\Codex\QualityReports"` |
| Beginnen in | `C:\App\Codex\Projects\codex-studio` |

Vul het veld **Beginnen in** zonder omringende aanhalingstekens in. Paden in
de argumenten blijven wel tussen aanhalingstekens staan, zeker bij spaties.
Gebruik het echte Windows-installatiepad als Windows niet onder `C:\Windows`
staat. Voeg geen PowerShell-commandotekst, beleidsomzeiling, wachtwoorden,
API-sleutels of shell-omleiding toe aan de actie.

## 4. Controleer, pauzeer en beëindig zelf

Selecteer de opgeslagen taak en kies **Uitvoeren** voor een bewuste proef.
Bekijk daarna het nieuwe rapport en **Resultaat laatste uitvoering**. Je kunt
de taakgeschiedenis desgewenst zelf inschakelen om starts en stops te bekijken;
het script maakt geen aparte logbestanden.

| Code | Gewone weergave in Taakplanner | Betekenis |
| --- | --- | --- |
| `0` | `0x0` | Geen FAIL in quality; WARN/SKIP blijft mogelijk. |
| `1` | `0x1` | Quality heeft FAIL gemeld; lees het rapport. |
| `2` | `0x2` | Ongeldige CLI-opties bij de Python-opdracht. |
| `3` | `0x3` | Scriptconfiguratie, rapportpad, rapportcontrole of opslaan mislukt. |
| `130` | `0x82` | Onderbreking die Python als Ctrl+C heeft afgehandeld. |

Een fout vóór het script start, bijvoorbeeld geblokkeerde uitvoerpolicy of
een verkeerd PowerShell-pad, kan een andere Windows-/PowerShell-code opleveren.
Taakplanner **Beëindigen**, geforceerd stoppen en sessie-/computerafsluiting
hoeven geen Python-exitcode 130 te geven. Gebruik dan ook de taakgeschiedenis
en controleer of een volledig nieuw rapport aanwezig is.

Kies **Uitschakelen** om volgende starts te voorkomen. Dat verwijdert geen
rapporten. Een reeds draaiende uitvoering moet je zo nodig apart beëindigen.
Taak of rapporten verwijderen doe je alleen zelf na controle; het script
verwijdert geen oude rapporten en heeft geen bewaartermijn. Let dus op
schijfruimte als je vaak laat controleren.

## Problemen oplossen

- **Geen rapport:** test dezelfde opdracht handmatig onder hetzelfde account.
  Controleer echte Python, uitvoerpolicy, bestaande rapportmap en schrijfrechten.
- **Exitcode 3:** controleer beide parameters en het JSON-rapport indien aanwezig.
  Ook een ongeldige Python-versie kan verhinderen dat het verwachte rapport ontstaat.
- **Git niet vertrouwd/onleesbaar:** gebruik dezelfde gebruiker die de studio
  beheert en controleer de bestaande Git-configuratie. Het script wijzigt geen
  `safe.directory` of andere Git-instellingen.
- **Taak blijft draaien:** kijk of je zelf de ingestelde tijdslimiet wilt laten
  ingrijpen. OS-bestandstoegang is niet overal hard onderbreekbaar. Installeer
  niet automatisch extra hulpmiddelen als oplossing.
- **Meerdere rapporten:** dat is normaal, elke uitvoering krijgt een nieuwe naam.
  Er wordt niets samengevoegd of overschreven.

Gebruik alleen vertrouwde lokale mappen zonder gelijktijdige padwijzigingen.
Dit script is geen sandbox tegen andere processen onder jouw account en geen
vervanging voor de [projectchecklist](PROJECT_CHECKLIST.md). Verdere grenzen
staan bij [quality](QUALITY.md) en [beveiliging](SECURITY.md).
