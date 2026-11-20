# Changelog

## [Unreleased]

- Betrouwbaardere procesboomtest en gecontroleerde verwachte foutlogs in tests.
- Oudere automation-, manifest- en release-workflow-branches geïntegreerd:
  vier werkende templates, interactief menu en generatie via het centrale manifest.
- Nieuwe projecten krijgen `.codex-studio.json`, zodat list/check/updates ze
  herkennen. Bestaande projectmappen blijven ongewijzigd.
- Volledige testworkflow voor studio, alle templates en JavaScript hersteld.

## [1.1.0]

Compatibele uitbreiding ten opzichte van de gepubliceerde tag v1.0.0:

- Lokale projectdetectie, veilige configuratie/Git-controles, template-updates
  en een alleen-lezen browserdashboard.
- Veilige broncodeback-ups en geverifieerd herstel naar uitsluitend nieuwe mappen.
- Quality- en lokale releasecontroles, JSON/Markdown-rapporten en optionele tests.
- PowerShell-ondersteuning voor een uitsluitend handmatig in te stellen Windows-taak.
- Benchmark met tijdelijke fictieve projecten, centrale logging naar stderr
  zonder standaard logbestanden en alleen-lezen maintenance-controles.
- CI-tests voor Windows met Python 3.11 en 3.13 en een handmatige publicatiehandleiding.

De Python-generator blijft beschikbaar. Web-, AI- en automation-templatebronnen
ontbreken op deze branch en blijven gepland. Aanwezige tests bewijzen geen
testdekking; maintenance doet daarover geen automatische uitspraak.

## [1.0.0]

- Gepubliceerde basis met Python-template en Python-projectgenerator,
  overeenkomstig de bestaande tag v1.0.0.
