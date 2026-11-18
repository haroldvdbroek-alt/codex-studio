# Een release voorbereiden en handmatig publiceren

Een release is een bewust gekozen, geteste versie van de studio. Deze handleiding
publiceert niets: de workflow maakt geen tags, releases, pakketten of deployments.
Ook handmatig starten van de testworkflow publiceert niets.

## 1. Kies de inhoud en versies

Werk op een taakbranch en bekijk vanuit de studiohoofdmap:

```powershell
git status --short --branch
git diff --check
git diff
```

Open ook nieuwe bestanden; `git diff` toont niet automatisch hun inhoud. Bekijk
[de changelog](../CHANGELOG.md) en spreek af welke wijzigingen bij de release horen.
Een generatorversie zoals `1.0.0` in de code betekent niet dat die versie al
als release gepubliceerd is. Gebruik geen verzonnen publicatiedatum.

Er zijn verschillende versies:

| Versie | Waar? | Wanneer aanpassen? |
| --- | --- | --- |
| Studio/generator | `GENERATOR_VERSION` in `create_project.py` | Bij een nieuwe generatorrelease; gebruik dezelfde versie voor de releasetag. |
| Template | `version` per type in `templates/manifest.json` | Als de inhoud van die template verandert. |
| Metadata-/manifestschema | `schema_version` | Alleen als het bestandsformaat verandert, inclusief passende ondersteuning en tests. |
| Gegenereerde app | `version` in template-`pyproject.toml` | Losse beginversie voor de app; onafhankelijk van de studio. |

Gebruik voor generator en templates `MAJOR.MINOR.PATCH`: verhoog major bij
onverenigbare veranderingen, minor voor compatibele functies en patch voor
compatibele correcties. Verander alleen de versies die bij deze release horen.
Eerdere templateversies worden niet automatisch bewaard. Bestaande gegenereerde
projecten worden nooit bijgewerkt door deze procedure.

## 2. Voer de volledige controles uit

Gebruik Python 3.11+ en Node.js 22+. Voer vanuit de studiohoofdmap uit:

```powershell
python --version
node --version
python -B run_tests.py
if ($LASTEXITCODE -ne 0) { throw 'Tests niet volledig geslaagd; release stoppen.' }
```

Deze opdracht test de generator, het menu, manifest en metadata, zelfstandig
gegenereerde projecten, alle vier templates en de JavaScript-webcode. Ze
installeert niets. Een ontbrekende Node-opdracht of falende suite geeft exitcode
1; volgende suites worden waar mogelijk nog uitgevoerd voor een volledig beeld.
Testdata staat in tijdelijke mappen. De standaardmap-test is nu veilig geïsoleerd;
er wordt geen test meer uitgesloten om de suite groen te maken.

Controleer iedere `skipped`-melding: een skip is geen uitgevoerde test.
Windows kan echte symlink-tests overslaan. De Linux-jobs moeten die controles
wel uitvoeren; onderzoek skips daar. Noteer versies, resultaten en resterende
beperkingen bij de release. Lokale resultaten bewijzen niet dat de hele CI-matrix slaagt.

De workflow `.github/workflows/studio-tests.yml` draait dezelfde opdracht in acht
combinaties van Windows/Linux, Python 3.11/3.14 en Node.js 22/24. Bekijk op GitHub
alle jobs voor de exacte commit die je wilt uitbrengen. Publiceer niet terwijl
er jobs falen of nog bezig zijn. Er worden geen tests met betaalde AI-aanroepen gedaan.

Controleer daarnaast handmatig de webpagina in een browser en het interactieve
menu. Bekijk documentatielinks en voorbeelden. Gebruik voor een CLI-proef een
nieuwe doelmap en expliciet `--output`; overschrijf nooit een echt project.

## 3. Controleer het materiaal dat je gaat delen

- Controleer nieuwe en geselecteerde bestanden op secrets, persoonsgegevens,
  lokale paden, backups en echte input/output. Lees ook [veilig werken](SECURITY.md).
- Neem `.venv`, caches, `.git`, `.env`, logs en persoonlijke datasets niet op in
  een handmatig gemaakt archief. Alleen `.env.example` met lege/fictieve waarden
  hoort bij het AI-template.
- Controleer gebruiksrechten van code en assets. Er is geen licentie gekozen door
  deze releasehandleiding; spreek die af vóór publieke distributie.
- Werk `CHANGELOG.md` bij met de echte releaseversie, wijzigingen en beperkingen.
  Vul de publicatiedatum pas bij publicatie in en werk vooraf gerust met een concept.

## 4. Alleen na een bewust besluit: vastleggen en publiceren

Deze stap voer je zelf uit, of je geeft Codex er afzonderlijk toestemming voor.
De opdracht om documentatie of tests te maken is geen opdracht om te publiceren.
Volg eerst [de Git-workflow](WORKFLOW.md): selecteer bestanden gericht, bekijk
de selectie en leg pas dan de releasevoorbereiding vast. Laat de afgesproken
review en testmatrix op de uiteindelijke commit slagen. Controleer dat de
werkkopie schoon is; een niet-vastgelegde wijziging hoort niet bij de releasecommit.

Gebruik op GitHub bij **Releases** de optie **Draft a new release**. Kies bewust
de juiste repository, versie-tag en geteste commit. Een tag verwijst naar een
vaste versie; laat hem naar de bedoelde commit wijzen en controleer dit vóór
publiceren. Gebruik bijvoorbeeld het patroon `v1.0.0`, maar alleen als `1.0.0`
werkelijk de afgesproken, nog niet gebruikte releaseversie is.

Neem de gecontroleerde changelogpunten over in de releasebeschrijving. Bewaar
eerst als concept, controleer bijlagen en de zichtbaarheid van de repository en
publiceer pas na je laatste controle. GitHub biedt bij een release bronarchieven
van de gekozen tag. Deze studio bouwt of uploadt zelf geen releasepakket.
De handmatige stappen staan ook in de
[officiële GitHub-handleiding](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

## 5. Na publicatie

Controleer of tag, releasebeschrijving, datum en bronbestanden overeenkomen.
Probeer bij voorkeur uit een nieuwe download één nieuw project te genereren en
te testen. Begin daarna een nieuwe sectie **Nog niet uitgebracht** in de changelog.
Bij een probleem: beschrijf de impact en breng een correctieversie uit. Herschrijf
geen gepubliceerde geschiedenis of bestaande projecten zonder aparte afspraak.
