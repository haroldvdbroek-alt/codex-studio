# Veilig werken met het lokale dashboard

De [benchmark](BENCHMARK.md) gebruikt uitsluitend zelfgemaakte tijdelijke
fictieve projecten. Hij accepteert geen projectroot, start geen projectcode of
tests en verwijdert alleen zijn eigen op identiteit en begrenzing gecontroleerde
tempmap. De resultaten komen op stdout; echte projectmappen blijven ongemoeid.

De [CLI-back-upfunctie](BACKUPS.md) en [herstelfunctie](RESTORE.md) staan los van
HTTP. Het dashboard blijft alleen-lezen en heeft geen route om een back-up,
herstel of andere schrijfactie te starten.

Ook [quality](QUALITY.md) is alleen een CLI-opdracht. De standaardmodus leest
broncode voor syntaxiscontrole en start alleen de bestaande alleen-lezen
Git-controles. `--run-tests` vereist de waarschuwing en expliciete bevestiging;
tests kunnen bestanden wijzigen en zijn geen beveiligingssandbox.
Alleen een expliciete `quality --output` bewaart een nieuw rapportbestand.
JSON en Markdown delen hetzelfde resultaatmodel; prompts staan op stderr.
Rapportdoelen worden gecontroleerd op bestaande bestanden, onveilige paden en
koppelingen. Rapporten kunnen relatieve bestandsnamen bevatten en zijn niet
versleuteld; controleer ze voordat je ze deelt.

Het [PowerShell-script voor Taakplanner](TASK_SCHEDULER.md) voert uitsluitend
quality zonder tests uit. Het registreert geen taak, wijzigt geen uitvoerpolicy
en installeert niets. Een eventuele planning ontstaat pas wanneer de gebruiker
die zelf bewust in Windows Taakplanner opslaat.

De [lokale releasecontrole](RELEASE.md) publiceert nooit en doet geen netwerk-
of release-API-aanroepen. GitHub Actions, reviews en andere externe vereisten
blijven handmatig te verifiëren. Een lokaal rapport is geen vrijgavebewijs;
zelfs zonder lokale fouten is de release-check-exitcode `4`, niet `0`.

De [lokale releasecontrole](RELEASE.md) publiceert nooit. Externe Actions-runs,
reviews, branchregels en publicatietoestemming blijven handmatig te verifiëren.
Een lokaal rapport kan die controles niet goedkeuren of een release maken.

Start vanuit de hoofdmap in PowerShell:

```powershell
python studio.py dashboard --root "C:\App\Codex\Projects"
```

Of gebruik `python studio.py dashboard` voor `$HOME\Projects`. Je hebt Python
3.11 of hoger nodig, zonder extra pakketten. De root moet al bestaan.
Open het getoonde adres, bijvoorbeeld `http://127.0.0.1:54321/`, in een moderne
browser. De poort wordt automatisch gekozen en kan bij iedere start anders zijn.
De browser wordt niet automatisch gestart. Stop in dezelfde PowerShell met
`Ctrl+C`. Het afronden van de lopende achtergrondcontrole kan circa 17 seconden
duren. Alleen een browsertab sluiten stopt de server niet.

## Wat het dashboard doet

- Het leest metadata uit directe projectmappen en toont type en templateversies.
- Het hergebruikt de configuratie- en Git-controles van `studio.py`.
- Git gebruikt vaste, alleen-lezen opdrachten, zonder shell en met begrensde
  uitvoer en tijdslimieten. Filters, hooks en externe configuratie-includes
  worden uitgeschakeld of geweigerd. Er wordt niet gefetcht of gepusht.
- Tests staan altijd op `NIET_UITGEVOERD`. Er is geen HTTP-route om tests,
  opdrachten, installaties of bestandsbewerkingen te starten.
- Het voert geen projectmodules, projecttests of project-startuphooks uit.
  De scanner draait via een vaste lokale Python-opdracht met `-I -S -B`.
