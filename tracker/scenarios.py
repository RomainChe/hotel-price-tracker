"""Scénarios vol + hôtel : les vols les moins chers de flight-price-tracker, chacun avec son itinéraire d'hôtels.

Chaque recherche du suivi de vols (dates fournies, dates flexibles...) donne ses `par_recherche` vols les moins chers
vers les aéroports du voyage ; on garde le scénario dont le total vols + hébergement + trajets est le plus bas.
"""
import csv
import io
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Flight:
    search: str
    dest: str  # aéroport d'arrivée
    back_from: str  # aéroport de départ du retour
    depart: date  # départ d'Europe ; arrivée au Japon le lendemain
    back: date  # jour du vol retour
    price: float  # par personne


@dataclass
class Scenario:
    flight: Flight | None
    cfg: object
    results: list
    resume: dict  # hébergement + trajets, au format de `resume()`

    def totals(self, voyageurs: int) -> tuple[float, float]:
        """(moins cher, recommandé) : vols pour tous les voyageurs + hébergement + trajets."""
        fl = self.flight.price * voyageurs if self.flight else 0.0
        return fl + self.resume["total_moins_cher"], fl + self.resume["total_recommande"]


def load_rows(src: str) -> list[dict]:
    """CSV de prix de flight-price-tracker : fichier local ou URL https (le contenu reste une donnée)."""
    if src.startswith("https://"):
        with urlopen(Request(src, headers={"User-Agent": "hotel-price-tracker"}), timeout=30) as r:
            text = r.read(8_000_000).decode("utf-8")
    else:
        text = Path(src).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def cheapest(rows: list[dict], airports: set[str], per_search: int = 2) -> list[Flight]:
    """Par recherche, dans son relevé le plus récent, les vols les moins chers dont l'arrivée et le retour sont des aéroports connus."""
    last: dict[str, str] = {}
    for r in rows:
        s, d = r.get("search", ""), r.get("run_date", "")
        if s and d > last.get(s, ""):
            last[s] = d
    best: dict[tuple, Flight] = {}
    for r in rows:
        if r.get("run_date") != last.get(r.get("search")):
            continue
        dest = (r.get("dest") or "").upper()
        back = (r.get("return_from") or dest).upper()
        try:
            f = Flight(r["search"], dest, back, date.fromisoformat(r["depart_date"]), date.fromisoformat(r["return_date"]),
                       float(r["price"]))
        except (KeyError, ValueError, TypeError):
            continue
        if dest in airports and back in airports and 0 < f.price < 100_000:
            key = (f.search, dest, back, f.depart, f.back)
            if key not in best or f.price < best[key].price:
                best[key] = f
    out, count = [], {}
    for f in sorted(best.values(), key=lambda f: f.price):
        count[f.search] = count.get(f.search, 0) + 1
        if count[f.search] <= per_search:
            out.append(f)
    return out


def with_flight(cfg, f: Flight):
    """Config du scénario : arrivée le lendemain du départ d'Europe, aéroports du vol."""
    return replace(cfg, arrivee=f.depart + timedelta(days=1), depart=f.back,
                   aeroport_arrivee=f.dest, aeroport_depart=f.back_from)


def pick(scenarios: list[Scenario], voyageurs: int) -> Scenario:
    """Le moins cher au total ; un scénario complet (une offre et un trajet partout) passe avant un incomplet."""
    return min(scenarios, key=lambda s: (not s.resume["complet"], s.totals(voyageurs)[0]))


def render(scenarios: list[Scenario], chosen: Scenario, voyageurs: int, devise: str) -> str:
    out = ["| Cas | Aéroports | Dates | Vol (×%d) | Hôtels + trajets | Total moins cher | Total recommandé |" % voyageurs,
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for s in sorted(scenarios, key=lambda s: s.totals(voyageurs)[0]):
        f, (cheap, reco) = s.flight, s.totals(voyageurs)
        mark = " ← retenu" if s is chosen else ""
        inc = "" if s.resume["complet"] else " (incomplet)"
        out.append(f"| {f.search if f else 'config'} | {f.dest} → {f.back_from} | {s.cfg.arrivee} → {s.cfg.depart} "
                   f"| {f.price * voyageurs:.0f} {devise} | {s.resume['total_moins_cher']:.0f} {devise}{inc} "
                   f"| {cheap:.0f} {devise}{mark} | {reco:.0f} {devise} |" if f else
                   f"| config | — | {s.cfg.arrivee} → {s.cfg.depart} | — | {s.resume['total_moins_cher']:.0f} {devise}{inc} "
                   f"| {cheap:.0f} {devise}{mark} | {reco:.0f} {devise} |")
    return "\n".join(out) + "\n"
