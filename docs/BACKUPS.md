# Een lokale broncodeback-up maken

Deze functie bewaart een beperkte selectie broncode, tests, documentatie en
bekende configuratie in een ZIP. Het is geen volledige kopie van je project:
gegevens, secrets, Git-geschiedenis en lokale omgevingen vallen buiten de selectie.
De werking is hetzelfde voor Python, web, AI en automation; de aanwezigheid van
een templatebron is hiervoor niet nodig.

## 1. Bekijk eerst de selectie

Open PowerShell in de studiohoofdmap. Het project moet als directe map onder
de root staan en een geldige `.codex-studio.json` hebben:

```powershell
python -B .\studio.py backup mijn-project --root "C:\App\Codex\Projects"
```

Vervang `mijn-project` door de eigen projectmapnaam. Zonder `--root` wordt
`$HOME\Projects` gebruikt. Ontbrekende of ongeldige metadata wordt geweigerd;
de back-upfunctie maakt of herstelt geen metadata en verzint geen versies.
Een expliciet onbekende versie (`null`) is wel geldig.

Je ziet bron, voorgesteld doel, alle geselecteerde bestanden met grootte,
uitsluitingen met reden en de totale ongecomprimeerde grootte.
Uitgesloten mappen worden als één item getoond: hun inhoud wordt niet bekeken.
Het overzicht leest geen broncode-inhoud en maakt geen map, archief, log of
planbestand aan. Alleen de benodigde projectmetadata wordt inhoudelijk gelezen.

Standaard is de voorgestelde bestemmingsmap `$HOME\StudioBackups`. Kies eventueel
een andere lokale map met `--output`. De ouder van die map moet al bestaan;
de bestemmingsmap zelf mag pas na bevestiging worden aangemaakt.

## 2. Geef expliciet toestemming voor aanmaken

```powershell
python -B .\studio.py backup mijn-project --root "C:\App\Codex\Projects" --output "$HOME\StudioBackups" --create
```

Ook met `--create` volgt eerst een nieuw overzicht. Iedere aanroep krijgt een
nieuwe voorgestelde naam met UTC-tijd en een willekeurig achtervoegsel.
Controleer dus opnieuw de selectie en het getoonde doel. Daarna typ je exact:

```text
BACKUP mijn-project
```

`ja` is geen geldige bevestiging. Enter, `nee` of een ander antwoord annuleert.
`Ctrl+C` of einde invoer annuleert eveneens. Er is bewust geen `--yes`-optie:
doorgepijpte invoer en niet-interactieve aanroepen mogen geen back-up aanmaken.
De toestemming om deze functie te bouwen is geen toestemming voor een back-up
van echte projecten. Codex vraagt daarvoor afzonderlijk toestemming.

## Wat gaat wel en niet mee?

| Selectie | Beleid |
| --- | --- |
| Broncode en documentatie | `.py`, `.html`, `.css`, `.js`, `.mjs`, `.cjs`, `.md`, `.rst` in de hoofdmap of onder `src`, `tests`, `public`, `docs`, `dashboard`. |
| Bekende configuratie in de hoofdmap | `pyproject.toml`, `package.json`, `requirements.txt`, `.gitignore`, `.gitattributes`, `.codex-studio.json`, `LICENSE`, `COPYING`. |
| GitHub Actions | Alleen `.yml`/`.yaml` rechtstreeks onder `.github/workflows`. |
| Mogelijk gevoelig | `.env` en alle varianten, inclusief `.env.example`; sleutels/certificaten en namen met onder andere `secret`, `credential`, `password`, `token`, `api_key`, `private` worden uitgesloten. |
| Gegevens en resultaten | Onder andere `data`, `gegevens`, `personal`, `persoonlijk`, `private`, `uploads`, `downloads`, `documents`, databases, CSV/Excel, logs en archieven worden uitgesloten. |
| Omgevingen en administratie | Onder andere `.git`, `.venv`, `venv`, `env`, `node_modules`, `__pycache__`, `.aws`, `.ssh`, `.vscode`, `.idea`, build/output/back-upmappen worden uitgesloten. |
| Onbekende bestanden of mappen | Niet op de positieve lijst betekent uitsluiten; ook een willekeurig `.txt`-bestand gaat niet automatisch mee. |

Uitsluitingen gaan vóór toelating: ook `src/client_secret.py` en
`docs/token.md` vallen dus buiten de back-up. Er is in deze eerste versie geen
vlag om gevoelige bestanden toch mee te nemen. Pas zulke bestanden niet alleen
van naam aan om ze alsnog mee te laten nemen.

