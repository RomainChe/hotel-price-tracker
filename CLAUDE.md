# Hotel Price Tracker

Itinéraire d'hébergement Japon (Osaka, Kyoto, Tokyo) avec prix total. Dépôt PUBLIC : aucun secret, token, IP ou donnée personnelle dans les fichiers.

## Stack

Python 3.12, bibliothèque standard, `PyYAML`, `pytest`. Mêmes conventions que flight-price-tracker : une source = un module avec `NAME` et `collect(...)`, dépendances injectables, tests sans réseau, historique CSV commité par le workflow.

## Vérifications

- Tests : `python -m pytest -q` (aucun code pour l'instant : Phase 0).

## Règles

- Aucune valeur de voyage en dur : tout dans `config.yaml`.
- Aucun hôtel hors critères. Si une ville n'a aucun résultat : le dire et proposer d'assouplir un critère, jamais en silence.
- Ne jamais contourner un blocage ou des conditions d'utilisation d'une source.
- Trajets et quartiers : fichiers statiques versionnés (`data/`), pas de LLM.
- Phase 4 (intégration JARVIS) seulement après feu vert explicite.

## Où c'est

- `docs/ARCHITECTURE.md` : sources, schéma de config, flux.
- `docs/ROADMAP.md` : phases et état actuel.
