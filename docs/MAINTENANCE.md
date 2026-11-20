# Alleen-lezen onderhoudscontrole

Voer vanuit de studiohoofdmap in PowerShell uit:

```powershell
python .\studio.py maintenance
python .\studio.py maintenance --format json
python .\studio.py maintenance --format markdown
```

Python 3.11 of hoger is vereist. De opdracht controleert de map waarin de studio
staat, ook bij starten vanuit een andere werkmap. Je hoeft niets te installeren.
Er zijn geen opties `--root`, `--output`, `--run-tests` of automatische reparaties.
De opdracht wijzigt geen projecten, bestanden, caches of Git-administratie.
Onderzochte Python-bestanden worden als tekst/syntaxis gelezen, niet geïmporteerd.
Er worden geen subprocessen, tests of netwerkverzoeken gestart.

## Vaststellingen en aanbevelingen

Iedere regel heeft een status en een herkenbaar voorvoegsel:

- **VASTSTELLING**: een controleerbare voorwaarde. PASS betekent dat die specifieke
  controle slaagt; FAIL betekent dat iets ontbreekt, onveilig of ongeldig is.
  SKIP betekent dat iets niet beoordeeld is, bijvoorbeeld een geplande template.
- **AANBEVELING**: een expliciet als WARN gemarkeerde handmatige vervolgstap.
  Dit is geen bewezen fout en verandert op zichzelf de exitcode niet.

De controle gebruikt dezelfde veilige leesfuncties en structurele controles als
[quality](QUALITY.md), zonder Git-opdrachten. Symlinks, Windows-junctions en
onveilige paden worden geweigerd. Bestandsgrootte, aantallen en verwerkingstijd
zijn begrensd. Een onvolledige controle geeft een fout, geen stilzwijgend succes.
Blokkerende OS-bestandstoegang kan niet universeel met een harde deadline worden
gestopt; dit is geen sandbox tegen gelijktijdige wijzigingen door andere processen.

## Wat wordt gecontroleerd?

- Vereiste studiobestanden, releasehandleiding en changelog: gewone bestanden,
  geen koppelingen. Lokale links en afgesloten codeblokken in de bekende
  verplichte Markdownbestanden worden gecontroleerd; externe links en anchors niet.
- Het manifest: schema, MAJOR.MINOR.PATCH-templateversies, paden en gedeclareerde
  templatebestanden. Ontbrekende web-, AI- en automation-bronnen die op deze
  branch gepland zijn, krijgen SKIP. Een aanwezige onvolledige template krijgt FAIL.
- De letterlijke Python-bestandenlijst in de generator wordt vergeleken met het
  manifest. Een niet-letterlijke lijst vereist aanvullende analyse en krijgt SKIP.
  Er wordt geen proefproject gegenereerd.
- De teststructuur: vindbare testbestanden en Python-syntaxis. Dit bewijst geen
  succesvolle testuitvoering of goede tests. **Testdekking blijft SKIP**: er wordt
  geen ontbrekende dekking afgeleid uit aantallen of namen van bestanden.
- Statische pakketversies in gedeclareerde `pyproject.toml`-bestanden: geldig
  MAJOR.MINOR.PATCH. Dynamische versies worden niet berekend. Pakketversies,
  templateversies en studioreleaseversies zijn verschillende gegevens en hoeven
  niet gelijk te zijn.
- Gevonden changelogsecties `## [Unreleased]` en `## [MAJOR.MINOR.PATCH]`: geldige,
  unieke secties. De inhoud en publicatiestatus worden niet bewezen. Er wordt
  geen studioreleaseversie verzonnen als een gezaghebbende bron ontbreekt.

## Uitvoer en vervolgstappen

Tekst, JSON en Markdown bevatten dezelfde resultaten en samenvatting. Logging
staat op stderr, resultaten op stdout; voeg die niet samen als je JSON verwerkt.
Er ontstaan standaard geen log- of rapportbestanden. Foutmeldingen herhalen geen
ruwe exceptions of broninhoud. Zie [veiligheid](SECURITY.md).

Exitcodes: 0 bij geen FAIL, 1 bij vastgestelde fouten/onvolledige controle,
2 bij ongeldige opties, 130 bij Ctrl+C. Bij een mislukte rapportaflevering kan de
gedeelde rapportmodule exitcode 3 geven. WARN/SKIP betekenen geen volledige
kwaliteitsgarantie. De JSON bevat `command: "maintenance"` en `tests_requested: false`.

Beoordeel aanbevelingen zelf: gedragsgerichte tests en testdekking vragen
aanvullende analyse; browsergedrag, beveiliging en inhoudelijke documentatiekwaliteit
vragen een passende review. Voor optionele tests gebruik je apart `quality
--run-tests` en bevestig je de waarschuwing. Voor een release gebruik je
[release-check](RELEASE.md); externe controles en publiceren blijven handmatig.
