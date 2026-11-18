# Veilig werken

De studio helpt met vaste afspraken en controles. Je blijft zelf verantwoordelijk
voor de gegevens die je invoert, laat genereren en deelt.

## Secrets en persoonlijke gegevens

Secrets zijn bijvoorbeeld wachtwoorden, API-sleutels, toegangstokens en private
SSH-sleutels. Zet ze niet in code, tests, documentatie, screenshots, prompts of
Git-commits. Gebruik alleen fictieve voorbeeldgegevens. Deel ook geen echte
klantgegevens, privéadressen of persoonlijke exports als testmateriaal.

Het huidige Python-template heeft geen secrets nodig en leest geen `.env`-bestand.
Het bevat geen automatische koppeling met een AI-dienst, database of GitHub-account.
Voeg daarvoor niet alvast echte toegangsgegevens toe.

De generator kopieert alleen expliciet genoemde bestanden per template.
Dat sluit `.venv`, `__pycache__`, `.git`, `.env`, lokale backups en andere onbekende
bestanden uit. Maar gevoelige informatie die je in een toegestaan bestand zet,
zoals README of Python-code, wordt wel meegenomen. Er is geen automatische
herkenning of verwijdering van persoonsgegevens.

Het webtemplate heeft evenmin secrets nodig. Browsercode is voor bezoekers
leesbaar: plaats daar nooit toegangssleutels in. De teller slaat niets op en
gebruikt geen externe assets of netwerkverzoeken. Node.js is alleen nodig voor
automatische JavaScript-tests; ook die gebruiken geen externe pakketten.

Het AI-template is een offline startpunt, zonder echte provider. De configuratie
kan `AI_API_KEY` lezen voor toekomstige uitbreiding, maar de demo heeft die
sleutel niet nodig. Tests geven uitsluitend fictieve waarden door en blokkeren
netwerkverbindingen. Gebruik geen betaalde API-aanroepen als automatische test.
De meegeleverde `.env.example` heeft een lege sleutel. Alleen dat expliciete
voorbeeldbestand mag worden gekopieerd; echte `.env`-bestanden blijven lokaal.
Python leest `.env` niet automatisch in. De sleutel wordt verborgen in de gewone
configuratie-repr; volledige dictionaries of dumps kunnen hem wel onthullen.

Het automation-template gebruikt dry-run als standaard: geen bestanden, mappen
of logbestanden worden geschreven. `--apply` schrijft alleen naar een nieuwe
doelmap en behoudt bronbestanden. De voorbeeldtaak logt geen inhoud, namen of
persoonlijke paden. Test eerst met fictieve gegevens. Een schijffout kan een
gedeeltelijk doel achterlaten; er wordt niets automatisch verwijderd. Gebruik
alleen vertrouwde mappen en kleine tekstbestanden. De dry-run controleert niet
de UTF-8-inhoud of uiteindelijke schrijfrechten.

## Git en publicatie

Controleer voor vastleggen of delen:

```powershell
git status --short
git diff
git diff --cached
```

Open ook nieuwe bestanden. `.gitignore` voorkomt niet dat eerder gevolgde
bestanden opnieuw worden vastgelegd. Het verwijdert evenmin oude commits of
secrets uit de geschiedenis. Ook een private repository is geen kluis voor secrets.

Git-commits bevatten een naam en e-mailadres. Controleer vóór je eerste commit
welke identiteit je wilt gebruiken; GitHub biedt ook een afgeschermd no-reply-adres.

Is een secret al gedeeld? Trek het in of vervang het bij de dienst die het heeft
uitgegeven. Alleen de tekst verwijderen maakt een uitgelekte sleutel niet veilig.
Bespreek daarna hoe de geschiedenis en eventuele kopieën worden opgeschoond;
laat Codex niet zelfstandig Git-geschiedenis herschrijven.

## Mappen en bestandsnamen

De projectnaam is één naam, geen pad. Tekens voor padnavigatie zoals `..`, `/` en
`\` worden geweigerd. Kies de bovenliggende map met `--output`. Een bestaande
doelmap of een bestaand doelbestand wordt nooit bewust hergebruikt, ook niet
wanneer de map leeg is.

De generator controleert op symbolische koppelingen en Windows-junctions: mappen
of bestanden die doorverwijzen naar een andere locatie. Gebruik een rechtstreeks
pad in een map die jij beheert. De controles en schrijfacties zijn afzonderlijke
stappen; de generator is niet bestand tegen een ander proces dat tussendoor
de mappen vervangt. Gebruik hem dus niet in een gedeelde, onbetrouwbare uitvoermap.

Een schrijffout kan een gedeeltelijk project achterlaten. Het script ruimt dat
niet automatisch op. Bekijk eerst het genoemde pad; kies bij twijfel een nieuwe
projectnaam in plaats van bestanden te verwijderen.

## Toestemming en minimale rechten

Volgens [AGENTS.md](../AGENTS.md) vraagt Codex toestemming voor installaties,
updates en destructieve opdrachten. Laat daarbij het doelpad en de gevolgen
uitleggen. Voor het bestaande template zijn geen extra pakketten of
administratorrechten nodig. Verlaag het PowerShell-uitvoeringsbeleid niet om
deze Python-voorbeelden te kunnen volgen.

Een commit, push, Git-initialisatie of nieuwe GitHub-repository gebeurt niet
automatisch. Geef daarvoor een concrete opdracht als je dat werkelijk wilt.
De meegeleverde workflow heeft alleen leesrechten voor repository-inhoud en
bewaart checkout-credentials niet voor volgende stappen. Eigen secrets zijn niet
nodig. Externe Actions blijven externe code: beoordeel wijzigingen eraan voordat
je de workflow overneemt of uitbreidt.

Lees ook [de workflow](WORKFLOW.md) en [problemen oplossen](TROUBLESHOOTING.md).
