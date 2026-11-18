# PROJECT_NAME

Een zelfstandige webapp met HTML, CSS en JavaScript, zonder frameworks, externe
lettertypen, netwerkverzoeken of pakketinstallaties. De teller werkt in het
geheugen: verversen begint opnieuw bij nul. Er worden geen gegevens opgeslagen.

## Starten op Windows

Open `public/index.html` vanuit Verkenner in je browser. Je hebt daarvoor alleen
een moderne browser nodig. Voor een lokale HTTP-server kun je vanuit de
projecthoofdmap ook Python 3.11 of hoger gebruiken:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory public
```

Open daarna `http://127.0.0.1:8000` in de browser. Stop met Ctrl+C. Deze server
is alleen voor lokaal ontwikkelen; gebruik hem niet voor publieke hosting.
Alleen `public` wordt geserveerd, zodat tests en ontwikkelinstructies erbuiten blijven.

## Bestanden

- `public/index.html`: pagina met teller, optelknop en resetknop.
- `public/styles.css`: responsieve opmaak met zichtbare toetsenbordfocus.
- `public/app.js`: tellerlogica en knopafhandeling, zonder imports van buitenaf.
- `tests/counter.test.cjs`: JavaScript-tests met ingebouwde Node.js-modules.
- `tests/test_page.py`: HTML- en bestandscontroles met Python.
- `.github/workflows/web-tests.yml`: dezelfde tests op GitHub Actions.
- `AGENTS.md`: ontwikkelregels; `.gitignore`: lokale bestanden buiten Git houden.

## Automatisch testen

Gebruik Node.js 22 of hoger en Python 3.11 of hoger. Node is alleen nodig voor
de JavaScript-tests, niet om de pagina te bekijken. Voer vanuit de projectmap uit:

```powershell
node --test tests/counter.test.cjs
python -m unittest discover -s tests -v
```

Er is geen `npm install`, pip-installatie of buildstap. De zes JavaScript-tests
controleren tellerlogica, reset, onafhankelijke tellers, knopafhandeling,
ontbrekende elementen en het automatisch starten van het browserscript.
De drie Python-tests controleren HTML-structuur, element-ID's en lokale assets.
De knoptests gebruiken een kleine nagebootste documentstructuur; dit zijn geen
volledige browsertests. Controleer ook handmatig klikken, resetten, vernieuwen,
een smal venster en bediening met Tab en Enter.

Lees de uitvoer van beide opdrachten: een geslaagde Python-test vervangt de
JavaScript-tests niet. Ontbrekende hulpmiddelen eerst bespreken, niet automatisch
installeren.

## GitHub en verder bouwen

De workflow werkt wanneer deze projectmap de hoofdmap van een GitHub-repository
is en Actions is toegestaan. Hij gebruikt Node.js 22 en 24 en Python 3.11 op
Linux en Windows, met alleen leesrechten en zonder eigen secrets. Hij publiceert
de site niet. Git en een GitHub-repository worden niet automatisch aangemaakt.

`PROJECT_NAME` is de tijdelijke projectnaam. De studio-generator vult deze in;
bij handmatig kopiëren vervang je de naam zelf. Het gegenereerde project heeft
geen studio-bestanden nodig om te draaien of te testen.

Gebruik `textContent` voor tekst die later uit invoer komt, geen `innerHTML`.
Zet geen secrets of persoonsgegevens in browsercode: die is voor bezoekers
leesbaar. Lees `AGENTS.md` voordat je wijzigingen maakt.
