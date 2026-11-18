# Codex Development Studio

Codex Development Studio is een herbruikbare werkmap met afspraken voor samenwerken met Codex aan software. De afspraken zijn bruikbaar voor verschillende programmeertalen en soorten projecten.

Deze studio bevat ontwikkelafspraken, een Python-template en een generator voor nieuwe projecten. De generator gebruikt alleen de Python-standaardbibliotheek. Je hebt Python 3.11 of hoger nodig, maar hoeft geen pakketten te installeren.

## Projecten bekijken

Gebruik vanuit de studiohoofdmap:

```powershell
python -B .\studio.py list
python -B .\studio.py list --root "D:\Projecten"
```

De standaardroot is `$HOME\Projects`, onafhankelijk van de standaardmap van de
generator. Alleen directe projectmappen met `.codex-studio.json` worden herkend.
Het overzicht toont naam, type, studioversie, templateversie en locatie. Een
ontbrekende root wordt niet aangemaakt; het commando geeft dan een foutmelding.
Een lege root geeft een leeg overzicht. Er is geen recursieve zoekactie.

Verwachte UTF-8-metadata, met of zonder BOM (maximaal 64 KiB):

```json
{
  "schema_version": 1,
  "project": {"name": "mijn-project"},
  "generator": {"version": "1.0.0"},
  "template": {"id": "python", "version": "1.0.0"}
}
```

Types zijn `python`, `web`, `ai` en `automation`; versies gebruiken drie getallen
zoals `1.0.0`. Bij handmatige registratie mag een versie expliciet `null` zijn:
het overzicht toont dan `onbekend`, zonder een historische versie te verzinnen.
Ontbrekende versievelden blijven ongeldig. Andere velden worden niet getoond. Ongeldige of onleesbare metadata
en koppelingen worden overgeslagen met een waarschuwing zonder metadata-inhoud.
Bij waarschuwingen is de exitcode 1: het overzicht kan onvolledig zijn. Zonder
problemen is de exitcode 0; ongeldige commandoregelargumenten geven 2.

Unicode blijft behouden bij UTF-8-uitvoer. Bij een beperktere terminalcodering,
zoals CP1252, worden niet-ondersteunde tekens zichtbaar ge-escaped (bijvoorbeeld
`\u6d4b`) zodat ook omgeleide uitvoer niet crasht. Dit wijzigt de metadata niet.

Symlinks en Windows-junctions in root, bovenliggende mappen, projectmappen of
metadata worden geweigerd. Gebruik rechtstreekse, vertrouwde mappen die niet
gelijktijdig door andere processen worden vervangen. Leescontrole en bestandstoegang
zijn geen transactionele momentopname. Het commando voert geen projectcode uit
en leest geen `.env`, broncode of andere projectbestanden.

De huidige generator op deze branch schrijft deze metadata nog niet. Ook
`.codex-project.json` wordt niet als alternatief gelezen. Er worden geen bestanden
hernoemd, toegevoegd of gemigreerd in bestaande projecten. Alleen-lezen betekent
hier geen inhouds- of configuratiewijzigingen; het besturingssysteem kan bij lezen
wel toegangstijden bijwerken. `-B` voorkomt Python-importcachebestanden.

Test het nieuwe commando met `python -B -m unittest discover -s tests -p test_studio.py -v`.

## Wat staat waar?

| Onderdeel | Doel |
| --- | --- |
| `AGENTS.md` | Instructies voor Codex bij het onderzoeken, wijzigen en controleren van projecten. |
| `README.md` | Deze uitleg voor jou als gebruiker. |
| `docs/` | Ruimte voor toekomstige handleidingen en afspraken; momenteel leeg. |
| `create_project.py` | Maakt een zelfstandig Python-project op basis van het template. |
| `tests/` | Automatische tests voor de generator. |
| `templates/` | Startsjablonen; alleen het Python-template is al ingevuld. |
| `templates/ai-app/` | Gereserveerd voor toepassingen met AI. |
| `templates/automation/` | Gereserveerd voor automatiseringen. |
| `templates/python-app/` | Werkend Python-template met src-layout, tests en GitHub Actions. |
| `templates/web-app/` | Gereserveerd voor webtoepassingen. |

## Hoe werk je met de studio?

1. Open deze map in Codex en geef aan aan welk project je wilt werken. Geef bij een bestaand project het juiste pad op.
2. Beschrijf het gewenste resultaat in gewone taal. Vermeld wat wel en niet mag veranderen.
3. Codex onderzoekt eerst het project en de instructies. Bij grotere wijzigingen stelt Codex een kort plan voor.
4. Codex maakt kleine wijzigingen en gebruikt bij een Git-project een aparte branch: een eigen werklijn voor de taak.
5. Codex schrijft passende tests voor veranderd gedrag en controleert het resultaat. Bij documentatie controleert Codex de tekst en verwijzingen.
6. Je krijgt een Nederlandse samenvatting van de wijzigingen, controles en eventuele openstaande punten.

Codex maakt alleen een commit of push als je daar uitdrukkelijk om vraagt. De projectgenerator initialiseert zelf geen Git-repository en maakt geen GitHub-repository aan.

## Een Python-project genereren

Open een terminal in de hoofdmap van deze studio en voer uit:

