"""Point d'entrée : python -m tracker [--dry-run] [--config config.yaml]"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .config import Config, load_config
from .filters import explain_empty, filter_hotels, filter_offers, near_airport
from .itineraire import build, load_trajets, plan_stays, resume
from .models import Offer, label, rooms_for
from .scenarios import Scenario, cheapest, load_rows, pick, render as render_scenarios, with_flight
from .sources.sample import Sample
from .sources.xotelo import BudgetExhausted, Xotelo
from .suivi import alerts, dashboard, load_history, rows_for, write_history

ROOT = Path(__file__).resolve().parents[1]
SHOWN = 3  # offres affichées par ville


@dataclass
class CityResult:
    ville: str
    chk_in: str
    chk_out: str
    nights: int = 0
    offers: list[Offer] = field(default_factory=list)  # un par hôtel (OTA la moins chère), du moins cher au plus cher
    message: str = ""  # pourquoi il n'y a rien, ou quelle panne
    parent: str = ""  # ville d'une étape aéroport


def run(cfg: Config, source, aeroports: dict | None = None) -> list[CityResult]:
    rooms, adults = rooms_for(cfg.voyageurs)
    results = []
    for ville, chk_in, nights in plan_stays(cfg):
        res = CityResult(ville.name, chk_in.isoformat(), (chk_in + timedelta(days=nights)).isoformat(), nights, parent=ville.parent)
        results.append(res)
        try:
            hotels, funnel = filter_hotels(source.list_hotels(ville.location_key), cfg)
            airport = (aeroports or {}).get(ville.aeroport)  # `aeroport` : code des seules étapes aéroport
            if ville.proche_aeroport and not airport:
                raise ValueError(f"aéroport {ville.aeroport} absent de data/aeroports.yaml")
            if ville.proche_aeroport:
                near, f_near = near_airport(hotels, airport, cfg)
                hotels, funnel, km = [h for h, _ in near], funnel + f_near, {h.key: d for h, d in near}
            else:
                km = {}
            offers, errors = [], 0
            for h in hotels[:cfg.candidats_max]:
                try:
                    rates = source.rates(h.key, res.chk_in, res.chk_out, rooms, adults, cfg.devise)
                except BudgetExhausted:
                    raise
                except Exception:  # un hôtel en échec ne perd pas la ville
                    errors += 1
                    continue
                if rates:
                    ota, rate = min(rates, key=lambda r: r[1])
                    offers.append(Offer(h, ota, rate, nights, rooms, km.get(h.key)))
            offers, f2 = filter_offers(offers, cfg)
            res.offers = sorted(offers, key=lambda o: o.rate)
            if not res.offers:
                res.message = explain_empty(funnel + f2, cfg)
            if errors:
                res.message = (res.message + " " if res.message else "") + f"{errors} requête(s) de tarifs en échec."
        except Exception as e:  # une ville en panne n'arrête pas les autres, et la panne est dite
            res.message = f"Source en panne : {e}"  # plafond atteint : les villes suivantes le disent aussi
    return results


class Cached:
    """Une même ville aux mêmes dates revient dans plusieurs scénarios : une seule requête."""

    def __init__(self, source):
        self.source, self.NAME, self._lists, self._rates = source, source.NAME, {}, {}

    def list_hotels(self, key):
        if key not in self._lists:
            self._lists[key] = self.source.list_hotels(key)
        return self._lists[key]

    def rates(self, *args):
        if args not in self._rates:
            self._rates[args] = self.source.rates(*args)
        return self._rates[args]


def compare(cfg: Config, source, aeroports: dict, trajets: dict, flights, today: date):
    """Un itinéraire d'hôtels par vol ; sans vol exploitable, le seul scénario de la config. Retourne (retenu, tous)."""
    if not flights:
        res = run(cfg, source, aeroports)
        only = Scenario(None, cfg, res, resume(cfg, res, trajets, today))
        return only, [only]
    source, scenarios = Cached(source), []
    for f in flights:
        c = with_flight(cfg, f)
        if sum(v.nuits_min for v in c.villes) > (c.depart - c.arrivee).days:
            continue  # dates trop courtes pour les nuits minimales
        res = run(c, source, aeroports)
        scenarios.append(Scenario(f, c, res, resume(c, res, trajets, today)))
    if not scenarios:
        return compare(cfg, source, aeroports, trajets, [], today)
    return pick(scenarios, cfg.voyageurs), scenarios


