# Roadmap

## État actuel

Phase 3 fusionnée dans `main` (essai réel du workflow « Suivi quotidien » à faire à la main une fois). **Phase 4 codée le 2026-10-13** (branche `feat/4-jarvis`, non fusionnée) : `tracker/itineraire.resume` + `historique/resume.json` (totaux recommandé / moins cher, trajets, étapes ; écrit à chaque relevé réel, commité par le workflow) ; côté JARVIS (dépôt `ProjectJarvis`, branche `feat/hotel-itineraire`) : outil N0 `hotel_itineraire`, intention du routeur et carré « Hôtels · Japon » du dashboard. Aucune écriture de JARVIS dans ce dépôt. `resume.json` n'existe qu'après le premier relevé réel : sans lui, JARVIS dit « aucun relevé ». Limites de la Phase 3 inchangées. **Prochaine étape : revue, fusion, premier lancement manuel du workflow, fusion de la branche JARVIS.**

## Phases

- **Phase 0 — Cadrage** : fait (ce dossier).
- **Phase 1 — Moteur** (fait) : config, modèle de données, source Xotelo (`/list`, `/rates`), filtres note/avis/budget, nombre de voyageurs, dry-run, tests.
- **Phase 2 — Itinéraire** (codée, à fusionner) : ordre des villes, répartition des nuits, trajets, total, `itineraire.md`, comparaison recommandé vs moins cher, alertes de réservation.
- **Phase 3 — Suivi** (codée, à fusionner) : workflow planifié, historique CSV, alertes de baisse et d'hôtel disparu, dashboard, push.
- **Phase 4 — Intégration JARVIS** (codée, à fusionner) : outil N0 `hotel_itineraire` et carré dashboard, sur le modèle de `voyage_prix`. Feu vert donné le 2026-10-13.
