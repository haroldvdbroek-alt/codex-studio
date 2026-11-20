# Een nieuwe versie publiceren

Publiceren gebeurt bewust en handmatig. Er is geen automatische publicatietaak.
De bestaande [releasevoorcontrole](RELEASE.md) publiceert zelf nooit.

## Versienummer kiezen

Gebruik de laatste gepubliceerde GitHub-release en bijbehorende tag als basis.
Projectmetadata en templateversies zijn geen studioreleaseversies.

- PATCH, bijvoorbeeld 1.0.1: compatibele foutcorrecties.
- MINOR, bijvoorbeeld 1.1.0: nieuwe functies met behoud van bestaande opdrachten.
- MAJOR, bijvoorbeeld 2.0.0: bewust incompatibele wijzigingen.

Beschrijf de werkelijke wijzigingen in een eigen changelogsectie. Versie 1.1.0
volgt op 1.0.0 vanwege aanvullende projectbeheer-, kwaliteits-, logging- en
onderhoudsfuncties; de bestaande Python-generator blijft beschikbaar.
De aanwezigheid van deze notities bewijst geen gepubliceerde release.

## Eerst de Pull Request afronden

1. Controleer wijzigingen en gevoelige gegevens. Maak een PR met doelbranch
   `main`; controleer dit expliciet als de standaardbranch anders heet.
2. Wacht tot beide Windows/Python-testtaken in `Studio tests` slagen voor de
   actuele PR-commit. Die testen de studio, alle vier zelfstandige templates,
   de JavaScript-logica en de alleen-lezen onderhoudscontrole. Node.js 22+ moet
   beschikbaar zijn; er worden geen pakketten geïnstalleerd.
3. Beoordeel overgeslagen tests en de overige handmatige voorwaarden uit
   [RELEASE.md](RELEASE.md). Een geslaagde CI is geen beveiligingsgarantie.
4. Merge pas na geslaagde checks en eventuele vereiste reviews. Omzeil geen
   branchbescherming. Wacht ook op de workflow voor de gemergede `main`-commit.

## De gecontroleerde main-commit publiceren

Gebruik in GitHub **Releases → Draft a new release**. Kies een nieuwe tag,
bijvoorbeeld `v1.1.0`, en selecteer als target exact de gecontroleerde commit
op `main`. De standaardbranch kan anders zijn: laat het target niet onbewust
op die branch staan. Controleer dat de tag nog niet bestaat en wijzig nooit
een bestaande releasetag om een nieuwe versie te publiceren.

Gebruik de bijbehorende changelogsectie voor de releasenotities en beschrijf
resterende beperkingen. De vier templates zijn nu hersteld; de AI-demo doet
geen echte API-aanroepen en automation heeft standaard dry-run.
Controleer tag, commit, tests en notities; kies pas daarna **Publish release**.
GitHub maakt standaard broncodearchieven; upload geen lokale gegevensbestanden,
secrets, rapporten of persoonlijke back-ups als bijlagen.

Na publicatie controleer je de releasepagina, de tag en de workflow voor de tag.
Publicatie verandert project- of templateversies niet automatisch. Bestaande
projectmappen worden niet bijgewerkt. Een defecte gepubliceerde versie herstel
je met een volgende versie, niet door stilzwijgend de bestaande tag te verplaatsen.
