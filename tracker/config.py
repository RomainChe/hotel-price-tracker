"""Lecture et validation de config.yaml."""
from dataclasses import dataclass
from datetime import date

import yaml


@dataclass
class Ville:
    name: str
    location_key: str  # clé Xotelo (ex. g298566)
    nuits_min: int


@dataclass
class Config:
    arrivee: date
    depart: date
    voyageurs: int
    devise: str
    villes: list[Ville]
    note_min: float  # sur 10
    avis_min: int
    budget_max_nuit: float | None = None  # par chambre et par nuit
    petit_dejeuner: bool = False
    max_requests: int = 200
    pause_seconds: tuple[float, float] = (1.0, 3.0)
    candidats_max: int = 10
    source: str = "xotelo"


def _date(value, label) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"{label} : date invalide « {value} » (format attendu AAAA-MM-JJ).") from None


def _ville(name: str, raw: dict | None) -> Ville:
    raw = raw or {}
    key = raw.get("xotelo_location_key")
    if not key:
        raise ValueError(f"villes.{name} : `xotelo_location_key` est obligatoire (ex. g298566).")
    nuits = int(raw.get("nuits_min", 1))
    if nuits < 1:
        raise ValueError(f"villes.{name} : `nuits_min` doit être au moins 1.")
    return Ville(name=str(name), location_key=str(key), nuits_min=nuits)


def parse_config(raw: dict) -> Config:
    voyage = raw.get("voyage") or {}
    arrivee, depart = _date(voyage.get("arrivee"), "voyage.arrivee"), _date(voyage.get("depart"), "voyage.depart")
    if depart <= arrivee:
        raise ValueError("voyage : `depart` doit être après `arrivee`.")
    voyageurs = int(raw.get("voyageurs", 2))
    if not 1 <= voyageurs <= 8:
        raise ValueError("voyageurs : de 1 à 8.")
    villes = [_ville(n, v) for n, v in (raw.get("villes") or {}).items()]
    if not villes:
        raise ValueError("config.yaml : aucune ville dans `villes`.")
    if sum(v.nuits_min for v in villes) > (depart - arrivee).days:
        raise ValueError("villes : la somme des `nuits_min` dépasse la durée du voyage.")

    c = raw.get("contraintes") or {}
    note_min = float(c.get("note_min", 0))
    if not 0 <= note_min <= 10:
        raise ValueError("contraintes.note_min : entre 0 et 10.")
    budget = c.get("budget_max_nuit")
    s = raw.get("source") or {}
    if s.get("nom", "xotelo") != "xotelo":
        raise ValueError(f"source.nom : « {s['nom']} » inconnue (seule `xotelo` existe).")
    pause = s.get("pause_seconds", [1, 3])
    try:
        pause = (float(pause[0]), float(pause[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("source.pause_seconds attend [min, max] en secondes.") from None
    if not 0 <= pause[0] <= pause[1]:
        raise ValueError("source.pause_seconds : le minimum doit être positif et inférieur au maximum.")

    return Config(
        arrivee=arrivee, depart=depart, voyageurs=voyageurs, devise=str(raw.get("devise", "EUR")).upper(),
        villes=villes, note_min=note_min, avis_min=int(c.get("avis_min", 0)),
        budget_max_nuit=float(budget) if budget is not None else None,
        petit_dejeuner=bool(c.get("petit_dejeuner", False)),
        max_requests=int(s.get("max_requests", 200)), pause_seconds=pause,
        candidats_max=int(s.get("candidats_max", 10)),
    )


def load_config(path) -> Config:
    with open(path, encoding="utf-8") as f:
        return parse_config(yaml.safe_load(f) or {})
