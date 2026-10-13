"""Tests de la Phase 2 : ordre, répartition des nuits, recommandé, total, alertes. Sans réseau."""
import unittest
from datetime import date

from tracker.__main__ import run
from tracker.config import parse_config
from tracker.itineraire import build, plan_stays, recommended
from tracker.models import Hotel, Offer
from tracker.sources.sample import Sample

TRAJETS = {"kyoto-osaka": {"mode": "JR", "duree_min": 30, "prix_jpy": 1000, "reservation": False},
           "kyoto-tokyo": {"mode": "Shinkansen", "duree_min": 135, "prix_jpy": 10000, "reservation": True}}


def cfg(villes=None, depart="2027-05-22", taux=0.01):
    villes = villes or {
        "tokyo": {"xotelo_location_key": "g3", "nuits_min": 4, "aeroport": "HND"},
        "kyoto": {"xotelo_location_key": "g2", "nuits_min": 3},
        "osaka": {"xotelo_location_key": "g1", "nuits_min": 3, "aeroport": "KIX",
                  "activites": [{"nom": "USJ", "reservation_requise": True, "delai_reservation": 30}]},
    }
    return parse_config({"voyage": {"arrivee": "2027-05-06", "depart": depart, "aeroport_arrivee": "KIX",
                                    "aeroport_depart": "HND"},
                         "voyageurs": 2, "taux_jpy_eur": taux, "contraintes": {"note_min": 8, "avis_min": 100},
                         "villes": villes})


class PlanTest(unittest.TestCase):
    def test_ordre_selon_les_aeroports(self):
        self.assertEqual([v.name for v, _, _ in plan_stays(cfg())], ["osaka", "kyoto", "tokyo"])

    def test_nuits_couvrent_tout_le_voyage_et_respectent_le_minimum(self):
        for depart in ("2027-05-16", "2027-05-17", "2027-05-22", "2027-05-23"):  # 10, 11, 16, 17 nuits
            plan = plan_stays(cfg(depart=depart))
            with self.subTest(depart=depart):
                self.assertEqual(sum(n for _, _, n in plan), (date.fromisoformat(depart) - date(2027, 5, 6)).days)
                self.assertTrue(all(n >= v.nuits_min for v, _, n in plan))

    def test_sejours_consecutifs_et_poids_des_activites(self):
        plan = plan_stays(cfg())  # 16 nuits, 6 en plus, poids osaka 2 / kyoto 1 / tokyo 1
        self.assertEqual([n for _, _, n in plan], [7, 4, 5])
        self.assertEqual([d for _, d, _ in plan], [date(2027, 5, 6), date(2027, 5, 13), date(2027, 5, 17)])


class RecommendedTest(unittest.TestCase):
    def offer(self, key, rating, rate):
        return Offer(Hotel(key, key, "Hotel", rating, 500), "Agoda", rate, 3, 1)

    def test_meilleure_note_dans_le_seuil_de_prix(self):
        offers = [self.offer("cheap", 4.0, 100), self.offer("good", 4.5, 140), self.offer("luxe", 5.0, 400)]
        self.assertEqual(recommended(offers).hotel.key, "good")  # luxe dépasse 1,5 × 100

    def test_une_seule_offre(self):
        offers = [self.offer("seul", 4.0, 100)]
        self.assertIs(recommended(offers), offers[0])


class BuildTest(unittest.TestCase):
    def test_total_trajets_et_alerte(self):
        c = cfg()
        md = build(c, run(c, Sample()), TRAJETS)
        # trajets : (1000 + 10000) ¥ × 2 voyageurs × 0,01 = 220 €
        self.assertIn("trajets 220)", md)
        self.assertIn("réserver au plus tard le 2027-04-06", md)  # 2027-05-06 − 30 j
        self.assertNotIn("INCOMPLET", md)

    def test_trajet_inconnu_et_ville_sans_offre_disent_incomplet(self):
        c = cfg()
        md = build(c, run(c, Sample()), {})
        self.assertIn("INCOMPLET", md)
        self.assertIn("absent de data/trajets.yaml", md)
        c2 = cfg()
        c2.budget_max_nuit = 10
        md = build(c2, run(c2, Sample()), TRAJETS)
        self.assertIn("INCOMPLET", md)
        self.assertIn("budget_max_nuit", md)


if __name__ == "__main__":
    unittest.main()
