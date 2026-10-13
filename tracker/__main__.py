"""Point d'entrée : python -m tracker [--dry-run] [--config config.yaml]"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .config import Config, load_config
from .filters import explain_empty, filter_hotels, filter_offers
from .itineraire import build, load_trajets, plan_stays, resume
from .models import Offer, rooms_for
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


def run(cfg: Config, source) -> list[CityResult]:
    rooms, adults = rooms_for(cfg.voyageurs)
    results = []
    for ville, chk_in, nights in plan_stays(cfg):
        res = CityResult(ville.name, chk_in.isoformat(), (chk_in + timedelta(days=nights)).isoformat(), nights)
        results.append(res)
        try:
            hotels, funnel = filter_hotels(source.list_hotels(ville.location_key), cfg)
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
                    offers.append(Offer(h, ota, rate, nights, rooms))
            offers, f2 = filter_offers(offers, cfg)
            res.offers = sorted(offers, key=lambda o: o.rate)
            if not res.offers:
                res.message = explain_empty(funnel + f2, cfg)
            if errors:
                res.message = (res.message + " " if res.message else "") + f"{errors} requête(s) de tarifs en échec."
        except Exception as e:  # une ville en panne n'arrête pas les autres, et la panne est dite
            res.message = f"Source en panne : {e}"  # plafond atteint : les villes suivantes le disent aussi
    return results


def render(cfg: Config, results: list[CityResult]) -> str:
    out = [f"{cfg.voyageurs} voyageur(s), note ≥ {cfg.note_min:g}/10, avis ≥ {cfg.avis_min}"
           + (f", ≤ {cfg.budget_max_nuit:g} €/nuit/chambre" if cfg.budget_max_nuit is not None else "")]
    for r in results:
        out.append(f"\n{r.ville.capitalize()} · {r.chk_in} → {r.chk_out}")
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
    parser.add_argument("--dry-run", action="store_true", help="données de test, aucun appel réseau")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # consoles Windows cp1252
    try:
        cfg = load_config(args.config)
    except ValueError as e:  # erreur de configuration : message clair, sans trace
        sys.exit(f"Configuration invalide : {e}")
    source = Sample() if args.dry_run else Xotelo(cfg.max_requests, cfg.pause_seconds)
    results = run(cfg, source)
    trajets = load_trajets(ROOT / "data" / "trajets.yaml")
    itineraire = build(cfg, results, trajets)
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
    resume_json = json.dumps(resume(cfg, results, trajets, date.today()), ensure_ascii=False, indent=1)
    (hist_dir / "resume.json").write_text(resume_json + "\n", encoding="utf-8")  # lu par JARVIS (outil hotel_itineraire)
    (args.out.parent / "alertes.md").write_text("\n".join(found) + "\n" if found else "", encoding="utf-8")
    print("\nAlertes :\n" + ("\n".join(found) if found else "aucune"))


if __name__ == "__main__":
    main()
