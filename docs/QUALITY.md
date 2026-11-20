# De studio controleren met quality

Voer in PowerShell vanuit de studiohoofdmap uit:

```powershell
python -B .\studio.py quality
```

Deze opdracht controleert **de studio zelf**, niet alle projecten in
`$HOME\Projects`. De gecontroleerde map is de map van `studio.py`, ook als je
het script vanuit een andere werkmap aanroept. Er zijn geen `--root`,
`--project`, installatie-, herstel- of automatische reparatieopties.
Gebruik `studio.py check PROJECT --root ...` voor een geregistreerd project.

Resultaten staan op stdout; centrale logmeldingen staan op stderr en maken
standaard geen bestanden. Zo blijft dit een geldig JSON-rapport:

```powershell
python -B .\studio.py quality --format json
```

Voeg `--output .\quality-result.json` toe als je bewust een nieuw rapportbestand
wilt bewaren. Een bestaand bestand wordt geweigerd. Voeg stderr niet samen met
stdout (`2>&1`) als een programma de JSON moet lezen. Zie de
[logging- en privacyafspraken](SECURITY.md) voor de foutcodes en beperkingen.

Voor een door jou ingestelde terugkerende controle zie je de
[PowerShell- en Taakplanner-handleiding](TASK_SCHEDULER.md). Het script start
geen tests en registreert geen taak; de planning maak je uitsluitend zelf.

## Standaard: alleen lezen

- Vereiste studiobestanden, frontendbestanden en handleidingen moeten aanwezig
  zijn als gewone bestanden, zonder symlinks of junctions in hun paden.
- Het lokale manifest wordt gecontroleerd op schema, versies, beschrijvingen
  en veilige relatieve paden. Ongeldige ongebruikte manifestregels geven ook FAIL.
- Alle in een aanwezige template gedeclareerde bestanden worden gecontroleerd.
  Ontbrekende Python-bron of een onvolledige aanwezige template geeft FAIL.
  Web-, AI- en automation-bronnen die op deze branch nog ontbreken geven WARN:
  hun status is gepland, geen bevestiging van een werkend template.
- Python-bestanden rechtstreeks in de studiohoofdmap, onder `tests` en in de
  gedeclareerde templatebestanden worden met `ast.parse` op syntaxis gecontroleerd.
  De modules worden niet geïmporteerd of uitgevoerd. Alleen syntaxfouten en
  regelnummers worden gemeld, geen bronregels of bestandinhoud.
- De bekende handleidingen worden gecontroleerd op lokale Markdownlinks en
  afgesloten codeblokken. Externe links worden niet opgehaald; anchors en
  volledige Markdown-/PowerShell-validatie vallen buiten deze eenvoudige controle.
- Git-status hergebruikt de bestaande alleen-lezen, begrensde Git-opdrachten
  uit `studio.py check`, met dezelfde weigering van hooks, filters, externe
  configuratie-includes en onveilige Git-verwijzingen.

Er worden geen projecttests, imports van de onderzochte broncode, scripts of
installaties gestart. Alleen vertrouwde studiocode voert de controle uit.
Er zijn geen externe netwerkverzoeken, caches, automatische correcties, commits
of pushes. Zonder `--output` wordt geen rapportbestand gemaakt. `.env` en gewone gegevensbestanden worden niet
inhoudelijk gelezen. Broncode en documentatie worden wél gelezen om ze te controleren.

## Optioneel: de vaste studio-testsuite uitvoeren

```powershell
python -B .\studio.py quality --run-tests
```

Eerst lopen de alleen-lezen controles. Bij een FAIL starten de tests niet en
wordt niet om toestemming gevraagd. Bij alleen PASS/WARN/SKIP toont de opdracht
een samenvatting van de voorcontrole, waarschuwing, werkmap en vaste testopdracht.
Alleen `ja` geeft
toestemming. Enter, `nee`, `q`, een ander antwoord of einde invoer annuleert.
Ctrl+C bij de bevestiging annuleert eveneens zonder tests te starten.

Voortgang, waarschuwingen en bevestigingsvragen staan op **stderr**. Het volledige
eindrapport staat op **stdout**. Daardoor blijft ook met `--run-tests` de JSON-
of Markdown-uitvoer vrij van prompts en ruwe testuitvoer.

**Tests voeren code uit en kunnen bestanden wijzigen, processen starten en
netwerkverkeer veroorzaken. Dit is geen sandbox.** Vertrouw de studio en tests
voordat je bevestigt. Statische controles kunnen niet bewijzen dat testcode
veilig is. Na bevestiging worden de statische bestands- en padcontroles herhaald.

De enige toegestane opdracht gebruikt dezelfde Python-interpreter als de studio:

```powershell
python -I -S -B -m unittest discover -s tests -v
```

