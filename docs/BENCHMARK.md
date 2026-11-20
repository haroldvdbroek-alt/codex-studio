# Benchmark met tijdelijke fictieve projecten

Deze benchmark meet de lokale functies achter `list`, `updates` en de
standaardmodus van `check`. Hij maakt zelf een nieuwe tijdelijke map met
kunstmatige projectstructuren. Je echte projectroot wordt niet gescand,
gekopieerd of aangepast. Er is geen `--root`, `--output`, `--keep` of
`--run-tests`-optie waarmee je de benchmark op bestaande projecten kunt richten.

## Starten in PowerShell

Voer vanuit de studiohoofdmap uit:

```powershell
python -B .\studio.py benchmark
```

Standaard gebruikt de benchmark 12 fictieve projecten, verdeeld over Python,
web, AI en automation. Per onderdeel wordt één opwarmronde uitgevoerd en
worden daarna drie herhalingen gemeten. Er is geen nieuwe toestemming nodig
voor een echte back-up of herstel: die functies worden hier niet gestart.

Je kunt de omvang begrensd aanpassen:

```powershell
python -B .\studio.py benchmark --projects 20 --repeat 5
python -B .\studio.py benchmark --projects 12 --repeat 3 --format json
python -B .\studio.py benchmark --projects 12 --repeat 3 --format markdown
```

`--projects` accepteert 4 tot en met 200; `--repeat` accepteert 1 tot en met 10.
De ondergrens zorgt dat alle vier de types voorkomen. Onjuiste argumenten
worden geweigerd voordat een tijdelijke werkmap wordt gemaakt.
Je hoeft geen pakketten te installeren; alleen de Python-standaardbibliotheek
en de aanwezige studiobestanden zijn nodig.

## Wat wordt precies gemeten?

| Onderdeel | Gemeten handeling per herhaling |
| --- | --- |
| `list` | Alle fictieve projecten herkennen en hun metadata valideren. |
| `updates` | Alle fictieve projectversies vergelijken met het lokale studiomanifest. |
| `check` | Alle fictieve projecten achter elkaar controleren zonder projecttests. |

De lokale templatebeschrijvingen leveren alleen de vereiste bestandsnamen en
versies. Bestandsinhoud wordt volledig fictief aangemaakt; er wordt geen inhoud
van bestaande projecten of echte templates gekopieerd. `pyproject.toml` bevat
een eenvoudige geldige fictieve projectnaam. Overige bestanden bevatten alleen
testtekst. Fictieve Python-modules geven bewust een fout als iemand ze zou
uitvoeren; de benchmark importeert of start die modules nooit.

De datasetstructuren lijken voor de configuratiecontrole op de vier templates,
maar zijn **geen werkende apps**. Dit herstelt de ontbrekende web-, AI- of
automation-templatebronnen niet en breidt de generator niet uit.

Er worden geen Git-repositories gemaakt. De standaard Git-controle herkent dat
de fictieve projecten geen `.git` hebben en start daarom geen Git-proces.
Dit meet dus niet de snelheid van Git, projecttests, de browserdashboardserver,
back-up, herstel, release-check of PowerShell.

Het opbouwen en opruimen van de dataset en de controles op de benchmarkuitkomsten
vallen buiten de gerapporteerde meetintervallen. De `check`-meting omvat wel de
eigen lus en termijncontrole rondom alle projecten. `updates` omvat het normale
lezen van het lokale manifest. Dit zijn functiemetingen, geen aparte Python-
processtarts per opdracht en geen volledige CLI-opstartbenchmark.

## Cijfers lezen

Per onderdeel worden de afzonderlijke tijden, minimum, mediaan, gemiddelde,
maximum en projecten per seconde berekend. Tijden zijn in **milliseconden voor
de hele batch**, niet voor één project. Er worden geen willekeurige maxima
gebruikt om jouw computer als snel of langzaam te beoordelen.

De mediaan is de middelste meetwaarde en is vaak minder gevoelig voor een
eenmalige vertraging. Achtergrondprocessen, schijfcache, antivirus, systeemlast
en Python-versie beïnvloeden de cijfers. Vergelijk alleen vergelijkbare
omstandigheden en datasetgroottes. Een kleine fictieve dataset voorspelt niet
de prestaties van grote echte projecten of andere computers.

Bij een theoretisch nulinterval is projecten per seconde `null`, geen oneindige
waarde. Er worden geen ontbrekende of mislukte metingen als succesvolle cijfers
ingevuld. `PASS` betekent dat de meetbewerking het verwachte resultaat gaf,
niet dat een bepaalde snelheid of releasekwaliteit is gegarandeerd.

## Isolatie en opruimen

