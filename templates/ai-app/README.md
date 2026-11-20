# PROJECT_NAME

Een minimaal Python-project dat is voorbereid op AI-functionaliteit, met alleen
de standaardbibliotheek. De voorbeeldapp gebruikt uitsluitend een lokale
nepclient: hij voert geen AI-model uit en verstuurt geen API-aanroepen.
Er zijn geen API-sleutel, betaalde dienst of extra pakketten nodig.

## Uitvoeren zonder installatie

Gebruik Python 3.11 of hoger. Voer vanuit de projecthoofdmap in PowerShell uit:

```powershell
python -m unittest discover -s tests -v
Push-Location .\src
python -m project_package
Pop-Location
```

De generator vervangt `project_package` door je eigen packagenaam. Bij handmatig
kopiëren vervang je `PROJECT_NAME` en `project_package` in inhoud en mapnamen zelf.
De uitvoer met standaardconfiguratie is:

```text
[demo:demo-model] Geef een korte begroeting.
```

Dit project werkt zelfstandig, zonder bestanden of een omgeving van de studio.

## Configuratie

| Omgevingsvariabele | Standaard | Betekenis |
| --- | --- | --- |
| `AI_MODE` | `mock` | Alleen deze offline modus wordt ondersteund. Andere waarden geven een fout. |
| `AI_MODEL` | `demo-model` | Naam voor het demoantwoord; er wordt geen echt model gestart. |
| `AI_API_KEY` | Leeg/afwezig | Gereserveerd voor een toekomstige provider. Wordt door de nepclient niet gebruikt. |

Voorbeeld met tijdelijke procesvariabelen, zonder sleutel, vanuit de projectmap:

```powershell
$env:AI_MODE = "mock"
$env:AI_MODEL = "demo-test"
Push-Location .\src
python -m project_package
Pop-Location
```

Deze toewijzingen gelden voor de huidige PowerShell-sessie en processen die je
daaruit start. Ze vervangen eventuele eerdere waarden; gebruik bij voorkeur
een nieuwe terminal voor de demo en sluit die daarna om de wijzigingen te laten
vervallen. Zet geen echte sleutel in opdrachten die in je shellgeschiedenis komen.

`.env.example` bevat alleen voorbeeldconfiguratie met een lege sleutel. Python
laadt dit bestand of een `.env` niet automatisch. Er is geen dotenv-pakket nodig.
Een echte sleutel toevoegen verandert de demo niet in een echte AI-koppeling.

## Structuur en uitbreiden

- `src/project_package/config.py`: leest bekende omgevingsvariabelen en valideert ze.
- `client.py`: het `TextClient`-contract en de lokale `MockClient`.
- `service.py`: invoervalidatie en aanroep van de gekozen client.
- `__main__.py`: offline voorbeeldapp met een vaste, fictieve prompt.
- `tests/test_ai.py`: configuratie-, client-, foutafhandelings- en app-tests.
- `pyproject.toml`: alleen projectmetadata, zonder externe afhankelijkheden.
- `.github/workflows/ai-tests.yml`: offline tests op GitHub Actions.

Het contract beschrijft een `complete(prompt, model=...)`-methode. De service kan
een andere client ontvangen, zodat tests een testdubbel kunnen gebruiken.
Een echte provideradapter, SDK, endpoint en kostenbeheer zijn bewust nog niet
ingericht. Bespreek die als aparte uitbreiding, inclusief toestemming, privacy,
timeouts en kostenlimieten. Het template schakelt nooit automatisch naar live om.

## Tests, veiligheid en GitHub

De 13 unittest-tests gebruiken expliciete fictieve configuratie of een nagebootste
omgeving; ze hebben geen echte API-sleutels nodig en lezen deze niet uit jouw
omgeving. Socketverbindingen en DNS-opzoekingen worden tijdens iedere test
geblokkeerd. Nieuwe tests moeten dezelfde offline aanpak behouden.

Elke nieuwe testmodule moet vóór package-imports het eigen `src`-pad beschikbaar
maken zoals `test_ai.py` doet. Vertrouw niet op de importvolgorde van andere tests.

De sleutel is verborgen in de gewone `repr` van de configuratie. Dat is geen
encryptie: druk geen volledige configuratiedictionaries af en log geen prompts
met persoonlijke gegevens. `.gitignore` is geen bescherming voor al gevolgde
bestanden. Controleer nieuwe bestanden en commits altijd op gevoelige inhoud.

De workflow werkt wanneer het project de hoofdmap van een GitHub-repository is.
Hij test Python 3.11 en 3.14 op Windows en Linux zonder installs of eigen secrets.
Hij maakt geen repository aan en publiceert niets. Lees `AGENTS.md` voor de
ontwikkelafspraken.
