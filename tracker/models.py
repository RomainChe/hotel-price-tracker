"""Hôtel, offre et règle de répartition des voyageurs en chambres."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Hotel:
    key: str
    name: str
    accommodation_type: str
    rating: float  # /5 (TripAdvisor)
    reviews: int
    url: str = ""
    breakfast: bool = False  # « Breakfast included » annoncé par la liste


@dataclass(frozen=True)
class Offer:
    hotel: Hotel
    ota: str
    rate: float  # par chambre et par nuit, dans la devise demandée
    nights: int
    rooms: int

    @property
    def total(self) -> float:
        return self.rate * self.nights * self.rooms


def rooms_for(voyageurs: int) -> tuple[int, int]:
    """(chambres, adultes) à demander : 1 à 3 voyageurs = 1 chambre, au-delà plusieurs chambres de 2."""
    return (1 if voyageurs <= 3 else -(-voyageurs // 2)), voyageurs