De werkmap is altijd de studiohoofdmap. `-I -S` voorkomt Python-startuphooks en
gebruikers-/site-packages; `-B` voorkomt bytecodecachebestanden. Opdrachten uit
metadata, `package.json`, workflows of URL's worden niet overgenomen. Er wordt
niets geïnstalleerd. Er komt geen quality-route of uitvoerknop in het dashboard.

De gedeelde procesrunner gebruikt `shell=False`, maximaal 60 seconden en 1 MiB
voor stdout en stderr samen. Bij overschrijding stopt de procesboom. De ruwe
testuitvoer wordt niet afgedrukt om gegevenslekken te beperken. Het overzicht
meldt het aantal gevonden en overgeslagen tests. Nul gevonden tests of alle
tests overgeslagen geeft FAIL, ook als unittest exitcode 0 teruggeeft.

## Testuitvoer herkennen

Bij `python -m unittest discover -s tests -v` is de einduitslag bepalend:
`OK` betekent geen mislukte tests; `FAILED (failures=..., errors=...)` betekent
dat er wel tests mislukken. `skipped` betekent dat een test bewust niet is
uitgevoerd, bijvoorbeeld door Windows-rechten of het bestaande uitvoerbeleid.

Tests bootsen ook fouten na om de foutafhandeling te controleren. Verwachte
benchmark- en dashboardmeldingen worden binnen die tests opgevangen en op hun
gebeurteniscode gecontroleerd. Ze verschijnen daardoor niet als losse
`[ERROR]`- of `[WARNING]`-regels tussen geslaagde tests. Echte testfouten en
onverwachte meldingen blijven zichtbaar; de normale CLI-logging is ongewijzigd.

## Tekst, JSON en Markdown

Kies de gewenste vorm met `--format`; `text` blijft de standaard:

```powershell
python -B .\studio.py quality --format text
python -B .\studio.py quality --format json
python -B .\studio.py quality --format markdown
```

Elke vorm komt uit hetzelfde rapportmodel: dezelfde resultaten in dezelfde
volgorde, dezelfde PASS/WARN/FAIL/SKIP-tellingen en dezelfde exitcode. Er wordt
per aanroep eenmaal gecontroleerd; drie afzonderlijke aanroepen kunnen verschillen
als de studiomap of Git-status tussentijds verandert. Er worden geen tijdstempels,
absolute studiopaden of ruwe subprocessuitvoer aan het rapportmodel toegevoegd.
Resultaten kunnen wel relatieve bestandsnamen bevatten; beoordeel een rapport
voordat je het deelt.

JSON bevat precies één document op stdout, met deze vaste velden:

| Veld | Betekenis |
| --- | --- |
| `schema_version` | Momenteel integer `1`; controleer dit bij automatische verwerking. |
| `command` | `quality`. |
| `completion` | `complete` voor afgeronde controles, `error` voor een fatale controle-/rapportagefout, `cancelled` voor onderbreking. `complete` betekent niet dat alles PASS is. |
| `tests_requested` | Of `--run-tests` is opgegeven; geen bewijs dat tests werkelijk draaiden. |
| `exit_code` | De afsluitcode die bij het rapport hoort. |
| `summary` | Aantallen met de vaste sleutels `PASS`, `WARN`, `FAIL`, `SKIP`. |
| `results` | Lijst objecten met `status`, `label` en `message`. |

JSON gebruikt ASCII-escapes waar nodig zodat Unicode ook via een Windows-console
met beperkte tekencodering geldig blijft en bij inlezen correct terugkomt.
Markdown gebruikt veilige tekstentiteiten voor onder meer HTML, links,
tabelscheidingstekens en opmaak. Stuurtekens worden zichtbaar gemaakt en niet
als terminalopdrachten uitgevoerd. Er wordt geen onbetrouwbare tekst als HTML
ingevoegd.

Een PowerShell-voorbeeld zonder rapportbestand:

```powershell
$qualityJson = python -B .\studio.py quality --format json
$qualityExit = $LASTEXITCODE
$qualityRapport = $qualityJson | ConvertFrom-Json
$qualityRapport.summary
$qualityExit
```

Voeg stderr niet samen met stdout wanneer je JSON automatisch verwerkt;
gebruik dus geen `2>&1` voor die parserinvoer.

## Optioneel een nieuw rapportbestand bewaren

Alleen een expliciete `--output` schrijft een bestand. Het rapport blijft ook
op stdout beschikbaar; de melding over opslaan gaat naar stderr:

```powershell
python -B .\studio.py quality --format json --output ".\quality-rapport.json"
python -B .\studio.py quality --format markdown --output ".\quality-rapport.md"
```

Gebruik bij tekstuitvoer een `.txt`-naam. De extensie moet bij het gekozen
formaat passen: `.txt`, `.json` of `.md`. Relatieve paden zijn relatief aan de
huidige PowerShell-map. De oudermap moet al bestaan; er worden geen mappen
aangemaakt. De rapportbestanden zijn UTF-8 zonder BOM.

