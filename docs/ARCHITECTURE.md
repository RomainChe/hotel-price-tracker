# Architecture

## Source de prix : Xotelo

Comparaison faite le 2026-10-13.

| Source | Verdict | Raison |
| --- | --- | --- |
| **Xotelo** (`data.xotelo.com`) | **Retenue** | Gratuite, sans clé, basée sur TripAdvisor. `/list` : hôtels d'une ville avec note /5, nombre d'avis, fourchette de prix, GPS. `/rates` : prix par chambre et par nuit chez Booking, Trip.com, Vio, Agoda. Testée en direct (Osaka : 2 921 hôtels, tarifs de mai 2027). |
| Amadeus Self-Service | Éliminée | Portail fermé le 17 juillet 2026. |
| Travelpayouts / Hotellook | Éliminée | Programme et API fermés le 20 octobre 2025. |
| Scraping Google Hotels | Écartée | Pas d'API officielle, conditions de Google contre l'accès automatisé, page fragile. |

### Limites de Xotelo (à garder visibles)

1. **Pas d'étoiles.** Décision du 2026-10-13 : le critère « étoiles » est abandonné, le filtre porte sur la note et le nombre d'avis. `accommodation_type` est conservé pour écarter ce qui n'est pas un hôtel si besoin.
2. **Pas de capacité de chambre.** On demande `rooms` et `adults` au prix et on s'appuie sur l'offre de l'OTA ; la taille réelle n'est pas vérifiable. Règle : 2 pers = 1 chambre, 3 = 1 chambre triple ou 2 chambres, 4+ = plusieurs chambres de 2.
3. **Note TripAdvisor (/5) ≠ note Booking (/10).** Équivalent retenu : 8,0/10 = 4,0/5. Approximation documentée.
4. **Aucune condition d'usage ni limite publiée**, `tax` toujours `null`. Service gratuit tenu par une seule personne : prévoir `max_requests` par jour, pauses, et signaler la panne au lieu de l'avaler.
5. `/search` (par nom) n'est disponible que via RapidAPI : on utilise `/list` par ville.

La source est derrière une interface `collect` : la remplacer ne touche pas le reste.

## Schéma de `config.yaml`

```yaml
voyage:                       # copié UNE fois de flight-price-tracker, à tenir synchro à la main
  arrivee: 2027-05-06         # le vol part le 05/05, arrivée au Japon le 06/05 (à confirmer)
  depart: 2027-05-22
  aeroport_arrivee: KIX
  aeroport_depart: HND
voyageurs: 2
devise: EUR
taux_jpy_eur: 0.0061          # paramétrable

contraintes:
  note_min: 8.0               # sur 10, converti en /5 pour Xotelo
  avis_min: 100
  budget_max_nuit: null       # € par chambre, optionnel
  petit_dejeuner: false

source:
  nom: xotelo
  max_requests: 200           # par jour
  pause_seconds: [1, 3]

villes:
  osaka:
    xotelo_location_key: g298566
    nuits_min: 3
    quartiers: [Namba, Nishikujo]
    activites:
      - {nom: Universal Studios Japan, duree_h: 9, gare: Universal City, reservation_requise: true, delai_reservation: 30}
  kyoto: {}
  tokyo: {}

alertes:
  total_sous: null            # € pour N voyageurs
  hotel_disparu: true
```

Données statiques versionnées : `data/trajets.yaml` (Shinkansen/JR : durée, prix en ¥, réservation) et `data/quartiers.yaml` (temps de transport quartier → activité).

## Flux d'une exécution (cible)

1. Validation de `config.yaml`.
2. Ordre des villes selon `aeroport_arrivee` / `aeroport_depart`, puis répartition des nuits (proportionnelle aux activités, Osaka ≥ 3 jours, tampons Nara et Fuji).
3. Pour chaque étape : `/list` par ville, filtre note/avis/budget, `/rates` des candidats, classement qualité/prix. Garder le n°1 et 2 alternatives.
4. Trajets et total (hébergement + trajets inter-villes, N voyageurs, € et ¥, date de mise à jour).
5. `itineraire.md`, ajout à l'historique CSV, alertes. Aucun résultat dans une ville : message clair et critère à assouplir proposé.

Mode `dry-run` : données de test, aucun appel réseau, aucune écriture d'historique.
