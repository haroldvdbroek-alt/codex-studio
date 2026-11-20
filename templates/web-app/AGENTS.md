# Ontwikkelregels voor PROJECT_NAME

- Communiceer in begrijpelijk Nederlands. Lees eerst README, code, tests en
  toepasselijke bovenliggende instructies. Controleer de Git-status.
- Stel bij grotere wijzigingen een plan voor en werk in kleine stappen.
  Behoud werk van de gebruiker en gebruik in een Git-project een taakbranch.
- Gebruik gewone HTML, CSS en JavaScript, zonder frameworks of externe assets.
  Houd browserbestanden in `public` en tests in `tests`.
- Houd de app rechtstreeks vanuit `public/index.html` bruikbaar. Er zijn geen
  package-installaties of buildstappen. De Node-export in `app.js` dient alleen
  om dezelfde logica te testen; de browser gebruikt een klassiek script met defer.
- Gebruik veilige tekstweergave met `textContent`. Voeg geen secrets,
  persoonsgegevens, tracking of externe netwerkverzoeken toe.
- Behoud semantische HTML, toetsenbordbediening en een zichtbare focusindicator.
- Test vanuit de projectmap met `node --test tests/counter.test.cjs` en
  `python -m unittest discover -s tests -v`. Gebruik Node.js 22+ en Python 3.11+.
  Test gewijzigd gedrag automatisch en controleer uiterlijk en bediening ook
  handmatig in een browser. Meld welke controles niet zijn uitgevoerd.
- Vraag toestemming voor installaties, updates en destructieve opdrachten.
  Initialiseer Git of een GitHub-repository niet ongevraagd. Maak alleen een
  commit of push als de gebruiker dat uitdrukkelijk vraagt.
