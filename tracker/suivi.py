"""Phase 3 : historique CSV, alertes (baisse, hôtel disparu, total sous le seuil) et tableau de suivi."""
import csv
from datetime import date

from .itineraire import recommended
from .models import Hotel, Offer

FIELDS = ["date", "ville", "chk_in", "chk_out", "hotel_key", "hotel", "rating", "reviews", "ota", "rate", "nights", "rooms"]


def load_history(path) -> list[dict]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def rows_for(results, today: date) -> list[dict]:
    return [dict(date=today.isoformat(), ville=r.ville, chk_in=r.chk_in, chk_out=r.chk_out, hotel_key=o.hotel.key,
                 hotel=o.hotel.name, rating=o.hotel.rating, reviews=o.hotel.reviews, ota=o.ota, rate=o.rate,
                 nights=o.nights, rooms=o.rooms) for r in results for o in r.offers]


def write_history(path, history: list[dict], new: list[dict]) -> list[dict]:
    """Remplace les lignes du jour (relancer le même jour ne duplique pas) et réécrit le fichier."""
    days = {r["date"] for r in new}
    rows = [r for r in history if r["date"] not in days] + new
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


def _offer(row: dict) -> Offer:
    return Offer(Hotel(row["hotel_key"], row["hotel"], "", float(row["rating"]), int(row["reviews"])),
                 row["ota"], float(row["rate"]), int(row["nights"]), int(row["rooms"]))


def _previous(history: list[dict], today: date, ville: str, chk_in: str, chk_out: str) -> list[dict]:
    """Lignes du relevé le plus récent avant `today` pour ce même séjour ([] si aucun)."""
    rows = [r for r in history if r["ville"] == ville and r["chk_in"] == chk_in and r["chk_out"] == chk_out
            and r["date"] < today.isoformat()]
    last = max((r["date"] for r in rows), default=None)
    return [r for r in rows if r["date"] == last]


def alerts(cfg, results, history: list[dict], today: date) -> list[str]:
    """Hôtels suivis = le recommandé et le moins cher du relevé précédent (évite les faux « disparus » dus au plafond de candidats)."""
    out = []
    for r in results:
        if not r.offers:  # panne ou critères trop stricts : on ne peut pas conclure
            continue
        prev = [_offer(x) for x in _previous(history, today, r.ville, r.chk_in, r.chk_out)]
        if not prev:
            continue
        prev.sort(key=lambda o: o.rate)
        watched = {o.hotel.key: o for o in (recommended(prev), prev[0])}.values()
        now = {o.hotel.key: o for o in r.offers}
        for old in watched:
            cur = now.get(old.hotel.key)
            if cur is None:
                if cfg.alerte_hotel_disparu:
                    out.append(f"- {r.ville.capitalize()} : {old.hotel.name} n'a plus de tarif (était à {old.rate:g} {cfg.devise}/nuit).")
            elif cur.rate <= old.rate * (1 - cfg.alerte_baisse_pct / 100):
                out.append(f"- {r.ville.capitalize()} : {old.hotel.name} baisse de {old.rate:g} à {cur.rate:g} {cfg.devise}/nuit "
                           f"({r.chk_in} → {r.chk_out}, {cur.ota}).")
    if cfg.alerte_total_sous is not None and results and all(r.offers for r in results):
        total = sum(recommended(r.offers).total for r in results)
        if total < cfg.alerte_total_sous:
            out.append(f"- Hébergement recommandé à {total:.0f} {cfg.devise}, sous le seuil de {cfg.alerte_total_sous:g} {cfg.devise}.")
    return out


def dashboard(cfg, history: list[dict]) -> str:
    """Par relevé : moins cher par ville (€/nuit) et total d'hébergement le moins cher (si toutes les villes ont une offre)."""
    villes = sorted({r["ville"] for r in history})
    by_day: dict[str, dict[str, float]] = {}
    totals: dict[str, dict[str, float]] = {}
    for r in history:
        rate, tot = float(r["rate"]), float(r["rate"]) * int(r["nights"]) * int(r["rooms"])
        d = by_day.setdefault(r["date"], {})
        if r["ville"] not in d or rate < d[r["ville"]]:
            d[r["ville"]] = rate
        t = totals.setdefault(r["date"], {})
        t[r["ville"]] = min(t.get(r["ville"], tot), tot)
    out = [f"# Suivi des prix ({cfg.devise})", "",
           "| Relevé | " + " | ".join(f"{v.capitalize()} (/nuit)" for v in villes) + " | Total le moins cher |",
           "|" + " --- |" * (len(villes) + 2)]
    for day in sorted(by_day, reverse=True)[:30]:
        cells = [f"{by_day[day][v]:g}" if v in by_day[day] else "—" for v in villes]
        total = f"{sum(totals[day].values()):.0f}" if len(totals[day]) == len(villes) else "incomplet"
        out.append(f"| {day} | " + " | ".join(cells) + f" | {total} |")
    return "\n".join(out) + "\n"
