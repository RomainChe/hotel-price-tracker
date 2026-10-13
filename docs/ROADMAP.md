# Roadmap

## État actuel

Phase 3 codée le 2026-10-13 (branche `feat/3-suivi`, non fusionnée) : workflow `.github/workflows/suivi.yml` (quotidien + manuel), historique `historique/prix.csv` commité par le workflow, alertes (baisse ≥ `baisse_pct`, hôtel suivi disparu, hébergement recommandé sous `total_sous`) comparées au relevé précédent, tableau `historique/suivi.md`, push = issue GitHub (notification e-mail native, aucun secret). 30 tests verts, `--dry-run` OK. Pas d'essai réel du workflow : lancer « Suivi quotidien » à la main une fois (écrit et commite le premier relevé). Limites : « suivis » = recommandé et moins cher du relevé précédent ; `total_sous` compare l'hébergement seul (sans trajets) ; dashboard = tableau Markdown des 30 derniers relevés, pas de courbes ; seuil 1,5× du recommandé toujours fixe. **Prochaine étape : revue, fusion, premier lancement manuel, puis Phase 4 seulement sur feu vert.**

## Phases

- **Phase 0 — Cadrage** : fait (ce dossier).
- **Phase 1 — Moteur** (fait) : config, modèle de données, source Xotelo (`/list`, `/rates`), filtres note/avis/budget, nombre de voyageurs, dry-run, tests.
- **Phase 2 — Itinéraire** (codée, à fusionner) : ordre des villes, répartition des nuits, trajets, total, `itineraire.md`, comparaison recommandé vs moins cher, alertes de réservation.
- **Phase 3 — Suivi** (codée, à fusionner) : workflow planifié, historique CSV, alertes de baisse et d'hôtel disparu, dashboard, push.
- **Phase 4 — Intégration JARVIS (optionnelle)** : outil N0 `hotel_itineraire` et carré dashboard, sur le modèle de `voyage_prix`. Seulement après feu vert.
