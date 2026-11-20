# Het interactieve Studio-menu

Start vanuit de studiohoofdmap in een gewone PowerShell-terminal:

```powershell
python .\studio.py
```

Of geef de projectroot expliciet mee:

```powershell
python .\studio.py menu --root "C:\App\Codex\Projects"
```

Zonder expliciete root vraagt het menu bij een projectactie om de projectmap;
Enter gebruikt daar `$HOME\Projects`. Een projectnaam is één directe mapnaam,
bijvoorbeeld `codex-eerste-project`, geen volledig pad. De bestaande
naamvalidatie, symlink-/junctioncontroles en metadatacontroles blijven gelden.
Het generatormenu vraagt zelf om de oudermap voor een nieuw project.

## Een keuze maken

Het menu toont projecten, check, updates, dashboard, quality, maintenance,
back-up, herstel, optionele project-/studiotests, releasevoorcontrole,
benchmark en het bestaande generatormenu. Het menu voert één gekozen actie
uit en geeft de bijbehorende exitcode terug. Open het opnieuw voor een volgende
actie. Ongeldige keuzen starten niets en vragen opnieuw om een getoond nummer.

Het menu hergebruikt de bestaande Python-functies en CLI-opdrachten. Er wordt
geen shell-commandotekst opgebouwd, niets geïnstalleerd en geen Git-geschiedenis
gewijzigd. Er wordt niets automatisch gerepareerd of gepubliceerd. Alleen-lezen
Git-controles van de bestaande functies blijven mogelijk.

## Toestemming vóór schrijven of tests

- List, check zonder tests, updates, quality zonder tests, maintenance en
  releasevoorcontrole lezen alleen. Het dashboard start een lokale alleen-lezen
  server; stop deze met Ctrl+C. Er worden geen rapportbestanden aangevraagd.
- Back-up en herstel tonen standaard uitsluitend hun bestaande overzicht en
  controles. Enter, `nee` of een ander antwoord dan `ja` op de aanvraagvraag
  laat deze acties alleen lezen. Ook na `ja` moet je de gecontroleerde selectie
  en bestemming bekijken en exact `BACKUP projectnaam` of `HERSTEL doelmapnaam`
  typen. Het menu vult deze bevestiging nooit voor je in.
- Project- en studiotests voeren code uit en kunnen bestanden wijzigen,
  processen starten en netwerkverkeer veroorzaken. De bestaande controle toont
  eerst de waarschuwing en vaste testopdracht en vraagt zelf om `ja`. Zonder die
  bevestiging starten geen tests. Bij onveilige of ontbrekende voorwaarden
  kunnen tests ook worden overgeslagen of geweigerd.
- De benchmark maakt en verwijdert eigen tijdelijke fictieve bestanden. Het
  menu vraagt vooraf om exact `ja` voor twaalf projecten en drie metingen.
- Een nieuw project gebruikt het bestaande generatormenu: het doel wordt
  getoond en pas na `ja` aangemaakt. Bestaande doelmappen worden geweigerd.

## Annuleren en grenzen

In het hoofdmenu stoppen Enter, `0` en `q`. Bij vervolgvragen annuleert `q` of
`annuleren`; Ctrl+C en einde invoer breken de invoer ook af. Enter kiest alleen
een uitdrukkelijk getoonde standaardwaarde, zoals de root of alleen-lezen modus;
bij verplichte invoer annuleert Enter. In de bestaande bevestigingsvraag voor
schrijven annuleert elk antwoord behalve de exacte bevestiging.

Annuleren vóór bevestiging start geen schrijfactie of tests. Annuleren tijdens
een al bevestigde actie draait eerdere wijzigingen niet terug; volg de
[back-uphandleiding](BACKUPS.md), [herstelhandleiding](RESTORE.md) en
[testwaarschuwingen](QUALITY.md). Een onvolledige nieuwe map of ZIP kan blijven
bestaan. De benchmark ruimt uitsluitend zijn eigen gecontroleerde data op.

Het menu vereist een interactieve terminal en weigert omgeleide standaardinvoer.
Voor scripts en JSON gebruik je de bestaande directe opdrachten; die blijven
ongewijzigd beschikbaar, bijvoorbeeld:

```powershell
python .\studio.py list --root "C:\App\Codex\Projects"
python .\studio.py quality --format json
```

Het menu is geen sandbox tegen andere processen of tegen code die je zelf als
test laat uitvoeren. Zet geen secrets in projectnamen, paden of metadata.
