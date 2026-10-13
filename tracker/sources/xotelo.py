"""Source Xotelo (data.xotelo.com, gratuite, sans clé) : /list par ville, /rates par hôtel.

Interface d'une source : NAME, `list_hotels(location_key)` et `rates(hotel_key, chk_in, chk_out, rooms, adults, currency)`.
`rate` est un prix par chambre et par nuit (vérifié le 2026-10-13 : 2 chambres / 4 adultes = même prix que 1 / 2).
"""
import json
import random
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import Hotel

NAME = "xotelo"
BASE = "https://data.xotelo.com/api"
LIST_LIMIT = 100  # une page triée « best_value » ; ponytail : pas de pagination, à ajouter si une ville n'a pas assez de candidats


class BudgetExhausted(RuntimeError):
    """Le plafond `max_requests` est atteint : on s'arrête au lieu d'insister auprès d'un service gratuit."""


def http_get(path: str, params: dict, timeout: float = 20) -> dict:
    req = Request(f"{BASE}{path}?{urlencode(params)}", headers={"User-Agent": "hotel-price-tracker"})
    with urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    if data.get("error"):
        raise RuntimeError(f"Xotelo : {data['error']}")
    return data["result"]


class Xotelo:
    NAME = NAME

    def __init__(self, max_requests: int = 200, pause_seconds=(1.0, 3.0), get=http_get, sleep=time.sleep):
        self.max_requests, self.pause, self._get, self._sleep = max_requests, pause_seconds, get, sleep
        self.requests = 0

    def _call(self, path: str, params: dict) -> dict:
        if self.requests >= self.max_requests:
            raise BudgetExhausted(f"plafond de {self.max_requests} requêtes atteint")
        if self.requests:
            self._sleep(random.uniform(*self.pause))
        self.requests += 1
        return self._get(path, params)

    def list_hotels(self, location_key: str) -> list[Hotel]:
        res = self._call("/list", {"location_key": location_key, "limit": LIST_LIMIT, "offset": 0, "sort": "best_value"})
        hotels = []
        for h in res.get("list") or []:
            summary = h.get("review_summary") or {}
            if not h.get("key") or summary.get("rating") is None:  # sans note : impossible à filtrer, donc écarté
                continue
            hotels.append(Hotel(
                key=h["key"], name=h.get("name", ""), accommodation_type=h.get("accommodation_type") or "",
                rating=float(summary["rating"]), reviews=int(summary.get("count") or 0), url=h.get("url") or "",
                breakfast="Breakfast included" in (h.get("merchandising_labels") or []),
            ))
        return hotels

    def rates(self, hotel_key: str, chk_in: str, chk_out: str, rooms: int, adults: int, currency: str) -> list[tuple[str, float]]:
        """[(OTA, prix par chambre et par nuit)] ; liste vide si aucune offre pour ces dates."""
        res = self._call("/rates", {"hotel_key": hotel_key, "chk_in": chk_in, "chk_out": chk_out,
                                    "rooms": rooms, "adults": adults, "currency": currency})
        return [(r.get("name") or r.get("code") or "?", float(r["rate"])) for r in res.get("rates") or [] if r.get("rate")]
