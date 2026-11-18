# Codex Development Studio — ontwikkelregels

Deze regels gelden voor werk in deze map en de onderliggende mappen. Houd de aanpak onafhankelijk van een programmeertaal, framework of leverancier. Lees ook eventuele aanvullende `AGENTS.md`-bestanden in het project waaraan je werkt.

## 1. Communiceer duidelijk in het Nederlands

- Geef uitleg, plannen, voortgang en samenvattingen in het Nederlands.
- Gebruik eenvoudige taal en leg technische termen kort uit. Bestaande namen in code en opdrachten mogen hun oorspronkelijke taal behouden.
- Benoem aannames en onzekerheden. Vraag om verduidelijking als een onduidelijke keuze grote gevolgen heeft.

## 2. Onderzoek eerst het project

- Bepaal eerst in welke projectmap je moet werken en wat de gebruiker wil bereiken.
- Lees de projecthandleiding, toepasselijke instructies en relevante bestanden voordat je iets wijzigt.
- Onderzoek de structuur, gebruikte technologie, bestaande werkwijze, tests en beschikbare controleopdrachten.
- Controleer bij een Git-repository de huidige branch en niet-opgeslagen wijzigingen. Overschrijf of herstel nooit zomaar werk van de gebruiker.
- Beperk onderzoek en wijzigingen tot wat voor de opdracht nodig is. Wijzig geen andere projecten.

## 3. Stel bij grotere wijzigingen eerst een plan voor

- Geef bij werk over meerdere onderdelen, nieuwe afhankelijkheden of wijzigingen met grote gevolgen vooraf een kort stappenplan.
- Beschrijf het doel, de betrokken onderdelen, risico's en hoe je het resultaat controleert.
- Stel het plan bij als nieuwe informatie de aanpak verandert. Vraag toestemming wanneer een stap die volgens deze regels nodig heeft.
- Voer kleine, duidelijke opdrachten direct uit na het noodzakelijke onderzoek.

## 4. Maak kleine, gerichte wijzigingen

- Werk in kleine stappen die afzonderlijk te begrijpen en te controleren zijn.
- Volg bestaande afspraken en hergebruik bestaande oplossingen waar dat passend is.
- Vermijd ongevraagde herstructurering, nieuwe hulpmiddelen en wijzigingen aan niet-betrokken bestanden.
- Werk documentatie bij als gebruik of gedrag verandert.

## 5. Gebruik Git-branches

- Werk bij wijzigingen aan een Git-project op een aparte taakbranch, bijvoorbeeld `docs/handleiding` of `fix/inloggen`.
- Controleer eerst de Git-status. Wissel niet van branch als bestaand werk daardoor in gevaar komt.
- Is er geen Git-repository, meld dit dan. Initialiseer er alleen een als de opdracht dat toestaat; maak geen repository in een bestaand project zonder toestemming.
- Maak alleen een commit of push als de gebruiker dat uitdrukkelijk vraagt. Een commit legt wijzigingen lokaal vast; een push verstuurt ze naar een externe repository.
- Herschrijf geen Git-geschiedenis en forceer geen push zonder expliciete toestemming.

## 6. Schrijf tests en controleer het resultaat

- Schrijf of pas passende tests aan bij nieuw gedrag en opgeloste fouten. Test het gewenste resultaat, inclusief relevante foutgevallen.
- Gebruik de bestaande testaanpak. Vraag toestemming voordat je hiervoor iets installeert.
- Voer de relevante tests en beschikbare kwaliteitscontroles uit. Breid de controle uit als fouten of risico's daar aanleiding toe geven.
- Controleer bij alleen documentatie de inhoud, voorbeelden, verwijzingen en onderlinge consistentie; daarvoor zijn geen nieuwe geautomatiseerde tests nodig.
- Meld welke controles zijn uitgevoerd, wat het resultaat was en wat niet kon worden gecontroleerd. Beweer nooit dat een niet-uitgevoerde test is geslaagd.

## 7. Controleer veiligheid en privacy

- Controleer relevante wijzigingen op onveilige invoer, onbedoelde toegang en onnodige rechten.
- Zet geen wachtwoorden, toegangssleutels of persoonsgegevens in code, documentatie, testgegevens, logs of Git. Gebruik fictieve voorbeeldwaarden.
- Lees of deel geen geheimen die niet nodig zijn voor de opdracht. Meld een gevonden probleem zonder het geheim te herhalen.
- Controleer nieuwe afhankelijkheden op noodzaak en veiligheidsrisico's voordat je installatie voorstelt.

## 8. Vraag toestemming voor installaties en destructieve opdrachten

- Vraag vooraf expliciete toestemming voor het installeren, verwijderen of bijwerken van software, pakketten, uitbreidingen en afhankelijkheden. Leg uit wat verandert en waarom.
- Vraag vooraf expliciete toestemming voor opdrachten die gegevens kunnen verwijderen of overschrijven, zoals mappen wissen, databases leegmaken of Git-wijzigingen weggooien.
- Noem bij zo'n verzoek de concrete opdracht, de doelmap of gegevens en de gevolgen. Kies waar mogelijk een omkeerbare aanpak en controleer het doelpad.
- Een algemeen verzoek om iets te bouwen of repareren is geen toestemming voor deze handelingen. Als de gebruiker de concrete handeling al expliciet heeft toegestaan, vraag dan niet opnieuw zolang de reikwijdte gelijk blijft.

## 9. Rond begrijpelijk af

- Vat samen wat is gewijzigd, waarom en hoe het is gecontroleerd.
- Noem resterende problemen en eventuele handelingen die de gebruiker nog moet uitvoeren.
- Houd de uitleg kort genoeg om te volgen en volledig genoeg om het resultaat te beoordelen.
