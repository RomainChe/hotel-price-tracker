"""Lecture et validation de config.yaml."""
from dataclasses import dataclass, field
from datetime import date

import yaml


@dataclass
class Activite:
    nom: str
    reservation_requise: bool = False
    delai_reservation: int = 0  # jours avant le séjour


@dataclass
class Ville:
    name: str
    location_key: str  # clé Xotelo (ex. g298566)
    nuits_min: int
    poids: int = 0  # 0 = 1 + nombre d'activités ; plus il est grand, plus la ville reçoit de nuits en plus
    proche_aeroport: bool = False  # étape d'une nuit choisie près de `aeroport` (créée par plan_stays)
    aeroports: dict = field(default_factory=dict)  # code -> clé Xotelo de la zone de l'aéroport ("" = celle de la ville)
    parent: str = ""  # ville d'une étape « aéroport » (pour retrouver le trajet)
    aeroport: str = ""  # code de l'étape « aéroport » ; vide pour une ville. # sert à fixer l'ordre : la ville de l'aéroport d'arrivée d'abord, celle du départ en dernier
    activites: tuple[Activite, ...] = ()  # leur nombre pèse dans la répartition des nuits supplémentaires


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
    aeroport_arrivee: str = ""
    aeroport_depart: str = ""
    taux_jpy_eur: float = 0.0061
    vols_csv: str = ""  # prix de flight-price-tracker (fichier ou URL https) : active la comparaison vol + hôtel
    vols_par_recherche: int = 2  # vols les moins chers essayés par recherche de vols
    nuit_aeroport: bool = True  # 1re nuit près de l'aéroport d'arrivée, dernière près de celui du départ
    rayon_aeroport_km: float = 15.0  # étape « près de l'aéroport » : hôtels à moins de N km, les plus proches d'abord
    alerte_total_sous: float | None = None  # hébergement recommandé, pour tous les voyageurs
    alerte_baisse_pct: float = 5.0
    alerte_hotel_disparu: bool = True


def _date(value, label) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"{label} : date invalide « {value} » (format attendu AAAA-MM-JJ).") from None


def _aeroports(raw: dict) -> dict:
    """`aeroports: {KIX: g298200, HND: null}` (ou liste) ; l'ancienne forme `aeroport: KIX` + `aeroport_location_key` reste lue."""
    a = raw.get("aeroports")
    if isinstance(a, dict):
        return {str(k).upper(): str(v or "") for k, v in a.items()}
    if isinstance(a, list):
        return {str(k).upper(): "" for k in a}
    one = str(raw.get("aeroport", "")).upper()
    return {one: str(raw.get("aeroport_location_key", ""))} if one else {}


def _ville(name: str, raw: dict | None) -> Ville:
    raw = raw or {}
    key = raw.get("xotelo_location_key")
    if not key:
        raise ValueError(f"villes.{name} : `xotelo_location_key` est obligatoire (ex. g298566).")
    nuits = int(raw.get("nuits_min", 1))
    if nuits < 1:
        raise ValueError(f"villes.{name} : `nuits_min` doit être au moins 1.")
    activites = tuple(
        Activite(str(a.get("nom", "?")), bool(a.get("reservation_requise", False)), int(a.get("delai_reservation", 0)))
        for a in raw.get("activites") or [])
    return Ville(name=str(name), location_key=str(key), nuits_min=nuits, poids=int(raw.get("poids", 0)),
                 aeroports=_aeroports(raw), activites=activites)


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
    a = raw.get("alertes") or {}
    total_sous = a.get("total_sous")
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
        aeroport_arrivee=str(voyage.get("aeroport_arrivee", "")).upper(),
        aeroport_depart=str(voyage.get("aeroport_depart", "")).upper(),
        vols_csv=str((raw.get("vols") or {}).get("csv", "")),
        vols_par_recherche=max(1, int((raw.get("vols") or {}).get("par_recherche", 2))),
        nuit_aeroport=bool(voyage.get("nuit_aeroport", True)),
        rayon_aeroport_km=float(voyage.get("rayon_aeroport_km", 15)),
        taux_jpy_eur=float(raw.get("taux_jpy_eur", 0.0061)),
        alerte_total_sous=float(total_sous) if total_sous is not None else None,
        alerte_baisse_pct=float(a.get("baisse_pct", 5)), alerte_hotel_disparu=bool(a.get("hotel_disparu", True)),
    )


def load_config(path) -> Config:
    with open(path, encoding="utf-8") as f:
        return parse_config(yaml.safe_load(f) or {})