- Het schrijft geen projectbestanden, caches, logbestanden of metadata.
  De server bewaart alleen het laatste overzicht in het geheugen.

Een scan begint bij het starten. Na iedere afgeronde scan wacht de scanner
30 seconden voor de volgende. De browser haalt iedere 5 seconden het laatst
beschikbare overzicht op; de knop doet hetzelfde en start geen nieuwe scan.
De getoonde tijd is het moment van ophalen, niet het tijdstip van de scan.
Bij een mislukte scan worden oude projectstatussen vervangen door een melding.
`FAIL` voor configuratie betekent dat een vereiste configuratie ontbreekt,
ongeldig of onveilig is. `WARN` voor Git betekent bijvoorbeeld wijzigingen
of geen eigen repository. `SKIP` betekent dat een controle niet veilig kon
worden uitgevoerd, bijvoorbeeld door een te grote Git-administratie.

`ACTUEEL` vergelijkt uitsluitend versienummers in projectmetadata en het lokale
manifest. Het bewijst geen compatibiliteit, aanwezige templatebronbestanden of
geslaagde tests. Op deze branch zijn alleen Python-templatebronbestanden
aanwezig; web, AI en automation staan wel in het manifest. Ontbrekende of
ongeldige projectmetadata levert een melding op; er wordt niets hersteld.

## HTTP en browserbeveiliging

De server luistert uitsluitend op IPv4 `127.0.0.1`, op een vrije poort.
Alleen deze GET-routes zijn beschikbaar:

| Route | Inhoud |
| --- | --- |
| `/` | Vaste dashboardpagina |
| `/static/style.css` | Lokale stijlen |
| `/static/app.js` | Lokale JavaScript |
| `/api/projects` | Laatste overzicht als JSON |

Andere routes en queryparameters worden geweigerd. Andere HTTP-methoden geven
405 of 404; er is geen mapweergave of algemene bestandsserver. De projectroot
kan alleen bij het starten via de terminal worden gekozen, niet via een URL.
Ook de frontendbestanden worden vóór het starten gecontroleerd op koppelingen.

Host moet exact het getoonde `127.0.0.1:poort` zijn. Een aanwezige Origin moet
bij datzelfde adres horen. Cross-site en same-site browserverzoeken worden
geweigerd via `Sec-Fetch-Site` wanneer die header aanwezig is. CORS wordt niet
opengesteld. CSP staat uitsluitend lokale scripts, stijlen en API-verzoeken
toe en verbiedt framing. Antwoorden bevatten `nosniff`, `no-store`, een
same-origin resourcebeleid en `Referrer-Policy: no-referrer`.
De frontend gebruikt `textContent`, zodat namen en waarschuwingen niet als
HTML worden uitgevoerd. Er zijn geen CDN's, externe assets of externe
netwerkverzoeken; de browser communiceert alleen met de loopback-server.

## Grenzen en beperkingen

- Maximaal 500 directe root-items, 100 projecten en 2.000 items per onderzochte
  Git-administratie. JSON-metadata en manifest zijn maximaal 64 KiB per bestand;
  de API-uitvoer maximaal 512 KiB. Grenzen geven zichtbare meldingen.
- Eén scan tegelijk, met een totale workerlimiet van 12 seconden en maximaal
  1 MiB Git-uitvoer per opdracht. De procesrunner stopt de procesboom bij
  overschrijding; opruimen heeft een aparte begrensde termijn.
- Maximaal acht gelijktijdige HTTP-verzoeken, een kleine wachtrij en een absolute
  verbindingstermijn van drie seconden. Bij overbelasting kan de verbinding
  zonder antwoord worden gesloten. HTTP-headers vallen onder de limieten van
  de standaardbibliotheekserver.
- UNC- en Windows-devicepaden worden geweigerd. Op Windows worden ook gekoppelde
  netwerkschijven en onbekende schijftypes geweigerd. Symlinks en junctions in
  gecontroleerde paden worden niet toegestaan, ook niet binnen de root.
