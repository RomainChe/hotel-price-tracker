"""Filtres note / avis / petit-déjeuner (sur la liste) et budget (sur les tarifs).

Chaque filtre renvoie aussi son libellé : l'entonnoir sert à dire quel critère assouplir quand il ne reste rien.
"""
from .config import Config

# critère de config.yaml -> libellé de l'entonnoir
LABELS = {
    "note_min": "note ≥ {c.note_min:g}/10",
    "avis_min": "avis ≥ {c.avis_min}",
    "petit_dejeuner": "petit-déjeuner inclus",
    "budget_max_nuit": "prix ≤ {c.budget_max_nuit:g} €/nuit",
}


def filter_hotels(hotels, c: Config):
    """Retourne (hôtels gardés, entonnoir [(critère, restants)]). La note Xotelo est /5, celle de la config /10."""
    funnel = [("listés", len(hotels))]
    steps = [("note_min", lambda h: h.rating >= c.note_min / 2), ("avis_min", lambda h: h.reviews >= c.avis_min)]
    if c.petit_dejeuner:
        steps.append(("petit_dejeuner", lambda h: h.breakfast))
    for crit, keep in steps:
        hotels = [h for h in hotels if keep(h)]
        funnel.append((crit, len(hotels)))
    return hotels, funnel


def filter_offers(offers, c: Config):
    """Garde les offres sous le budget par nuit (si défini). Retourne (offres, entonnoir)."""
    funnel = [("tarif", len(offers))]
    if c.budget_max_nuit is not None:
        offers = [o for o in offers if o.rate <= c.budget_max_nuit]
        funnel.append(("budget_max_nuit", len(offers)))
    return offers, funnel


def explain_empty(funnel, c: Config) -> str:
    """Message quand une ville n'a aucun résultat : où ça tombe à zéro et quel critère assouplir."""
    detail = " → ".join(
        f"{n} {LABELS[k].format(c=c) if k in LABELS else k}" for k, n in funnel)
    for crit, n in funnel:
        if n == 0:
            if crit == "listés":
                return f"Aucun hôtel listé par la source ({detail})."
            if crit == "tarif":
                return f"Aucun tarif disponible pour ces dates ({detail}) : les dates ne sont peut-être pas encore ouvertes."
            return f"Aucun hôtel ne passe le critère « {LABELS[crit].format(c=c)} » ({detail}). Assouplis `{crit}` dans config.yaml."
    return f"Aucun résultat ({detail})."
