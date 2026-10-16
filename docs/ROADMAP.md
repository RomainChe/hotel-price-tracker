# Roadmap

## État actuel

Phases 0 à 4 fusionnées dans `main` (tracker et JARVIS). Premier relevé réel post-fusion fait le 2026-10-13 : `historique/resume.json` existe, JARVIS (`hotel_itineraire`, carré « Hôtels · Japon ») peut le lire. Limites de la Phase 3 inchangées. **Rien d'ouvert** : la roadmap est terminée ; prochaines idées à décider avec le propriétaire.

## Phases

- **Phase 0 — Cadrage** : fait (ce dossier).
- **Phase 1 — Moteur** (fait) : config, modèle de données, source Xotelo (`/list`, `/rates`), filtres note/avis/budget, nombre de voyageurs, dry-run, tests.
- **Phase 2 — Itinéraire** (fait) : ordre des villes, répartition des nuits, trajets, total, `itineraire.md`, comparaison recommandé vs moins cher, alertes de réservation.
- **Phase 3 — Suivi** (fait) : workflow planifié, historique CSV, alertes de baisse et d'hôtel disparu, dashboard, push.
- **Phase 4 — Intégration JARVIS** (fait) : outil N0 `hotel_itineraire` et carré dashboard, sur le modèle de `voyage_prix`. Feu vert donné le 2026-10-13.
