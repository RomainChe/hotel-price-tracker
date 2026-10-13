# Hotel Price Tracker

Itinéraire d'hébergement Japon (Osaka, Kyoto, Tokyo) avec prix total. Dépôt PUBLIC : aucun secret, token, IP ou donnée personnelle dans les fichiers.

## Stack

Python 3.12, bibliothèque standard, `PyYAML`, `pytest`. Mêmes conventions que flight-price-tracker : une source = un module avec `NAME` et `collect(...)`, dépendances injectables, tests sans réseau, historique CSV commité par le workflow.

## Vérifications

- Tests : `python -m pytest -q` (ou, sans pytest installé : `python -m unittest tests.test_engine tests.test_itineraire tests.test_suivi`). Aucun appel réseau.
- Essai sans réseau : `python -m tracker --dry-run`. Essai réel (~3 min, ~35 requêtes Xotelo) : `python -m tracker`.

## Règles

- Aucune valeur de voyage en dur : tout dans `config.yaml`.
- Aucun hôtel hors critères. Si une ville n'a aucun résultat : le dire et proposer d'assouplir un critère, jamais en silence.
- Ne jamais contourner un blocage ou des conditions d'utilisation d'une source.
- Trajets et quartiers : fichiers statiques versionnés (`data/`), pas de LLM.
- `historique/resume.json` est lu par JARVIS (`hotel_snapshot`, dépôt ProjectJarvis) : en changer le schéma, c'est changer JARVIS aussi.

## Dossiers

```text
config.yaml        voyage, contraintes, source, villes (aucun secret)
tracker/           __main__ (orchestration), config, models, filters, itineraire (ordre, nuits, total)
data/              trajets.yaml (durée, prix en ¥, valeurs approximatives)
tracker/suivi.py   historique CSV, alertes, tableau de suivi (Phase 3)
tracker/sources/   une source = list_hotels + rates (xotelo, sample pour le dry-run)
historique/        prix.csv + suivi.md, commités par le workflow
.github/workflows/ suivi.yml (quotidien, manuel)
tests/             unittest/pytest, sources injectées
```

## Où c'est

- `docs/ARCHITECTURE.md` : sources, schéma de config, flux.
- `docs/ROADMAP.md` : phases et état actuel.
