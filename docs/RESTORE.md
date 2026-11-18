# Een broncodeback-up controleren en herstellen

Deze handleiding geldt voor de ZIP-bestanden van [de Studio-back-upfunctie](BACKUPS.md)
en voor Python-, web-, AI- en automation-projecten. De ZIP moet een geldig
`_CODEX_BACKUP.json` bevatten. De controlesommen verifiëren de opgenomen bestanden;
ze bewijzen niet wie het archief gemaakt heeft. Gebruik uitsluitend een back-up
waarvan je de herkomst vertrouwt voordat je de herstelde code ooit uitvoert.

## 1. Kies een voltooid archief en een nieuwe doelmap

Open PowerShell in de studiohoofdmap. Het archief moet een gewoon lokaal
`.zip`-bestand zijn; een `.zip.incomplete`-bestand is geen voltooide back-up.
De **doelmap mag nog niet bestaan**, ook niet als lege map. De ouder van de
doelmap moet wel al bestaan. Kies bij voorkeur een map buiten bestaande projecten.

Gebruik in onderstaande voorbeelden de werkelijke ZIP-naam en eigen doelmap.
De functie kiest bewust geen standaarddoel: jij moet aangeven waar herstel
mag plaatsvinden.

```powershell
python -B .\studio.py restore "$HOME\StudioBackups\project.zip" --output "C:\App\Codex\Projects\project-herstel"
```

Dit verifieert eerst archiefstructuur, manifest, bestandslijst, groottes,
ZIP-CRC en SHA-256-controlesommen. Daarna toont het de opgenomen bestanden en
de voorgestelde nieuwe map. Het leest en decomprimeert het archief voor controle,
maar maakt geen map, bestand, cache, log of herstelplan op schijf aan.
Een ongeldig archief geeft een fout vóór er om toestemming wordt gevraagd.

Het hersteloverzicht vermeldt het aantal oorspronkelijk uitgesloten items.
Dat is geen lijst met terug te halen bestanden: de inhoud van uitgesloten
bestanden en mappen staat niet in de back-up.
Een geldig archief met alleen een manifest geeft een waarschuwing dat er geen
projectbestanden zijn; bevestiging zou dan uitsluitend een lege nieuwe map maken.

## 2. Geef alleen voor de getoonde bestemming toestemming

```powershell
python -B .\studio.py restore "$HOME\StudioBackups\project.zip" --output "C:\App\Codex\Projects\project-herstel" --create
```

Ook dit voert eerst de controles uit en toont het overzicht. Typ vervolgens exact:

```text
HERSTEL project-herstel
```

De naam achter `HERSTEL` is de laatste mapnaam van jouw getoonde doelpad.
Enter, `nee`, `ja` of een ander antwoord annuleert zonder herstel.
`Ctrl+C` en einde invoer annuleren eveneens. Er is geen `--yes`-optie en
doorgepijpte invoer mag geen herstel starten. Toestemming om de functie te bouwen
of een archief te controleren is geen toestemming om echte bestanden te herstellen.

Na bevestiging wordt het archief opnieuw gecontroleerd en vergeleken met het
overzicht, inclusief een SHA-256-controlesom van het gehele ZIP-bestand.
Een gewijzigde bron, gewijzigde doelouder of inmiddels bestaand doel wordt
geweigerd. De nieuwe map wordt exclusief aangemaakt; bestaande bestanden worden
nooit vervangen. De functie gebruikt geen `extractall()`.

## 3. Herken een geslaagd of onvolledig herstel

Bij volledig succes verschijnt:

```text
Hersteld en geverifieerd: ...
```

Alle geschreven projectbestanden zijn dan opnieuw op grootte en SHA-256
gecontroleerd. Namen, imports, inhoud en projectmetadata worden letterlijk
behouden; een nieuwe mapnaam hernoemt de oorspronkelijke package of projectnaam
niet. Daardoor kan `studio.py list` twee projecten met dezelfde naam tonen;
controleer ook hun locatie. Er worden geen versies aangepast.

Tijdens schrijven staat in de nieuwe map `_CODEX_RESTORE_INCOMPLETE.txt`.
Alleen na volledig geverifieerd herstel wordt deze eigen markering verwijderd.
Het interne `_CODEX_BACKUP.json` wordt voor verificatie gebruikt en niet als
extra projectbestand uitgepakt.

Bij fouten of annuleren na het starten kunnen een nieuwe map, deze markering
en gedeeltelijke bestanden achterblijven. Een foutmelding betekent dat je de
hele map als **ONVOLLEDIG** moet behandelen, ook als de markering ontbreekt
door bijvoorbeeld een schrijffout voordat die aangemaakt kon worden.
De functie verwijdert of overschrijft niets om automatisch opnieuw te proberen.
Onderzoek het resultaat en kies bij een volgende poging een andere nieuwe map.
Verwijder een mislukte map alleen na een bewuste controle en expliciete toestemming.

Afsluitcodes in PowerShell (`$LASTEXITCODE`):

