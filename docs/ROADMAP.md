# Roadmap

## État actuel

Phase 2 codée le 2026-10-13 (branche `phase-2-itineraire`, non fusionnée) : ordre des villes selon `aeroport` / aéroports du voyage, nuits réparties sur tout le voyage (`nuits_min` + reste pondéré par 1 + nombre d'activités), `data/trajets.yaml` (valeurs approximatives à vérifier), total recommandé vs moins cher (écart affiché), alertes de réservation des activités, `out/itineraire.md`. 22 tests verts, `--dry-run` OK. Pas d'essai réel Xotelo de la Phase 2 (~3 min, ~35 requêtes) : à faire. Limites connues : « recommandé » = meilleure note à ≤ 1,5× le moins cher (seuil fixe), délai d'alerte compté depuis le début du séjour (la date des activités n'est pas dans la config), pas de trajets depuis/vers l'aéroport, pas de tampons Nara/Fuji, `data/quartiers.yaml` non fait, séjour d'une ville limité à une page `/list` de 100 hôtels. **Prochaine étape : revue du propriétaire (valeurs de trajets, seuil 1,5×), fusion, puis Phase 3.**

## Phases

- **Phase 0 — Cadrage** : fait (ce dossier).
- **Phase 1 — Moteur** (fait) : config, modèle de données, source Xotelo (`/list`, `/rates`), filtres note/avis/budget, nombre de voyageurs, dry-run, tests.
- **Phase 2 — Itinéraire** (codée, à fusionner) : ordre des villes, répartition des nuits, trajets, total, `itineraire.md`, comparaison recommandé vs moins cher, alertes de réservation.
- **Phase 3 — Suivi** : workflow planifié, historique CSV, alertes de baisse et d'hôtel disparu, dashboard, push.
- **Phase 4 — Intégration JARVIS (optionnelle)** : outil N0 `hotel_itineraire` et carré dashboard, sur le modèle de `voyage_prix`. Seulement après feu vert.
