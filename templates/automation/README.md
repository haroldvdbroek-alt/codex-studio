# PROJECT_NAME

Een minimaal Python-startpunt voor handmatig herhaalde bestandsverwerking.
De voorbeeldtaak zet directe UTF-8 `.txt`-bestanden om naar hoofdletters in een
nieuwe, aparte doelmap. Bronbestanden blijven ongewijzigd. Andere bestanden en
submappen worden niet verwerkt. Er is geen scheduler of achtergrondtaak.

## Voorbereiden en testen

Gebruik Python 3.11+; alleen de standaardbibliotheek is nodig. Vanuit de projectmap:

```powershell
python -m unittest discover -s tests -v
```

De tests gebruiken tijdelijke mappen, controleren dry-run, echte bestandsuitvoer,
invoerfouten, logging en behoud van bestaande gegevens. Tests voegen hun eigen
`src`-map aan het zoekpad toe. Het project heeft geen installatie of studio nodig.

## Een veilige demo op Windows

Gebruik eerst een nieuwe bronmap met fictieve gegevens. Voer vanuit de projectmap
onderstaand PowerShell-blok uit; `New-Item` zonder `-Force` en `CreateNew` weigeren
bestaande demo-invoer. Maak bij een fout niet blind dezelfde bestanden opnieuw.

```powershell
New-Item -ItemType Directory -Path .\input -ErrorAction Stop
$demoPath = Join-Path (Get-Location) 'input\voorbeeld.txt'
$demoStream = [System.IO.File]::Open($demoPath, [System.IO.FileMode]::CreateNew)
try {
    $demoBytes = [System.Text.Encoding]::UTF8.GetBytes("Hallo voorbeeld`n")
    $demoStream.Write($demoBytes, 0, $demoBytes.Length)
} finally {
    $demoStream.Dispose()
}
```

Bekijk eerst het plan. Vanuit de projectmap:

```powershell
Push-Location .\src
python -B -m project_package ..\input ..\output
Pop-Location
```

De generator vervangt `project_package` door de eigen packagenaam. `-B` voorkomt
dat Python zelf importcachebestanden (`__pycache__`) schrijft. Deze dry-run
leest alleen mapinformatie: geen bestandsinhoud en geen writes, ook geen logbestand.
Hij meldt aantallen en acties, geen namen of inhoud. Hij controleert dus niet of
de tekst geldig UTF-8 is of de uitvoermap schrijfbaar is; dat gebeurt bij uitvoeren.

Alleen als je het plan wilt uitvoeren:

```powershell
Push-Location .\src
python -B -m project_package ..\input ..\output --apply
Pop-Location
Get-Content -LiteralPath .\output\voorbeeld.txt -Encoding UTF8
```

Verwachte tekst: `HALLO VOORBEELD`. Een volgende uitvoering naar `output` wordt
geweigerd. Kies een nieuwe doelmap, bijvoorbeeld `..\output-tweede-run`, om de
taak opnieuw uit te voeren. Een lege bron maakt ook met `--apply` geen doelmap.

## Logging en veiligheid

Logging verschijnt op stderr met INFO voor plannen/resultaten en ERROR voor
fouten. Exitcode 0 betekent dat de opdracht slaagde; 1 betekent een taakfout.
Een verkeerd commandoregelargument geeft de argparse-foutcode 2. Logging schrijft
geen bestanden en vermeldt geen inhoud, bestandsnamen of persoonlijke paden.

Bron en doel mogen niet gelijk zijn of in elkaar liggen. De hele doelmap moet
nieuw zijn; er worden geen bestanden in een bestaande map bijgewerkt. Symlinks
en Windows-junctions worden geweigerd, ook in bovenliggende mappen en de bronmap.
Gebruik rechtstreeks bereikbare mappen die jij beheert. Gelijktijdig vervangen
van bestanden door andere processen wordt niet ondersteund.

Alle tekst wordt vóór het schrijven gelezen en op UTF-8 gecontroleerd. Dit houdt
de voorbeeldcode eenvoudig, maar gebruikt geheugen naar de totale bestandsgrootte:
gebruik kleine tekstbestanden. Het is geen transactionele batch: een schijffout
kan een gedeeltelijk nieuw doel achterlaten. Er wordt niets automatisch verwijderd.
Controleer eerst het doel voordat je met opruimen instemt. Tekstregels worden
bij verwerken naar LF genormaliseerd.

## Bestanden en GitHub

De package bevat `tasks.py` voor verwerking en `__main__.py` voor de CLI.
`pyproject.toml` bevat alleen metadata. `tests/test_tasks.py` controleert de taak.
`AGENTS.md` beschrijft ontwikkelregels. `.gitignore` sluit onder andere lokale
input/output, caches en logs uit; controleer andere datamappen zelf voordat je
bestanden aan Git toevoegt. Secrets en persoonsgegevens horen niet in fixtures.

De workflow `.github/workflows/automation-tests.yml` voert tests uit op Windows
en Linux met Python 3.11 en 3.14. Hij werkt vanuit een zelfstandige repository,
zonder extra pakketten, planning of publicatie. Git en GitHub worden niet
automatisch ingericht. Bij handmatig kopiëren vervang je `PROJECT_NAME` en
`project_package` in inhoud en mapnamen zelf.