def render(cfg: Config, results: list[CityResult]) -> str:
    out = [f"{cfg.voyageurs} voyageur(s), note ≥ {cfg.note_min:g}/10, avis ≥ {cfg.avis_min}"
           + (f", ≤ {cfg.budget_max_nuit:g} €/nuit/chambre" if cfg.budget_max_nuit is not None else "")]
    for r in results:
        out.append(f"\n{label(r.ville)} · {r.chk_in} → {r.chk_out}")
        for o in r.offers[:SHOWN]:
            out.append(f"  {o.hotel.name} · {o.hotel.rating * 2:g}/10 ({o.hotel.reviews} avis) · "
                       f"{o.rate:g} {cfg.devise}/nuit via {o.ota} · total {o.total:g} {cfg.devise}")
        if r.message:
            out.append(f"  ! {r.message}")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Itinéraire d'hébergement : hôtels et prix par ville.")
    parser.add_argument("--config", default=ROOT / "config.yaml", type=Path)
    parser.add_argument("--out", default=ROOT / "out" / "itineraire.md", type=Path)
    parser.add_argument("--vols", help="CSV de prix de flight-price-tracker (fichier ou URL https) ; remplace `vols.csv` de la config")
    parser.add_argument("--dry-run", action="store_true", help="données de test, aucun appel réseau")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # consoles Windows cp1252
    try:
        cfg = load_config(args.config)
    except ValueError as e:  # erreur de configuration : message clair, sans trace
        sys.exit(f"Configuration invalide : {e}")
    source = Sample() if args.dry_run else Xotelo(cfg.max_requests, cfg.pause_seconds)
    aeroports = load_trajets(ROOT / "data" / "aeroports.yaml")
    trajets = load_trajets(ROOT / "data" / "trajets.yaml")
    flights, vols_src = [], args.vols or ("" if args.dry_run else cfg.vols_csv)
    if vols_src:
        try:
            flights = cheapest(load_rows(vols_src), {code for v in cfg.villes for code in v.aeroports}, cfg.vols_par_recherche)
        except Exception as e:  # prix de vols indisponibles : on garde le scénario de la config, et on le dit
            print(f"Prix de vols indisponibles ({e}).", file=sys.stderr)
        if not flights:
            print("Aucun vol exploitable : scénario de la config seul.", file=sys.stderr)
    chosen, scenarios = compare(cfg, source, aeroports, trajets, flights, date.today())
    cfg, results = chosen.cfg, chosen.results
    itineraire = build(cfg, results, trajets)
    if chosen.flight:
        itineraire += "\n## Comparaison vols + hôtels\n\n" + render_scenarios(scenarios, chosen, cfg.voyageurs, cfg.devise)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(itineraire, encoding="utf-8")
    print(render(cfg, results) + "\n\n" + itineraire)
    if args.dry_run:  # données de test : ni historique ni alertes
        return
    hist_dir = ROOT / "historique"
    history = load_history(hist_dir / "prix.csv")
    found = alerts(cfg, results, history, date.today())
    history = write_history(hist_dir / "prix.csv", history, rows_for(results, date.today()))
    (hist_dir / "suivi.md").write_text(dashboard(cfg, history), encoding="utf-8")
    summary = chosen.resume
    if chosen.flight:  # additif : JARVIS ignore ces clés tant qu'il ne les lit pas
        f = chosen.flight
        summary.update(vol={"recherche": f.search, "arrivee": f.dest, "depart": f.back_from, "jour_aller": f.depart.isoformat(),
                            "jour_retour": f.back.isoformat(), "prix_personne": f.price},
                       total_avec_vols=round(chosen.totals(cfg.voyageurs)[0], 2))
    resume_json = json.dumps(summary, ensure_ascii=False, indent=1)
    (hist_dir / "resume.json").write_text(resume_json + "\n", encoding="utf-8")  # lu par JARVIS (outil hotel_itineraire)
    (args.out.parent / "alertes.md").write_text("\n".join(found) + "\n" if found else "", encoding="utf-8")
    print("\nAlertes :\n" + ("\n".join(found) if found else "aucune"))


if __name__ == "__main__":
    main()
