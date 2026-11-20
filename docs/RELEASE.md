# Een release lokaal voorbereiden, handmatig vrijgeven

`release-check` is een lokale voorcontrole van Codex Studio. De opdracht
publiceert **nooit** en geeft geen externe goedkeuring af. Er worden geen commits,
tags, merges, pushes, releases, installaties of Windows-taken gemaakt.
GitHub en andere externe diensten worden niet benaderd.

## Eerst alleen bekijken

Voer vanuit de studiohoofdmap uit:

```powershell
python -B .\studio.py release-check
```

De gecontroleerde map is altijd de map van `studio.py`, ook als je het script
vanuit een andere werkmap aanroept. Net als bij [quality](QUALITY.md) worden
vereiste bestanden, manifest/templates, Python-syntaxis, lokale documentatielinks
en veilige Git-status gecontroleerd. Dit voert geen projecttests uit en schrijft
zonder `--output` geen rapportbestand.

Ontbreekt een kandidaatversie, dan wordt die als niet opgegeven gemeld.
Er wordt geen studioversie afgeleid uit templateversies of administratief
ingevulde projectmetadata. Een gewijzigde werkmap, ontbrekende eigen repository
of onleesbare/onveilige Git-status blokkeert de lokale kandidaat. Er wordt niets
automatisch vastgelegd of weggegooid om dat op te lossen.

## Een kandidaat bewust kiezen

Kies zelf het beoogde versienummer. Onderstaand nummer is een voorbeeld,
geen bestaande of voorgeschreven release:

```powershell
python -B .\studio.py release-check --version 0.1.0
```

Alleen `MAJOR.MINOR.PATCH` zonder voorloopnullen of suffixen wordt geaccepteerd.
Een hogere versie wordt niet automatisch gekozen, gereserveerd of gepubliceerd.

Vul na inhoudelijke beoordeling in [CHANGELOG.md](../CHANGELOG.md) een sectie
voor precies die kandidaat in. Het formaat is bijvoorbeeld:

```markdown
## [0.1.0]

- Beschrijf hier de werkelijk beoordeelde wijzigingen voor deze kandidaat.
```

Een kop met ` - YYYY-MM-DD` erachter is ook toegestaan. Een kop binnen een
codevoorbeeld telt niet. De datum en de inhoudelijke juistheid van notities
blijven handmatig te beoordelen. Een lege sectie of een losse placeholder
zoals `TODO` telt niet als release-notitie.

De huidige changelog bevat alleen `Unreleased`. Dat is bewust geen verzonnen
releasegeschiedenis. Templateversie `1.0.0` en eerder administratief op `1.0.0`
gezette projectmetadata bewijzen geen gepubliceerde studioversie.

Beoordeel wijzigingen en leg ze alleen op eigen opdracht vast via de
[Git-workflow](WORKFLOW.md). De releasecontrole maakt zelf geen commit. Als de
werkmap schoon en veilig leesbaar is, leest de opdracht met een vaste
`rev-parse --verify HEAD` de lokale commit-ID. Die ID dient als handmatige
vergelijking met GitHub; hij bewijst niet dat de remote die commit al bevat.

## Tests uitsluitend na expliciete bevestiging

```powershell
python -B .\studio.py release-check --version 0.1.0 --run-tests
```

Bij een ontbrekende kandidaatversie of een lokale FAIL wordt niet om toestemming
gevraagd en worden geen tests gestart. Anders wordt dezelfde vaste studio-
testsuite gebruikt als bij quality, met dezelfde waarschuwing, limieten en
procesboomopruiming. Alleen `ja` bevestigt; Enter, `nee`, `q`, een ander antwoord
of einde invoer annuleert de teststart. Er wordt geen eerder opgeslagen
testrapport als actueel bewijs overgenomen.

**Tests voeren code uit en kunnen bestanden wijzigen of netwerkverkeer starten.
Dit is geen sandbox.** Vertrouw de studio en tests voordat je instemt. De
releasecontrole zelf start geen publicatieopdrachten, ook niet na geslaagde tests.

Na geslaagde tests worden de lokale controles opnieuw uitgevoerd. HEAD moet nog
dezelfde zijn en de werkmap moet nog schoon zijn. Mislukte tests, gewijzigde
bestanden of een gewijzigde commit blokkeren de kandidaat. Overgeslagen tests
blijven zichtbaar in het testresultaat en moeten handmatig worden beoordeeld.
De standaardmodus voert deze tests niet automatisch uit.

## Drie lokale uitkomsten, nooit automatische vrijgave

| Release-status | Betekenis |
| --- | --- |
| `BLOCKED` | Een lokale controle faalde. Los die bewust op en controleer opnieuw. |
| `LOCAL_INCOMPLETE` | Geen lokale FAIL, maar bijvoorbeeld geen versie of geen geslaagde testuitvoering. |
| `MANUAL_REQUIRED` | De beperkte lokale vereisten slagen; externe en inhoudelijke controles staan nog open. |

`local_ready: true` betekent alleen: kandidaat en changelog zijn lokaal
gecontroleerd, er is een schone lokale commit en de vaste testsuite slaagde.
Het betekent geen security-goedkeuring, compatibiliteitsgarantie, toestemming
om te publiceren of verificatie van overgeslagen tests. Ontbrekende web-, AI-
en automation-templatebronnen die op deze branch als gepland zijn gedocumenteerd
blijven WARN; claim ze niet als beschikbaar releaseonderdeel.

De opdracht kan zelf niet vaststellen dat de volgende controles afgerond zijn.
Ze blijven in ieder rapport **HANDMATIG_TE_VERIFIEREN**:

