"""Données de test pour `--dry-run` : aucun appel réseau, même interface que Xotelo."""
from ..models import Hotel

NAME = "sample"

_HOTELS = [  # (nom, type, note /5, avis, petit-déjeuner, prix par nuit)
    ("Hôtel Sakura", "Hotel", 4.5, 850, True, 120),
    ("Hôtel Midori", "Hotel", 4.0, 320, False, 85),
    ("Auberge Tsuki", "Inn", 3.5, 410, False, 60),      # note trop basse
    ("Hôtel Hoshi", "Hotel", 4.5, 40, False, 150),      # trop peu d'avis
    ("Hôtel Umi", "Hotel", 4.0, 220, False, 0),         # aucun tarif
]


class Sample:
    NAME = NAME

    def list_hotels(self, location_key: str) -> list[Hotel]:
        return [Hotel(key=f"{location_key}-{i}", name=n, accommodation_type=t, rating=r, reviews=c, breakfast=b)
                for i, (n, t, r, c, b, _) in enumerate(_HOTELS)]

    def rates(self, hotel_key, chk_in, chk_out, rooms, adults, currency):
        price = _HOTELS[int(hotel_key.rsplit("-", 1)[1])][5]
        return [("Agoda", price), ("Trip.com", price + 6)] if price else []
