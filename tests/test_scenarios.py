"""Scénarios vol + hôtel : vols retenus, itinéraire aller-retour par la même ville, choix du total le plus bas. Sans réseau."""
import unittest
from datetime import date

from tracker.__main__ import compare
from tracker.config import parse_config
from tracker.itineraire import plan_stays
from tracker.models import Hotel
from tracker.scenarios import Flight, cheapest

TRAJETS = {"kyoto-osaka": {"mode": "JR", "duree_min": 30, "prix_jpy": 1000, "reservation": False},
           "kyoto-tokyo": {"mode": "S", "duree_min": 135, "prix_jpy": 10000, "reservation": True},
           "osaka-tokyo": {"mode": "S", "duree_min": 150, "prix_jpy": 10000, "reservation": True},
           "nrt-tokyo": {"mode": "NEX", "duree_min": 60, "prix_jpy": 3000, "reservation": False},
           "hnd-tokyo": {"mode": "K", "duree_min": 30, "prix_jpy": 500, "reservation": False},
           "kix-osaka": {"mode": "JR", "duree_min": 70, "prix_jpy": 1200, "reservation": False}}
AEROPORTS = {c: {"lat": 35.0, "lon": 135.0} for c in ("KIX", "HND", "NRT")}


def cfg(**voyage):
    return parse_config({
        "voyage": {"arrivee": "2027-05-06", "depart": "2027-05-22", "aeroport_arrivee": "KIX", "aeroport_depart": "HND", **voyage},
        "voyageurs": 2, "taux_jpy_eur": 0.01, "contraintes": {"note_min": 8, "avis_min": 100},
        "villes": {"osaka": {"xotelo_location_key": "g1", "nuits_min": 3, "aeroports": {"KIX": "gK"}},
                   "kyoto": {"xotelo_location_key": "g2", "nuits_min": 3},
                   "tokyo": {"xotelo_location_key": "g3", "nuits_min": 4, "poids": 3, "aeroports": {"HND": None, "NRT": "gN"}}}})


class Fake:
    """Hôtels à 0,01° de l'aéroport ; le prix par nuit dépend de la zone (clé) : Tokyo est cher, Narita bon marché."""
    NAME = "fake"
    PRICE = {"g1": 100, "gK": 100, "g2": 100, "g3": 400, "gN": 50}

    def __init__(self):
        self.calls = 0

    def list_hotels(self, key):
        return [Hotel(f"{key}-1", f"Hotel {key}", "Hotel", 4.5, 500, lat=35.0, lon=135.0)]

    def rates(self, hotel_key, chk_in, chk_out, rooms, adults, currency):
        self.calls += 1
        return [("Agoda", float(self.PRICE[hotel_key.split("-")[0]]))]


class SelectionTest(unittest.TestCase):
    ROWS = [{"search": "fixe", "run_date": d, "dest": dest, "return_from": back, "depart_date": "2027-05-05",
             "return_date": "2027-05-22", "price": p}
            for d, dest, back, p in [("2026-10-12", "KIX", "HND", "100"),  # relevé périmé
                                     ("2026-10-13", "KIX", "HND", "700"), ("2026-10-13", "NRT", "NRT", "600"),
                                     ("2026-10-13", "FUK", "NRT", "300"),  # aéroport hors voyage
                                     ("2026-10-13", "NRT", "NRT", "650"), ("2026-10-13", "HND", "HND", "800")]]

    def test_dernier_releve_aeroports_connus_et_limite_par_recherche(self):
        got = cheapest(self.ROWS, {"KIX", "HND", "NRT"}, per_search=2)
        self.assertEqual([(f.dest, f.back_from, f.price) for f in got], [("NRT", "NRT", 600.0), ("KIX", "HND", 700.0)])


class ItineraireMemeVilleTest(unittest.TestCase):
    def test_narita_aller_retour(self):
        c = cfg(aeroport_arrivee="NRT", aeroport_depart="NRT")
        plan = plan_stays(c)
        self.assertEqual([v.name for v, _, _ in plan], ["nrt", "osaka", "kyoto", "tokyo", "nrt"])
        self.assertEqual(sum(n for _, _, n in plan), 16)
        self.assertEqual([v.location_key for v, _, _ in plan][0], "gN")
        self.assertEqual(plan[0][1], date(2027, 5, 6))
        self.assertEqual(plan[-1][1], date(2027, 5, 21))


class ChoixTest(unittest.TestCase):
    def test_vol_plus_cher_mais_total_plus_bas_gagne(self):
        flights = [Flight("fixe", "KIX", "HND", date(2027, 5, 5), date(2027, 5, 22), 650.0),  # vol le moins cher
                   Flight("fixe", "NRT", "NRT", date(2027, 5, 5), date(2027, 5, 22), 700.0)]  # +100 € pour 2, hôtels moins chers
        chosen, all_ = compare(cfg(), Fake(), AEROPORTS, TRAJETS, flights, date(2026, 10, 14))
        self.assertEqual(len(all_), 2)
        by = {s.flight.dest: s.totals(2)[0] for s in all_}
        self.assertLess(by["NRT"], by["KIX"])
        self.assertEqual(chosen.flight.dest, "NRT")
        self.assertTrue(chosen.resume["complet"])

    def test_sans_vol_scenario_de_la_config(self):
        chosen, all_ = compare(cfg(), Fake(), AEROPORTS, TRAJETS, [], date(2026, 10, 14))
        self.assertIsNone(chosen.flight)
        self.assertEqual(len(all_), 1)

    def test_derniere_nuit_toujours_pres_de_l_aeroport_de_depart(self):
        flights = [Flight("fixe", "KIX", "HND", date(2027, 5, 5), date(2027, 5, 22), 650.0)]
        chosen, _ = compare(cfg(), Fake(), AEROPORTS, TRAJETS, flights, date(2026, 10, 14))
        self.assertEqual(chosen.results[-1].ville, "hnd")
        self.assertEqual(chosen.results[-1].chk_out, "2027-05-22")

    def test_requetes_partagees_entre_scenarios(self):
        src = Fake()
        f = Flight("fixe", "KIX", "HND", date(2027, 5, 5), date(2027, 5, 22), 650.0)
        compare(cfg(), src, AEROPORTS, TRAJETS, [f], date(2026, 10, 14))
        one = src.calls
        src.calls = 0
        compare(cfg(), src, AEROPORTS, TRAJETS, [f, f], date(2026, 10, 14))
        self.assertEqual(src.calls, one)  # le second scénario identique ne refait aucune requête


if __name__ == "__main__":
    unittest.main()