| Controle | Wat jij zelf verifieert |
| --- | --- |
| GitHub Actions | Alle vereiste workflows slagen voor precies de gerapporteerde commit, niet alleen voor een eerdere branchversie. |
| Pull request en reviews | Juiste repository, doelbranch, actuele PR en vereiste onafhankelijke beoordelingen. |
| Branchbescherming | Ingestelde branchregels en verplichte externe statuschecks. |
| Secrets en afhankelijkheden | Relevante externe scans, meldingen en bewuste beoordeling van gevoelige inhoud. |
| Platforms en herstelproef | Ondersteunde Windows/Python-versies, browsergedrag, overgeslagen tests en een passende back-up/herstelproef. |
| Versie, artefacten en toestemming | Definitieve bestanden, release-notities, eventuele externe tags/releases en afzonderlijke publicatietoestemming. |

Leg bewijs en beslissingen buiten dit rapport vast bij de betreffende kandidaat,
bijvoorbeeld in de pull request. Deel geen secrets. Een later gewijzigde commit
vraagt opnieuw passende controles. Er is geen vlag om externe controles lokaal
op goedgekeurd te zetten en geen `--publish`, `--push` of automatische workflow.
Deze opdracht zal ook na jouw eigen handmatige verificatie zelf nooit publiceren.

## Rapporten en exitcodes

Dezelfde veilige uitvoer als bij quality is beschikbaar:

```powershell
python -B .\studio.py release-check --version 0.1.0 --format json
python -B .\studio.py release-check --version 0.1.0 --format markdown --output "C:\App\Codex\QualityReports\release-kandidaat.md"
```

Bestaande doelen worden geweigerd. Een rapport mag ook geblokkeerde of
onvolledige resultaten bevatten; een aangemaakt bestand bewijst geen vrijgave.
Kies een bestaande rapportmap buiten de studiorepository. Een nieuw rapport
binnen de repository maakt de werkmap na de controle weer gewijzigd; een
herhaalde releasecontrole zal die werkmap dan terecht blokkeren. Het rapport
beschrijft de gemeten lokale commit en is geen voortdurende statusbewaking.
Rapportpaden, extensies, UTF-8, begrenzing en `.incomplete`-bestanden volgen
[de quality-rapportregels](QUALITY.md). Prompts en voortgang staan op stderr,
het volledige eindrapport staat op stdout. Stuur stderr niet naar een JSON-parser.

Het JSON-schema behoudt `schema_version: 1`, `results`, `summary`, `completion`,
`tests_requested` en `exit_code`, maar gebruikt `command: "release-check"`.
Het aanvullende object `release` bevat:

- `version`: de geldige expliciete kandidaat, of `null` bij ontbrekende/ongeldige invoer;
- `commit`: de veilig vastgestelde lokale HEAD, of `null` als die niet aantoonbaar is;
- `state` en `local_ready`: de lokale uitkomst zoals hierboven beschreven;
- `published`: altijd `false`;
- `manual_checks`: vaste controles met ID, label, uitleg en de status `HANDMATIG_TE_VERIFIEREN`.

De PASS/WARN/FAIL/SKIP-samenvatting telt de lokale resultaten. De handmatige
controles staan daar los van; ze worden niet als lokaal geslaagd meegeteld.
Ook bij een fatale controlefout, annulering of rapportagefout blijft de
handmatige lijst zichtbaar. `completion: complete` betekent alleen dat de
controle is afgerond, niet dat een release is vrijgegeven.

| Exitcode | Betekenis |
| --- | --- |
| `1` | Lokale kandidaat geblokkeerd of controle mislukt. |
| `2` | Ongeldige CLI-opties; gebruiksuitleg op stderr. |
| `3` | Rapportdoel ongeldig/bestaand/onveilig of rapport niet veilig afgeleverd. |
| `4` | Geen lokale FAIL, maar lokale of handmatige verificatie staat nog open. Dit is **geen publicatiegoedkeuring**. |
| `130` | Onderbroken tijdens controle of draaiende tests. |

Deze opdracht geeft bewust geen exitcode `0` als algemene releasevrijgave.
`quality` behoudt zijn bestaande exitcodes. Gebruik geen `&& publish`-keten of
andere automatische publicatiestap op basis van een lokaal rapport.

## Veiligheidsgrenzen

Geen netwerkverzoeken, dependency-installaties, wijzigingen aan Git-geschiedenis
of repository-instellingen. Alleen de bestaande veilige lokale Git-controles en
de vaste HEAD-leesopdracht worden gebruikt; geen fetch, pull, push, commit, tag,
merge of release-API. Broncode en begrensde changelog worden gelezen zonder ze
te importeren of uit te voeren. Tests en rapportbestanden zijn optioneel en
volgen hun expliciete vlaggen en toestemming.

De bestaande limieten voor bestanden, directorybomen, subprocessuitvoer en
time-outs blijven gelden. Gebruik een vertrouwde lokale studiomap zonder
gelijktijdige padwijzigingen. Dit is geen sandbox tegen andere processen onder
hetzelfde account. Zie [beveiliging](SECURITY.md) en [de projectchecklist](PROJECT_CHECKLIST.md).

## Tests van de releasecontrole

```powershell
python -B -m unittest discover -s tests -p test_release_check.py -v
python -B -m unittest discover -s tests -v
```

Tests gebruiken tijdelijke mappen en mocks voor Git, testsuite en externe
uitkomsten. Er worden geen echte commits, tags, pushes of releases gemaakt.