- Gebruik een lokale map die je zelf beheert en een vertrouwde Python- en
  Git-installatie. Gelijktijdige kwaadwillige padvervanging is niet volledig
  uitgesloten. Dit is geen sandbox tegen andere processen onder jouw account.
- Op andere besturingssystemen wordt een netwerkbestandssysteem onder een
  lokaal mountpunt niet betrouwbaar herkend. Windows-filesystemdrivers en
  synchronisatiesoftware kunnen eveneens eigen netwerkactiviteit hebben.
- OS-bestandstoegang en procescreatie kunnen bij systeemproblemen blokkeren;
  de standaardbibliotheek biedt daarvoor geen universele harde deadline.
- Lokale programma's kunnen HTTP-headers nabootsen. Loopback- en
  browserbeveiliging vervangen geen gebruikersauthenticatie. Publiceer deze
  server niet, gebruik geen proxy/tunnel en deel de poort niet.
- De normale Python-start kan systeem- of gebruikers-startuphooks laden.
  Het dashboard zelf laadt uitsluitend vertrouwde studiocode; de achtergrondscan
  schakelt Python-startuphooks expliciet uit.

Zet geen secrets of persoonsgegevens in projectnamen of metadata: die namen
komen in de browser. De scanner leest geen `.env` of gewone broncode-inhoud;
de gecontroleerde `pyproject.toml` wordt wel als configuratie gelezen.
Projectpaden en ruwe subprocessuitvoer worden niet via de API aangeboden.

## Centrale logging en gevoelige gegevens

`studio.py maintenance` gebruikt uitsluitend lokale, begrensde leescontroles van
de studio zelf. De opdracht start geen Git, subprocessen, tests of netwerkverkeer
en heeft geen schrijf- of reparatieopties. Onderzochte code wordt niet uitgevoerd.
Zie [onderhoudscontrole](MAINTENANCE.md) voor het onderscheid tussen vaststellingen,
aanbevelingen en niet-beoordeelde testdekking.

De studio gebruikt `studio_logging.py` voor vaste logcodes en Nederlandse
meldingen. Deze gaan alleen naar **stderr**; resultaten en JSON blijven op
**stdout**. De logger maakt geen logbestanden, gebruikt geen netwerk en verandert
de algemene Python-loggingconfiguratie niet. Alleen een expliciete `--output`
bij een rapportopdracht maakt een rapportbestand; dat is geen automatisch log.

Logs bevatten geen ingevoerde argumentwaarden, ruwe exceptions, tracebacks,
HTTP-verzoeken, bestandinhoud of subprocessuitvoer. Ook onbekende gebeurtenissen
worden vervangen door een vaste melding. Onverwachte fouten geven een veilige
melding en een foutcode. Bij rapportopdrachten blijft ook het foutrapport geldige
JSON als je `--format json` kiest. Ongeldige CLI-argumenten geven exitcode 2 en
gebruiksinformatie op stderr; er ontstaat dan geen JSON-rapport.

Bij een fout kun je de gebeurteniscode delen, bijvoorbeeld `REPORT_WRITE_FAILED`,
zonder de oorspronkelijke exception te delen. Functionele overzichten, paden
bij back-ups/herstel en expliciet opgeslagen rapporten kunnen wel projectnamen
of locaties bevatten. Zet daarom geen secrets of persoonsgegevens in namen of
metadata en controleer rapporten voordat je ze deelt. Door zelf `2>` te gebruiken
in PowerShell kun je stderr bewust bewaren; bescherm dat bestand dan zelf.

## Tests uitvoeren

Vanuit de studiohoofdmap:

```powershell
python -B -m unittest discover -s tests -v
```

De tests gebruiken tijdelijke mappen, mocks, lokale loopback-verbindingen en
een vaste geïsoleerde scanopdracht. Bestaande projecten blijven ongemoeid.
Sommige echte symlink-tests worden overgeslagen als Windows daarvoor geen
rechten geeft; junction-kenmerken worden ook met mocks gecontroleerd.
