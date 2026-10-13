"""Phase 2 : ordre des villes, répartition des nuits, trajets, total et itineraire.md."""
from datetime import date, timedelta

import yaml


def order_cities(cfg):
    """Ville de l'aéroport d'arrivée d'abord, celle du départ en dernier, les autres dans l'ordre de config.yaml."""
    def rank(v):
        if cfg.aeroport_arrivee and v.aeroport == cfg.aeroport_arrivee:
            return 0
        return 2 if cfg.aeroport_depart and v.aeroport == cfg.aeroport_depart else 1
    return sorted(cfg.villes, key=rank)  # tri stable


def plan_stays(cfg):
    """[(ville, check-in, nuits)] couvrant tout le voyage : `nuits_min` + le reste réparti selon le poids (1 + activités)."""
    villes = order_cities(cfg)
    extra = (cfg.depart - cfg.arrivee).days - sum(v.nuits_min for v in villes)
    w = [1 + len(v.activites) for v in villes]
    nights = [v.nuits_min + extra * wi // sum(w) for v, wi in zip(villes, w)]
    heaviest = sorted(range(len(villes)), key=lambda i: -w[i])
    for k in range(extra - sum(n - v.nuits_min for n, v in zip(nights, villes))):  # reste de la division
        nights[heaviest[k % len(villes)]] += 1
    plan, day = [], cfg.arrivee
    for v, n in zip(villes, nights):
        plan.append((v, day, n))
        day += timedelta(days=n)
    return plan


def recommended(offers):
    """Meilleure note (puis avis) parmi les offres à ≤ 1,5× le prix de la moins chère. `offers` : du moins cher au plus cher."""
    # ponytail : heuristique qualité/prix à un seuil fixe ; à affiner avec l'historique (Phase 3)
    cap = offers[0].rate * 1.5
    return max((o for o in offers if o.rate <= cap), key=lambda o: (o.hotel.rating, o.hotel.reviews, -o.rate))


def load_trajets(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build(cfg, results, trajets: dict) -> str:
    """Markdown de l'itinéraire. `results` : un par étape, dans l'ordre, avec ville / chk_in / chk_out / nights / offers / message."""
    eur = cfg.devise
    rows, notes, reco_total, min_total, complete = [], [], 0.0, 0.0, True
    for r in results:
        head = f"| {r.ville.capitalize()} | {r.chk_in} → {r.chk_out} | {r.nights} "
        if not r.offers:
            complete = False
            rows.append(head + "| — | — |")
            notes.append(f"{r.ville.capitalize()} : {r.message or 'aucune offre'}")
            continue
        best, cheap = recommended(r.offers), r.offers[0]
        reco_total += best.total
        min_total += cheap.total
        fmt = lambda o: f"{o.hotel.name} ({o.hotel.rating * 2:g}/10, {o.rate:g} {eur}/nuit) = {o.total:g} {eur}"
        rows.append(head + f"| {fmt(best)} | {fmt(cheap) if cheap is not best else 'idem'} |")

    legs, trajets_eur = [], 0.0
    for a, b in zip(results, results[1:]):
        t = trajets.get("-".join(sorted((a.ville, b.ville))))
        if not t:
            notes.append(f"Trajet {a.ville} → {b.ville} absent de data/trajets.yaml : non compté.")
            complete = False
            continue
        cost = t["prix_jpy"] * cfg.voyageurs * cfg.taux_jpy_eur
        trajets_eur += cost
        legs.append(f"- {a.ville.capitalize()} → {b.ville.capitalize()} : {t['mode']}, {t['duree_min']} min, "
                    f"{t['prix_jpy']} ¥ × {cfg.voyageurs} ≈ {cost:.0f} {eur}"
                    + (" · réservation conseillée" if t.get("reservation") else ""))

    activites = {v.name: v.activites for v in cfg.villes}
    alerts = []
    for r in results:
        for a in activites[r.ville]:
            if a.reservation_requise:
                limit = date.fromisoformat(r.chk_in) - timedelta(days=a.delai_reservation)
                alerts.append(f"- {a.nom} ({r.ville.capitalize()}) : réserver au plus tard le {limit} "
                              f"({a.delai_reservation} j avant le début du séjour ; fixer la date exacte de l'activité).")

    out = [f"# Itinéraire — {cfg.voyageurs} voyageur(s), {cfg.arrivee} → {cfg.depart}", "",
           "| Étape | Dates | Nuits | Recommandé | Moins cher |", "| --- | --- | --- | --- | --- |", *rows, "",
           "## Trajets", *(legs or ["Aucun trajet."]), "", "## Total", ""]
    flag = "" if complete else " (INCOMPLET, voir les notes)"
    out += [f"- Recommandé : {reco_total + trajets_eur:.0f} {eur} (hébergement {reco_total:.0f} + trajets {trajets_eur:.0f}){flag}",
            f"- Moins cher : {min_total + trajets_eur:.0f} {eur} (hébergement {min_total:.0f} + trajets {trajets_eur:.0f}){flag}",
            f"- Écart : {reco_total - min_total:.0f} {eur} pour la meilleure note"]
    if alerts:
        out += ["", "## À réserver à l'avance", *alerts]
    if notes:
        out += ["", "## Notes", *(f"- {n}" for n in notes)]
    return "\n".join(out) + "\n"


def resume(cfg, results, trajets: dict, today: date) -> dict:
    """Totaux du relevé en JSON (`historique/resume.json`), lus par JARVIS : mêmes règles que `build`, aucune donnée personnelle."""
    pick = lambda o: o and {"hotel": o.hotel.name, "note10": o.hotel.rating * 2, "nuit": o.rate, "total": o.total}  # noqa: E731
    etapes = [{"ville": r.ville, "chk_in": r.chk_in, "chk_out": r.chk_out, "nuits": r.nights,
               "recommande": pick(recommended(r.offers) if r.offers else None),
               "moins_cher": pick(r.offers[0] if r.offers else None)} for r in results]
    legs = [trajets.get("-".join(sorted((a.ville, b.ville)))) for a, b in zip(results, results[1:])]
    trajets_eur = sum(t["prix_jpy"] * cfg.voyageurs * cfg.taux_jpy_eur for t in legs if t)
    done = [r for r in results if r.offers]
    return {"date": today.isoformat(), "devise": cfg.devise, "voyageurs": cfg.voyageurs, "etapes": etapes,
            "trajets": round(trajets_eur, 2), "complet": len(done) == len(results) and all(legs),
            "total_recommande": round(sum(recommended(r.offers).total for r in done) + trajets_eur, 2),
            "total_moins_cher": round(sum(r.offers[0].total for r in done) + trajets_eur, 2)}
