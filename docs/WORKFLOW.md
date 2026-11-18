# Dagelijks werken en versiebeheer

Werk aan één duidelijk doel tegelijk: onderzoek, wijzig een klein onderdeel,
test en bekijk de verschillen. Lees eerst de `AGENTS.md` en README van het
project. Geef Codex vooraf je grenzen, bijvoorbeeld geen installaties of publicatie.

## Van opdracht naar gecontroleerde wijziging

Beschrijf wat je wilt bereiken en hoe je kunt zien dat het werkt. Laat Codex
bij grotere wijzigingen eerst een plan geven. Als je wilt dat Codex op jouw
goedkeuring wacht, zeg dat expliciet. Controleer na elke stap de gewijzigde
bestanden in VS Code en voer vanuit de projecthoofdmap de tests uit:

```powershell
python -m unittest discover -s tests -v
```

Een nieuw gedrag of een opgeloste fout krijgt een passende test. Een geslaagde
test sluit niet alle fouten uit; controleer ook voorbeelden en foutmeldingen.
`FAIL` betekent dat een verwachting niet klopt; `ERROR` betekent dat uitvoeren
misging. `skipped` is overgeslagen en dus niet volledig getest.

Bij een webproject voer je daarnaast `node --test tests/counter.test.cjs` uit
(Node.js 22+). De Python-tests controleren de pagina en assets; de Node-tests
controleren JavaScript en knopafhandeling. Controleer de pagina ook handmatig
in een browser. Geen van beide automatische suites vervangt een visuele controle.

Voor het AI-startproject volstaat dezelfde unittest-opdracht als voor Python.
Geef tests alleen fictieve configuratie en behoud de netwerkblokkade. Er zijn
geen API-sleutel of betaalde aanroepen nodig; de demo gebruikt geen echte provider.

Bij automation begin je met dry-run op fictieve gegevens. Gebruik `--apply` pas
na beoordeling van het plan en kies een nieuwe doelmap. Test bestandsbewerkingen
met tijdelijke mappen; de gewone unittest-opdracht controleert ook de dry-run.
Er wordt geen taakplanner of achtergrondservice automatisch ingericht.

## Werken in een bestaande Git-repository

Git houdt lokaal versies bij. GitHub is een externe dienst waar je een repository
kunt delen. Een gegenereerd project heeft nog geen eigen Git-repository.

Controleer vanuit de juiste projectmap:

```powershell
git rev-parse --show-toplevel
git status --short --branch
git branch --show-current
```

De bovenste map moet bij dit project horen. Een project binnen een andere
repository kan onbedoeld de Git-status van die bovenliggende repository tonen.
Als Git meldt dat er geen repository is, stop dan met de Git-stappen. Spreek
eerst af of je Git wilt inrichten; de generator doet dat niet automatisch.

Maak bij een schone werkmap een taakbranch met een nog ongebruikte naam:

```powershell
git switch -c feature/begroeting
```

Een branch is een eigen werklijn voor je wijziging. Zijn er al wijzigingen van
jou of iemand anders, bepaal dan eerst bij welke taak ze horen. Gooi ze niet weg
om een branchwisseling mogelijk te maken.

## Wijzigingen beoordelen en eventueel vastleggen

Na wijzigen en testen:

```powershell
git status --short
git diff --check
git diff
```

`git diff` toont veranderingen aan bestanden die Git al volgt. Nieuwe, nog niet
gevolgde bestanden moet je ook openen en lezen; `git status` noemt ze met `??`.
Controleer vooral op [secrets en persoonsgegevens](SECURITY.md).

De volgende opdrachten zijn uitsluitend voor wanneer je bewust een lokale
commit wilt maken. Dit is geen opdracht aan Codex om dat vanzelf te doen.
Voorbeeld: alleen de README is aangepast op de taakbranch:

```powershell
git add -- README.md
git diff --cached
git commit -m "docs: verduidelijk de projecthandleiding"
```

`git add` selecteert bestanden voor de volgende commit. `--cached` toont precies
die selectie. Een commit legt de selectie lokaal vast. Selecteer bestanden
gericht in plaats van blind alles toe te voegen. Als Git om een identiteit vraagt,
kies die bewust; de naam en het e-mailadres komen in de commitmetadata terecht.

## Optioneel delen via GitHub

De studio maakt geen GitHub-repository aan. Regel eerst bewust een repository,
toegang en de zichtbaarheid ervan. Controleer de bestaande koppeling:

```powershell
git remote -v
```

Alleen als `origin` de bedoelde repository is, de taakbranch `feature/begroeting`
heet en je wilt publiceren:

```powershell
git push -u origin feature/begroeting
```

Een push verstuurt commits naar de externe repository. Geef Codex hiervoor
uitdrukkelijk toestemming. Open daarna op GitHub een pull request: een voorstel
om de branch samen te voegen. Bekijk verschillen en testresultaten voordat je
samenvoegt. Gebruik geen geforceerde push om fouten of conflicten te omzeilen.

De meegeleverde Python-workflow draait alleen als hij onder `.github/workflows`
in de repositoryhoofdmap staat en Actions beschikbaar is. Een workflow in de
templatemap van de studio wordt niet als zelfstandige workflow ontdekt.

## De studio zelf controleren

De generator-tests staan in de studiohoofdmap onder `tests`. Er is momenteel
een bekende fout: de standaardmap is hardcoded en de test
`test_default_output_uses_home_projects` verwacht de thuismap. Draai daarom
voorlopig niet blind de volledige suite: die test kan buiten de tijdelijke map
proberen te schrijven. Zie [problemen oplossen](TROUBLESHOOTING.md) voor een
veilige beperkte controle. Verzwijg de uitgesloten test niet in je verslag.

De branch- en beoordelingsstappen sluiten aan bij de officiële uitleg van
[git switch](https://git-scm.com/docs/git-switch),
[git diff](https://git-scm.com/docs/git-diff) en
[GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow).