| Code | Betekenis |
| --- | --- |
| `0` | Controle geslaagd, bewust bij de vraag geannuleerd, of herstel geslaagd; lees de eindmelding. |
| `1` | Archief/pad ongeldig, controlesom ongelijk, limiet bereikt of herstel mislukt. |
| `2` | Ongeldige CLI-opties, bijvoorbeeld ontbrekend `--output`. |
| `130` | Onderbroken met Ctrl+C of einde invoer tijdens de opdracht. |

## Wat wordt niet hersteld of uitgevoerd?

- Uitgesloten gegevens, databases, secrets, `.env` en `.env.example`, lokale
  omgevingen, logs, caches en Git-geschiedenis komen niet terug.
- Er worden geen projectmodules, tests, scripts, shell- of Git-opdrachten gestart.
- Er worden geen dependencies geïnstalleerd, netwerken benaderd of planningen
  aangemaakt. Het dashboard heeft geen herstelroute of schrijfknop.
- ZIP-permissies, uitvoerbits, links en speciale bestandsmetadata worden niet
  overgenomen. Bestanden krijgen de gebruikelijke toegangsrechten van de nieuwe
  lokale map; kies zelf een bestemming met passende toegangsrechten.

Dit is een broncodeherstel, geen volledige computer- of gegevensrestore. De
herstelchecker accepteert alleen bestanden binnen het huidige broncodeback-upbeleid.
Een willekeurig ZIP-bestand of een oude/onbekende manifestversie wordt geweigerd.
Bij een toekomstige beleidswijziging kan een bewuste compatibiliteitsuitbreiding
nodig zijn; schakel controles niet uit om een fout te omzeilen.

## Beveiligingscontroles en grenzen

- Absolute paden, `..`, lege padonderdelen, backslashes, Windows-datastromen,
  apparaatnamen, te lange namen, stuurtekens en onveilige namen worden geweigerd.
- Dubbele ZIP-namen, hoofdletterconflicten, Unicode-normalisatieconflicten en
  bestanden die ook als map dienen worden geweigerd. Extra of ontbrekende
  bestanden ten opzichte van het manifest blokkeren herstel.
- Symlink- en speciale ZIP-items worden geweigerd. Er worden uitsluitend gewone
  nieuwe bestanden gemaakt. Koppelingen/junctions in het archiefpad of de
  doelouder, netwerkpaden en op Windows gekoppelde netwerkschijven worden geweigerd.
  Ook een bron-ZIP met meerdere hardlinks wordt geweigerd.
- Alleen ZIP Stored en Deflate worden ondersteund. Versleutelde ZIP's,
  ZIP64 en meerdelige ZIP's worden niet ondersteund.
- Maximaal 128 MiB ZIP, 2 MiB centrale ZIP-directory, 4 MiB manifest,
  1.000 projectbestanden, 16 MiB per projectbestand en 100 MiB totale
  projectinhoud. Aantallen en directorygrootte worden vóór de ZIP-parser
  gecontroleerd. Uitgepakte bytes worden ook tijdens lezen begrensd.
- Er geldt een termijn van 60 seconden voor de controle en opnieuw voor de
  schrijffase, inclusief de herhaalde controles. Wachten op toestemming telt
  niet mee. OS-bestandstoegang kan niet universeel hard worden onderbroken.

De ZIP en het manifest samen zijn geen digitale handtekening: iemand die beide
kan aanpassen, kan passende nieuwe hashes maken. Controlesommen detecteren
beschadiging en verschillen, geen betrouwbare herkomst. Ook geldig herstelde
broncode kan onveilig zijn. Gebruik vertrouwde lokale mappen zonder gelijktijdige
wijzigingen. Dit is geen sandbox tegen andere processen onder hetzelfde account.
De beperkingen voor netwerk-mounts, filesystemdrivers en synchronisatie uit
[de back-uphandleiding](BACKUPS.md) gelden hier eveneens.

## 4. Controleer na herstel zonder meteen code te starten

Open eerst de nieuwe map in VS Code. Lees README, AGENTS.md en relevante code.
Vergelijk het resultaat met wat volgens de back-up aanwezig moest zijn.
Een ontbrekende omgevingsconfiguratie of dataset kan terecht uitgesloten zijn;
zet echte secrets niet terug in broncode of Git.

Pas als je de herstelde code vertrouwt, kun je zelf de projecttests uitvoeren
volgens de eigen README. Python/AI/automation gebruiken doorgaans unittest;
voor web kunnen daarnaast de aanwezige Node-tests en een handmatige
browsertest nodig zijn. AI-tests moeten zonder echte sleutels of betaalde
aanroepen blijven werken; automation-tests gebruiken tijdelijke bestanden.
Zie de [workflow](WORKFLOW.md) en [projectchecklist](PROJECT_CHECKLIST.md).

## De herstelfunctie testen

Vanuit de studiohoofdmap:

```powershell
python -B -m unittest discover -s tests -p test_restore.py -v
python -B -m unittest discover -s tests -v
```

De tests gebruiken tijdelijke mappen en bootsen toestemming na. Ze controleren
ook een volledige back-up/herstelronde voor alle vier de projecttypes,
beschadiging, manifestfouten, padmisbruik, bestaande doelen en onderbrekingen.
Er wordt geen herstelproef op echte projecten gedaan zonder afzonderlijke opdracht.