```text
python create_project.py mijn-notities --type python
```

Dit maakt `Projects/mijn-notities` onder je thuismap. De thuismap wordt bepaald
met `Path.home()` (op veel systemen aangeduid als `$HOME`). De package heet
`mijn_notities`: koppeltekens worden underscores, zodat Python de naam kan importeren.

Je kunt een andere bovenliggende map kiezen:

```text
python create_project.py mijn-notities --type python --output ./projecten
```

Het resultaat staat dan in `./projecten/mijn-notities`. Een relatief pad is relatief
aan je huidige terminalmap. Gebruik aanhalingstekens rond paden met spaties.
De generator vindt het template relatief aan zijn eigen script, ook als je hem
vanuit een andere map aanroept. `--output` ondersteunt ook `~` voor je thuismap.

Projectnamen bevatten maximaal 64 kleine letters, cijfers en enkele koppeltekens.
Begin met een letter en eindig met een letter of cijfer. Spaties, underscores,
punten, padtekens en dubbele koppeltekens zijn niet toegestaan. Namen die door
Windows of Python worden gereserveerd en namen van standaardbibliotheekmodules
(zoals `unittest`) worden geweigerd om conflicten te voorkomen.

De generator vervangt de template-namen in de package, imports, tests, metadata
en documentatie. Alleen de expliciet toegestane templatebestanden worden gelezen
en gekopieerd. Lokale omgevingen, caches, Git-gegevens, `.env`-bestanden en andere
onbekende bestanden worden niet meegenomen. Zet ook in de toegestane
templatebestanden nooit persoonlijke gegevens of secrets: de generator kan de
inhoud daarvan niet automatisch als gevoelig herkennen.

Bestaande doelen worden altijd geweigerd, ook lege mappen, bestanden en kapotte
symbolische koppelingen. Symbolische koppelingen en Windows-junctions in bron-
en doelpaden worden niet gevolgd. Gebruik een rechtstreeks pad. Bij een
schrijffout kan een onvolledige nieuwe projectmap achterblijven; de generator
meldt dit en verwijdert niets automatisch. Gebruik de generator in een map die
je zelf beheert; gelijktijdige wijzigingen aan doelpaden door andere processen
zijn niet ondersteund.

Na het genereren kun je het project meteen testen:

```text
cd projecten/mijn-notities
python -m unittest discover -s tests -v
```

Dit voorbeeld gebruikt de uitvoermap `./projecten` van hierboven. Bij de
standaarduitvoer ga je eerst naar `Projects/mijn-notities` in je thuismap.
Lees de gegenereerde README voor het starten van de app. De meegeleverde workflow
kan op GitHub testen zodra dit project de hoofdmap van een repository vormt;
het uitvoeren van de generator publiceert niets.

## De studio testen

Voer vanuit de studiohoofdmap de generator-tests uit:

```text
python -m unittest discover -s tests -v
```

De tests gebruiken tijdelijke mappen, controleren veiligheidsgevallen en testen
ook een volledig gegenereerd project. Ze schrijven niet naar je echte
`Projects`-map. Symlink-tests worden overgeslagen als het systeem geen koppelingen
toestaat. Test daarna ook het oorspronkelijke template:

```text
cd templates/python-app
python -m unittest discover -s tests -v
```

## Een eerste opdracht

Bijvoorbeeld:

> Onderzoek project [pad naar mijn project]. Leg in eenvoudig Nederlands uit hoe het werkt en hoe ik de bestaande tests kan uitvoeren. Wijzig nog geen bestanden en installeer niets.

Voor een wijziging kun je daarna vragen:

> Voeg [gewenst gedrag] toe aan dit project. Stel eerst een kort plan voor, houd de wijzigingen klein en test het resultaat. Vraag toestemming voor installaties en destructieve opdrachten. Maak geen commit of push.

Vervang tekst tussen vierkante haken door je eigen gegevens. Deel geen wachtwoorden of toegangssleutels.

## Afspraken hergebruiken

De instructies in [AGENTS.md](AGENTS.md) gelden voor deze map en onderliggende projectmappen. Een project kan aanvullende instructies in een eigen `AGENTS.md` hebben; Codex leest die ook voordat het daar wijzigingen maakt.

Wil je de afspraken gebruiken in een project buiten deze studio, laat Codex dan eerst het bestaande project en eventuele instructies onderzoeken. Je kunt daarna vragen de afspraken passend over te nemen. Overschrijf een bestaand instructiebestand niet zomaar. Alleen verwijzen naar een externe projectmap zorgt er niet automatisch voor dat dit bestand daar geldt.

## Waarvoor vraagt Codex toestemming?

Codex vraagt vooraf toestemming voor installaties en voor opdrachten die gegevens kunnen verwijderen of overschrijven. Het verzoek legt uit wat er gaat veranderen en wat de gevolgen zijn. Een al expliciet toegestane handeling hoeft niet opnieuw te worden goedgekeurd zolang die hetzelfde blijft.

Een test controleert of software zich gedraagt zoals bedoeld. Tests geven vertrouwen, maar sluiten niet alle fouten uit. Codex vermeldt daarom ook welke controles niet zijn uitgevoerd. Jij kunt de wijzigingen bekijken voordat je besluit ze vast te leggen of te delen.
