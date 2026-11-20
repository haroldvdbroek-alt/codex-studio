# Beginnen met Codex Development Studio

Deze handleiding gebruikt Windows en PowerShell. De studio kan momenteel een
Python-, web-, offline AI- of automation-project genereren. Er is geen
installatie van projectpakketten nodig. De stappen hieronder beginnen met Python;
voor web zie ook [de webhandleiding](../templates/web-app/README.md).
Voor AI-voorbereiding zie [de AI-handleiding](../templates/ai-app/README.md):
die werkt met een lokale nepclient, zonder sleutel of betaalde API-aanroepen.
Voor bestandsverwerking zie [de automation-handleiding](../templates/automation/README.md):
die begint met dry-run en behoudt bronbestanden.

## 1. Open de studio en controleer je hulpmiddelen

Open in VS Code via **File > Open Folder** de map `codex-studio`. Open daarna een
nieuwe terminal en kies PowerShell. Voer opdrachten regel voor regel uit. Kopieer
geen eventuele `PS ...>`-prompt mee.

```powershell
Get-Location
Test-Path .\create_project.py
python --version
git --version
```

`Test-Path` moet `True` tonen. Gebruik Python 3.11 of hoger. Git is pas nodig voor
versiebeheer, niet voor het genereren of testen. Als een opdracht ontbreekt, volg
dan [problemen oplossen](TROUBLESHOOTING.md). Laat Codex niets installeren zonder
dat je eerst weet wat wordt geïnstalleerd en toestemming hebt gegeven.

De voorbeelden starten telkens vanuit de aangegeven map. Je hoeft geen virtuele
omgeving te activeren en geen PowerShell-uitvoeringsbeleid te wijzigen.

## 2. Genereer je eerste project

Voer dit uit vanuit de hoofdmap van de studio:

```powershell
python .\create_project.py mijn-notities --type python --output "$HOME\Projects"
```

Dit maakt `mijn-notities` onder `Projects` in je eigen thuismap. `$HOME` is een
PowerShell-variabele; gebruik deze alleen als onderdeel van een pad en verander
de waarde niet. De bovenliggende map wordt zo nodig aangemaakt. Het project zelf
mag nog niet bestaan, ook niet als lege map.

Zonder `--output` gebruikt de generator `Projects` in je thuismap. Met
`--output` kies je bewust een andere oudermap. De helptekst toont de standaard.

Een alternatief vanuit de studio is:

```powershell
python .\create_project.py mijn-notities --type python --output .\projecten
```

Dat maakt `.\projecten\mijn-notities` onder de studio. Kies één van de voorbeelden.
De vervolgstappen hieronder gaan uit van het eerste voorbeeld met `$HOME`.
Een project buiten de studio blijft duidelijk gescheiden van de studio zelf.

## 3. Open en test het nieuwe project

Open in een nieuw VS Code-venster de map `Projects\mijn-notities` onder je
thuismap. Je kunt in PowerShell ook rechtstreeks naar die map gaan:

```powershell
Set-Location -LiteralPath "$HOME\Projects\mijn-notities"
Get-ChildItem -Force
python -m unittest discover -s tests -v
```

De vier voorbeeldtests moeten slagen: de laatste regel is `OK`. Ze controleren
de begroeting, het verwijderen van witruimte rondom de naam, lege invoer en de
uitvoer van de app. Een test vergelijkt wat de code werkelijk doet met het
verwachte resultaat. `-s tests` kiest de testmap en `-v` toont elke testnaam.

De tests voegen de eigen `src`-map toe aan het Python-zoekpad. Daarom werken ze
zonder package-installatie en zonder de studio. Zie [templates](TEMPLATES.md)
voor de uitleg van deze mappenstructuur.

## 4. Start de app

Vanuit de nieuwe projectmap:

```powershell
Set-Location .\src
python -m mijn_notities
Set-Location ..
```

De uitvoer is `Hallo, Voorbeeld!`. De projectnaam bevat een koppelteken; de
Python-packagenaam gebruikt een underscore. Gebruik dus `mijn_notities` bij `-m`.

## 5. Vraag Codex om een kleine wijziging

Lees de gegenereerde `README.md` en `AGENTS.md`. Een bruikbare opdracht is:

> Lees eerst AGENTS.md en onderzoek dit project. Stel een kleine uitbreiding
> voor op de begroeting en leg uit welke tests erbij horen. Wacht op mijn
> goedkeuring. Installeer niets en maak geen commit of push.

Controleer steeds in welke map Codex werkt. De studio-instructies gelden niet
automatisch voor projecten buiten de studio; het gegenereerde project heeft
daarom een eigen `AGENTS.md`.

Ga verder met [de dagelijkse workflow](WORKFLOW.md) en [veilig werken](SECURITY.md).
