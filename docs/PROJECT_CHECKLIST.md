# Herbruikbare projectchecklist

Gebruik deze checklist samen met de [workflowhandleiding](WORKFLOW.md).
Kopieer de tekst naar een taaknotitie of pull request. Afvinken is een bewuste
controle, geen automatische test. Schrijf `n.v.t.` met een korte reden wanneer
een punt niet geldt. Bewaar hier geen secrets, persoonsgegevens of gevoelige paden.

## Taakgegevens

- Project: …
- Type: Python / web / AI / automation
- Taak en gewenst resultaat: …
- Branch, indien van toepassing: …
- Template-/studioversie: …; bron van die informatie: …
- Belangrijkste risico of beperking: …

## Voor het wijzigen

- [ ] Ik werk in de juiste Windows-projectmap en heb dit met `Get-Location` gecontroleerd.
- [ ] README, AGENTS.md, aanvullende instructies en relevante code/tests zijn gelezen.
- [ ] Beschikbare functies en templatebestanden zijn gecontroleerd; gepland gedrag is niet als werkend aangenomen.
- [ ] Git-status en bestaande wijzigingen zijn bekeken; bestaand werk blijft behouden.
- [ ] In een Git-project is een passende taakbranch gekozen; zonder Git wordt niet ongevraagd geïnitialiseerd.
- [ ] Doel, omvang en acceptatiecriteria zijn duidelijk; bij groter werk is een kort plan besproken.
- [ ] Voor benodigde installaties of destructieve opdrachten is expliciete toestemming geregeld.
- [ ] Indien een back-up nodig is: [selectie en uitsluitingen](BACKUPS.md) zijn bekeken; aanmaken is apart toegestaan en vervangt geen gegevensback-up.
- [ ] Indien herstel nodig is: [archief en controlesommen](RESTORE.md) zijn gecontroleerd, de nieuwe doelmap bestaat nog niet en herstel is apart toegestaan.

## Tijdens de wijziging

- [ ] Wijzigingen zijn klein en beperken zich tot de afgesproken taak.
- [ ] Gewijzigd gedrag heeft passende tests, inclusief relevante ongeldige invoer en fouten.
- [ ] Tests gebruiken fictieve gegevens en tijdelijke mappen, niet de echte gebruikersbestanden.
- [ ] Invoer, namen en paden worden gevalideerd waar de toepassing die accepteert.
- [ ] Bestaande doelbestanden worden niet onbedoeld overschreven; symlinks/junctions zijn waar relevant gecontroleerd.
- [ ] Subprocessen, indien nodig, gebruiken vaste argumenten, geen `shell=True`, en passende tijd-/uitvoerlimieten.
- [ ] Code, metadata, logs en documentatie bevatten geen echte sleutels of persoonsgegevens.

## Controle per projecttype

Vul het eigen type in; markeer de andere secties als niet van toepassing.
Op deze branch zijn de web-, AI- en automation-templatebronnen nog niet aanwezig.
De punten gelden ook voor bestaande zelfstandige projecten van die types.

### Python

- [ ] Package en imports passen bij de eigen `src`-layout.
- [ ] Iedere relevante testmodule maakt het eigen `src`-pad beschikbaar vóór package-imports.
- [ ] `python -B -m unittest discover -s tests -v` is vanuit de projecthoofdmap uitgevoerd.
- [ ] De app/startfunctie is volgens de eigen README gecontroleerd, zonder onnodige installatie.

### Web

- [ ] HTML, CSS en JavaScript gebruiken de afgesproken lokale bestanden en geen onbedoelde externe bronnen.
- [ ] Dynamische tekst gebruikt veilige DOM-methoden zoals `textContent`; onbetrouwbare tekst wordt geen HTML.
- [ ] De aanwezige Python-tests zijn uitgevoerd.
- [ ] Indien aanwezig is `node --test tests/counter.test.cjs` uitgevoerd met de vooraf beschikbare Node-installatie.
- [ ] De pagina is handmatig in een browser gecontroleerd, inclusief toetsenbord, focus en foutmeldingen.
- [ ] Bij een server zijn binding, routes, HTTP-methoden, Host/Origin en beveiligingsheaders gecontroleerd.

### AI

- [ ] Echte API-sleutels komen alleen uit de afgesproken lokale omgeving, niet uit code of versiebeheer.
- [ ] Voorbeeldconfiguratie bevat uitsluitend fictieve waarden en beschrijft benodigde variabelen.
- [ ] Tests gebruiken mocks of een nepclient en hebben geen echte API-sleutels of betaalde API-aanroepen nodig.
- [ ] Tests zijn zonder echte netwerkclient uitgevoerd; ontbrekende configuratie en foutantwoorden zijn getest.
- [ ] Logs en foutmeldingen tonen geen sleutels, prompts of andere gevoelige inhoud.

### Automation

- [ ] Veilige testmodus en eventuele schrijfactie zijn volgens de eigen README vastgesteld; vlaggen zijn niet verzonnen.
- [ ] Testmodus verandert geen bestanden, mappen of logs op schijf.
- [ ] Bestandsbewerkingen zijn met tijdelijke bron- en doelmappen getest.
- [ ] Bestaande doelen, onveilige paden, koppelingen en relevante foutgevallen zijn getest.
- [ ] Logging is begrijpelijk en bevat geen gevoelige inhoud.
- [ ] Een echte schrijfactie of terugkerende planning gebeurt alleen na expliciete toestemming voor die handeling.

## Afronden

- [ ] Relevante tests zijn geslaagd; overgeslagen tests en niet-uitgevoerde controles zijn verklaard.
- [ ] Er zijn daadwerkelijk tests gevonden; alleen een exitcode zonder testresultaat is niet genoeg.
- [ ] Indien geregistreerd zijn `studio.py check` en `updates` met de juiste `--root` bekeken.
- [ ] Een dashboardstatus of administratief versienummer is niet als bewijs van geslaagde tests gebruikt.
- [ ] README, configuratievoorbeelden en aanwezige GitHub Actions-workflow passen bij het werkelijke gedrag.
- [ ] Links, paden en PowerShell-voorbeelden in gewijzigde documentatie zijn gecontroleerd.
- [ ] `git diff --check`, `git diff` en `git status` zijn bekeken, indien Git beschikbaar is.
- [ ] Nieuwe en geselecteerde bestanden zijn apart op secrets en onbedoelde inhoud gecontroleerd.
- [ ] Het project is bruikbaar zonder toevallige imports of hulpmiddelen uit de studio; beschrijf wat hiervoor is gecontroleerd.
- [ ] Bij herstel zijn de eindmelding en eventuele ONVOLLEDIG-markering gecontroleerd; code wordt pas na beoordeling uitgevoerd.
- [ ] Wijzigingen, controles en resterende beperkingen zijn in begrijpelijk Nederlands gerapporteerd.
- [ ] Commit, merge, push, installatie en publicatie zijn alleen uitgevoerd als die afzonderlijk waren toegestaan.

## Bewijs en overdracht

| Controle of opdracht | Resultaat | Beperking / reden voor overslaan |
| --- | --- | --- |
| … | … | … |

Niet opgelost / vervolgactie: …

Toestemming voor eventuele volgende actie: …