Bestaande bestanden, mappen en kapotte koppelingen worden **nooit overschreven**.
Een tweede aanroep met dezelfde naam wordt geweigerd vóór controles of tests
starten. Kies zelf een nieuwe naam; gebruik geen `>` of `Out-File -Force` als
vervanging voor deze veiligheidscontrole, want shell-omleiding kan wel een
bestaand bestand vervangen.

UNC-/Windows-devicepaden, alternatieve datastromen, onveilige namen,
symlinks/junctions in de oudermap en bekende administratie zoals `.git`, `.aws`,
`.ssh`, `.codex` en virtuele omgevingen worden geweigerd. Oudermap en doelnaam
worden vlak vóór publiceren opnieuw gecontroleerd. Het rapport is maximaal
4 MiB en wordt eerst exclusief onder een willekeurige
`.quality-report-....incomplete`-naam geschreven en geflusht. Alleen volledige
inhoud wordt naar de eindnaam gepubliceerd, zonder overwrite-fallback.
Windows gebruikt hiervoor de niet-overschrijvende rename; op POSIX wordt een
hardlink gebruikt en vervolgens het eigen tijdelijke bestand verwijderd.

Bij een schrijf- of publicatiefout kan een eigen `.incomplete`-bestand
achterblijven. De eindnaam wordt dan niet als geslaagd gemeld. Een bestaand
doel blijft behouden. Bij een afgebroken quality-controle (exitcode 130) wordt
geen rapportbestand geschreven; stdout bevat wel het geannuleerde rapport.
Bij een onderbreking tijdens opslaan kan een tijdelijk bestand achterblijven.
Vertrouw een rapport op die tijdelijke naam niet als voltooid rapport.

Zonder `--run-tests` is `--output` de enige gevraagde schrijfactie. Rapporten
zijn niet versleuteld of digitaal ondertekend. Gebruik een vertrouwde lokale map
met passende toegangsrechten en zonder gelijktijdige padwijzigingen of onbedoelde
cloudsynchronisatie. De bestaande beperkingen voor netwerk-mounts en OS-toegang
uit [de back-uphandleiding](BACKUPS.md) gelden eveneens.

## Statussen en exitcodes

| Status | Betekenis |
| --- | --- |
| PASS | De genoemde controle slaagt; geen algemene kwaliteits- of veiligheidsgarantie. |
| WARN | Aandachtspunt, bijvoorbeeld geplande templates, gewijzigde werkmap of geen Git-repository. |
| FAIL | Ontbrekende/ongeldige/onveilige inhoud, mislukte tests of een overschreden limiet. |
| SKIP | Controle niet uitgevoerd, zoals tests zonder verzoek of een handmatige beoordeling. |

De samenvatting telt de statussen:

| Exitcode | Betekenis |
| --- | --- |
| `0` | Geen FAIL. WARN en bewust geannuleerde testbevestiging blijven toegestaan. |
| `1` | Mislukte kwaliteitscontrole of tests, of fatale controlefout. |
| `2` | Ongeldige CLI-opties; argparse schrijft gebruiksuitleg naar stderr, geen JSON-rapport. |
| `3` | Rapportdoel onveilig/bestaand, rapport te groot of niet veilig opgeslagen/uitgevoerd. Een geldig foutrapport blijft waar mogelijk op stdout beschikbaar. |
| `130` | Ctrl+C tijdens de controle of tijdens draaiende tests. |

Als tests verplicht zijn voor jouw vervolgactie, controleer dan naast exitcode 0
ook het resultaat met label `Tests`: dat moet `PASS` zijn. `tests_requested: true`
kan samengaan met SKIP na `nee` of einde invoer. Dit behoudt het bestaande
annuleergedrag; een overgeslagen test mag je niet als geslaagd behandelen.
Na gestarte tests zijn wijzigingen mogelijk; die worden niet teruggedraaid.

## Grenzen en handmatige controles

Bestanden worden begrensd tot 64 KiB per inhoudelijke leesactie, bomen en de
directe studiomap tot 4.000 items en documenten tot 500 verwijzingen.
De statische stappen hebben een controletermijn van 30 seconden; Git gebruikt
daarnaast zijn bestaande limiet van 10 seconden per proces. OS-bestandstoegang
is niet overal hard onderbreekbaar. Een te groot of onleesbaar onderdeel geeft
geen stilzwijgend volledig resultaat. De bestaande beperkingen rond gelijktijdige
padvervanging en vertrouwde lokale mappen gelden ook hier.

Quality is geen security-audit, geheimenscanner, formatter, JS/CSS-linter,
browsercontrole of bewijs dat alle checklistpunten voldaan zijn. JavaScript,
HTML en CSS worden niet uitgevoerd; inhoudelijke browsercontroles blijven
handmatig. Zie de [workflow](WORKFLOW.md), [projectchecklist](PROJECT_CHECKLIST.md)
en [beveiligingsuitleg](SECURITY.md).