- Alleen een nieuwe map met prefix `codex-studio-benchmark-` onder de lokale
  OS-tempmap wordt gebruikt; er worden geen projectnamen of uitvoerpaden aangenomen.
- De tempbasis wordt geweigerd als die binnen de studio, de bovenliggende
  projectcontainer, de standaard `$HOME\Projects` of een map met een Git-/studio-
  projectmarkering in de ouderketen valt. Koppelingen en Windows-netwerkschijven
  worden niet gevolgd. Er worden daarbij alleen padmarkeringen gecontroleerd,
  geen inhoud van bestaande projecten.
- De benchmark controleert aantallen, projectnamen, verwachte update-status en
  het ontbreken van FAIL in de configuratiecontroles. Tests moeten SKIP blijven.
- Voor en na meten worden bestandslijst, SHA-256-inhoud en wijzigingstijden van
  de fictieve bestanden vergeleken. OS-toegangstijden kunnen bij lezen wel wijzigen.
- Alleen de eigen tijdelijke map wordt opgeruimd. Vóór recursief verwijderen
  worden het absolute canonieke pad, de verwachte ouder, de prefix en de
  oorspronkelijke mapidentiteit gecontroleerd. Er wordt geen ander pad als
  opruimdoel gekozen als deze controle mislukt.
- Geen tests, projectcode, subprocessen, netwerkaanroepen, Git-wijzigingen,
  installaties, taakregistratie of publicatie door de benchmark.
- De normale Python-start laadt wel vertrouwde studiocode en kan normale
  interpreter-startupconfiguratie gebruiken. Gebruik een vertrouwde installatie;
  dit is geen sandbox tegen andere processen onder hetzelfde account.

Maximaal 5.000 fictieve bestanden en 2 MiB inhoud worden aangemaakt. Er is een
controletermijn van 60 seconden voor opbouwen, opwarmen, meten en verificatie.
Een te grote, beschadigde of onveilige manifestbeschrijving geeft een fout,
geen stilzwijgend ingekorte dataset. Opruimen kan extra tijd kosten; OS-
bestandstoegang is niet overal hard onderbreekbaar. De bestaande beperkingen
voor netwerk-mounts en gelijktijdige padvervanging blijven gelden.

Bij een gewone fout of `Ctrl+C` wordt opruimen van de eigen map nog geprobeerd.
Bij een geforceerde processtop, systeemuitval of mislukte veiligheidscontrole
kunnen fictieve bestanden onder de genoemde prefix achterblijven. Er is geen
automatische zoek-/verwijderactie voor oude mappen. Verwijder achterblijvers
alleen zelf na controle; ruim nooit op door echte projectmappen te wissen.

## Uitvoer en exitcodes

Tekst, JSON en Markdown komen uit hetzelfde rapportmodel. Er wordt geen
rapportbestand bewaard. JSON heeft de bestaande basisvelden, `command:
"benchmark"`, `tests_requested: false` en een extra `benchmark`-object:

- `projects`, `repeat`, `warmup_runs` en de verdeling `project_types`;
- `timings`, met per onderdeel `samples_ms`, minimum/mediaan/gemiddelde/maximum
  en `projects_per_second`;
- `dataset_unchanged` en `temporary_files_removed`;
- `scope: "synthetic_temporary_projects"` en `project_tests_executed: false`.

Alleen `true` bevestigt een afgeronde datasetcontrole of opruiming. `false`
bij een afgebroken run betekent niet geverifieerd of mislukt; kijk ook naar
`completion`, resultaten en exitcode. Een deels gevuld `timings`-veld bij een
fout of onderbreking mag je niet als complete benchmark presenteren. Absolute
tempnamen en echte projectnamen worden niet in het rapport opgenomen.

| Exitcode | Betekenis |
| --- | --- |
| `0` | Metingen en verificatie afgerond; eigen tijdelijke map opgeruimd. |
| `1` | Onveilige locatie, ongeldige dataset, afwijkend resultaat, limiet of opruimfout. |
| `2` | Ongeldige CLI-opties of omvang, zonder benchmark uit te voeren. |
| `3` | Rapport kon niet veilig naar stdout worden geschreven. |
| `130` | Benchmark geannuleerd; controleer de gerapporteerde opruimstatus. |

## Tests

```powershell
python -B -m unittest discover -s tests -p test_benchmark.py -v
python -B -m unittest discover -s tests -v
```

De tests controleren de vier fictieve types, rekenregels, afwezigheid van
subprocessen/netwerk, tijdelijke paden, ongewijzigde test-sentinels,
omvanggrenzen, annuleren en begrensd opruimen. Zie ook [quality](QUALITY.md)
en [beveiliging](SECURITY.md).
