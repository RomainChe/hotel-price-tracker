# Roadmap

## État actuel

Phase 1 codée le 2026-10-13 : config validée, modèle hôtel/offre, source Xotelo (`/list`, `/rates`, plafond de requêtes, pauses), filtres note/avis/petit-déjeuner/budget, voyageurs → chambres, `--dry-run`, 15 tests verts. Essai réel OK (Osaka, Kyoto, Tokyo, mai 2027, ~3 min). Limites connues : séjours provisoires (`nuits_min` à la suite, la Phase 2 répartit), une seule page `/list` de 100 hôtels, classement par prix seulement, pas d'historique. **Prochaine étape : revue du propriétaire, puis Phase 2.**

## Phases

- **Phase 0 — Cadrage** : fait (ce dossier).
- **Phase 1 — Moteur** (fait) : config, modèle de données, source Xotelo (`/list`, `/rates`), filtres note/avis/budget, nombre de voyageurs, dry-run, tests.
- **Phase 2 — Itinéraire** : ordre des villes, répartition des nuits, trajets, total, `itineraire.md`, comparaison recommandé vs moins cher, alertes de réservation.
- **Phase 3 — Suivi** : workflow planifié, historique CSV, alertes de baisse et d'hôtel disparu, dashboard, push.
- **Phase 4 — Intégration JARVIS (optionnelle)** : outil N0 `hotel_itineraire` et carré dashboard, sur le modèle de `voyage_prix`. Seulement après feu vert.