**Bestandsnamen herkennen niet alle gevoelige inhoud.** Een toegestane README,
broncode- of configuratiefile kan alsnog een geheim bevatten. Controleer dat
zelf zonder sleutels in logs of chat te plakken. Ook projectmetadata kan
persoonlijke opmerkingen bevatten. De functie geeft geen garantie dat de
selectie vrij is van secrets. De ZIP is **niet versleuteld**; bewaar hem in een
lokale map met passende toegangsrechten en geen onbedoelde cloudsynchronisatie.

## Veiligheidscontroles en foutafhandeling

- Geen projectcode, tests, shell, Git, installaties of netwerkverzoeken.
  Er is geen back-uproute of schrijfknop in het dashboard.
- Bron en bestemming moeten rechtstreekse lokale paden zijn. De bestemming mag
  niet binnen het project liggen. UNC-, device-, drive-relative paden en
  Windows-datastromen worden geweigerd; gekoppelde netwerkschijven eveneens.
- Symlinks, junctions, bijzondere bestanden en hardlinks worden niet gekopieerd.
  Koppelingen in bron-/doelmap of hun ouders blokkeren de operatie; uitgesloten
  items binnen het project verschijnen in het overzicht.
- Bestaande archieven en `.incomplete`-bestanden worden nooit overschreven.
  De geselecteerde bronbestanden worden na bevestiging opnieuw gecontroleerd,
  bij het openen en lezen gecontroleerd, en vóór publiceren nogmaals vergeleken.
  Een gewijzigde selectie vereist een nieuw overzicht en nieuwe toestemming.
- De ZIP wordt eerst exclusief als `.zip.incomplete` geschreven. Daarna worden
  de inhoud en SHA-256-controlesommen gecontroleerd. Een extra bestand
  `_CODEX_BACKUP.json` beschrijft de opgenomen bestanden en hun controlesommen;
  het bevat geen absolute bronpaden of inhoud van uitgesloten bestanden.
- Publiceren gebruikt een hardlink, zodat een bestaand einddoel niet kan worden
  vervangen. Hiervoor moet de bestemmingsschijf hardlinks ondersteunen, op
  Windows bijvoorbeeld NTFS. FAT/exFAT wordt niet via een onveilige fallback
  ondersteund. Alleen na succesvolle publicatie wordt het eigen tijdelijke
  archief verwijderd.
- Bij een fout of onderbreking na bevestiging kan een nieuwe map of
  `.incomplete`-bestand achterblijven. Gebruik dat niet als geslaagde back-up.
  Bij een fout tijdens publiceren kan ook de eind-ZIP bestaan; beoordeel het
  resultaat dan eerst. De functie ruimt mislukt werk niet automatisch op.
- Maximaal 3.000 bekeken items, 1.000 geselecteerde bestanden, 16 MiB per bestand
  en 100 MiB totaal ongecomprimeerd. Archiefpaden zijn maximaal 300 tekens en
  25 onderdelen. Het overzicht en het aanmaken hebben elk een termijn van
  60 seconden; wachten op jouw antwoord telt niet mee. Bij grensoverschrijding
  wordt geen stilzwijgend ingekorte back-up als geslaagd gepresenteerd.

Bestandstoegang is geen transactionele momentopname. Gebruik een vertrouwde map
zonder gelijktijdige wijzigingen. Dit is geen sandbox tegen andere processen
onder hetzelfde account en geen garantie tegen bewust vervalste tijdstempels.
OS-bestandsoproepen kunnen niet universeel met een harde deadline worden
onderbroken. Netwerk-mounts onder lokale paden op andere besturingssystemen en
netwerkactiviteit van filesystemdrivers/synchronisatie vallen buiten deze controle.

Afsluitcodes: `0` voor een geslaagd overzicht, bewuste weigering bij de vraag of
geslaagde back-up; `1` bij fouten; `2` bij ongeldige CLI-opties; `130` bij
`Ctrl+C` of einde invoer tijdens de opdracht. Na een geslaagde schrijfactie
verschijnt expliciet **Back-up gemaakt en geverifieerd** met het eindpad.

## Testen en herstellen

```powershell
python -B -m unittest discover -s tests -p test_backup.py -v
python -B -m unittest discover -s tests -v
```

De tests schrijven uitsluitend naar tijdelijke testmappen en bootsen de
toestemming na. Gebruik de [herstelhandleiding](RESTORE.md) om een archief opnieuw
te verifiëren en optioneel na bevestiging naar een **nog niet bestaande map**
te herstellen. Een verificatie tijdens aanmaken vervangt geen latere herstelproef.
Uitgesloten gegevens en secrets worden niet teruggezet.

Zie ook de [workflow](WORKFLOW.md), [projectchecklist](PROJECT_CHECKLIST.md) en
[beveiligingsbeperkingen](SECURITY.md).
