# Hotel Price Tracker

Construit l'itinéraire d'hébergement d'un voyage au Japon (Osaka, Kyoto, Tokyo) : ville, nombre de nuits, hôtel, prix, trajets entre les villes et prix total. Gratuit, dépôt public, même esprit que [flight-price-tracker](https://github.com/RomainChe/flight-price-tracker).

État : **Phase 3 (suivi)**. Le workflow « Suivi quotidien » relève les prix, ajoute `historique/prix.csv`, met à jour `historique/suivi.md` et ouvre une issue GitHub en cas d'alerte (baisse, hôtel disparu, total sous le seuil ; réglages dans `alertes:` de `config.yaml`). `python -m tracker --dry-run` (données de test) ou `python -m tracker` (Xotelo, ~3 min) ; écrit `out/itineraire.md`. Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) et [docs/ROADMAP.md](docs/ROADMAP.md).
