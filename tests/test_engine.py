"""Tests du moteur, sans réseau. Style unittest : `python -m pytest -q` les collecte aussi."""
import unittest
from datetime import date

from tracker.__main__ import render, run
from tracker.config import parse_config
from tracker.filters import explain_empty, filter_hotels, filter_offers
from tracker.models import Hotel, Offer, rooms_for
from tracker.sources.sample import Sample
from tracker.sources.xotelo import BudgetExhausted, Xotelo

RAW = {
    "voyage": {"arrivee": "2027-05-06", "depart": "2027-05-22"},
    "voyageurs": 2,
    "contraintes": {"note_min": 8.0, "avis_min": 100},
    "villes": {"osaka": {"xotelo_location_key": "g1", "nuits_min": 3}, "kyoto": {"xotelo_location_key": "g2", "nuits_min": 2}},
}


def cfg(**over):
    raw = {**RAW, **over}
    raw["contraintes"] = {**RAW["contraintes"], **over.get("contraintes", {})}
    return parse_config(raw)


def hotel(key="h1", rating=4.5, reviews=500, breakfast=False):
    return Hotel(key=key, name=key, accommodation_type="Hotel", rating=rating, reviews=reviews, breakfast=breakfast)


class ConfigTest(unittest.TestCase):
    def test_nominal(self):
        c = cfg()
        self.assertEqual((c.arrivee, c.voyageurs, c.note_min, c.budget_max_nuit), (date(2027, 5, 6), 2, 8.0, None))
        self.assertEqual([v.name for v in c.villes], ["osaka", "kyoto"])

    def test_invalides(self):
        for bad in (
            {"voyage": {"arrivee": "2027-05-06", "depart": "2027-05-01"}},
            {"voyage": {"arrivee": "pas une date", "depart": "2027-05-22"}},
            {"voyageurs": 0},
            {"villes": {}},
            {"villes": {"osaka": {"nuits_min": 3}}},  # clé Xotelo manquante
            {"villes": {"osaka": {"xotelo_location_key": "g1", "nuits_min": 40}}},  # plus que le voyage
            {"contraintes": {"note_min": 12}},
            {"source": {"nom": "booking"}},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cfg(**bad)


class FilterTest(unittest.TestCase):
    def test_note_convertie_sur_5_et_avis(self):
        hotels = [hotel("ok"), hotel("note", rating=3.9), hotel("avis", reviews=99), hotel("limite", rating=4.0, reviews=100)]
        kept, funnel = filter_hotels(hotels, cfg())
        self.assertEqual([h.key for h in kept], ["ok", "limite"])
        self.assertEqual(funnel, [("listés", 4), ("note_min", 3), ("avis_min", 2)])

    def test_petit_dejeuner(self):
        kept, _ = filter_hotels([hotel("a", breakfast=True), hotel("b")], cfg(contraintes={"petit_dejeuner": True}))
        self.assertEqual([h.key for h in kept], ["a"])

    def test_budget_par_nuit(self):
        offers = [Offer(hotel("a"), "Agoda", 100, 3, 1), Offer(hotel("b"), "Agoda", 100.01, 3, 1)]
        kept, _ = filter_offers(offers, cfg(contraintes={"budget_max_nuit": 100}))
        self.assertEqual([o.hotel.key for o in kept], ["a"])

    def test_message_assouplir_le_bon_critere(self):
        c = cfg()
        _, funnel = filter_hotels([hotel(rating=3.0)], c)
        msg = explain_empty(funnel, c)
        self.assertIn("note_min", msg)
        self.assertIn("Assouplis", msg)


class ModelTest(unittest.TestCase):
    def test_chambres(self):
        self.assertEqual([rooms_for(n)[0] for n in (1, 2, 3, 4, 5, 6)], [1, 1, 1, 2, 3, 3])

    def test_total(self):
        self.assertEqual(Offer(hotel(), "Agoda", 50, 3, 2).total, 300)


class XoteloTest(unittest.TestCase):
    def fake_get(self, calls):
        def get(path, params):
            calls.append((path, params))
            if path == "/list":
                return {"list": [
                    {"name": "A", "key": "g1-d1", "accommodation_type": "Hotel",
                     "review_summary": {"rating": 4.5, "count": 300}, "merchandising_labels": ["Breakfast included"]},
                    {"name": "sans note", "key": "g1-d2", "review_summary": {"rating": None, "count": 0}},
                ]}
            return {"rates": [{"code": "Agoda", "name": "Agoda.com", "rate": 56}, {"code": "x", "name": "X", "rate": None}]}
        return get

    def test_liste_et_tarifs(self):
        calls = []
        x = Xotelo(get=self.fake_get(calls), sleep=lambda s: None)
        hotels = x.list_hotels("g1")
        self.assertEqual([(h.key, h.rating, h.reviews, h.breakfast) for h in hotels], [("g1-d1", 4.5, 300, True)])
        self.assertEqual(x.rates("g1-d1", "2027-05-06", "2027-05-09", 1, 2, "EUR"), [("Agoda.com", 56.0)])
        self.assertEqual(calls[1][1]["rooms"], 1)

    def test_plafond_de_requetes(self):
        x = Xotelo(max_requests=1, get=self.fake_get([]), sleep=lambda s: None)
        x.list_hotels("g1")
        with self.assertRaises(BudgetExhausted):
            x.list_hotels("g2")


class RunTest(unittest.TestCase):
    def test_dry_run_filtre_et_classe(self):
        results = run(cfg(), Sample())
        osaka = results[0]
        self.assertEqual([o.hotel.name for o in osaka.offers], ["Hôtel Midori", "Hôtel Sakura"])  # moins cher d'abord
        self.assertEqual(osaka.offers[0].ota, "Agoda")
        self.assertEqual((osaka.chk_in, osaka.chk_out), ("2027-05-06", "2027-05-09"))
        self.assertEqual(results[1].chk_in, "2027-05-09")  # séjours consécutifs
        self.assertEqual(osaka.offers[0].total, 85 * 3)
        self.assertIn("Osaka", render(cfg(), results))

    def test_aucun_resultat_est_dit(self):
        results = run(cfg(contraintes={"budget_max_nuit": 10}), Sample())
        self.assertEqual(results[0].offers, [])
        self.assertIn("budget_max_nuit", results[0].message)

    def test_panne_source_signalee_sans_arreter_les_autres(self):
        class Down(Sample):
            def list_hotels(self, key):
                if key == "g1":
                    raise RuntimeError("503")
                return super().list_hotels(key)
        results = run(cfg(), Down())
        self.assertIn("en panne", results[0].message)
        self.assertTrue(results[1].offers)

    def test_echec_de_tarifs_compte(self):
        class Flaky(Sample):
            def rates(self, *a):
                raise RuntimeError("timeout")
        res = run(cfg(), Flaky())[0]
        self.assertIn("en échec", res.message)

    def test_plafond_atteint_dit_sur_chaque_ville(self):
        results = run(cfg(source={"max_requests": 1}), Xotelo(1, (0, 0), get=lambda p, q: {"list": []}, sleep=lambda s: None))
        self.assertIn("plafond", results[1].message)


if __name__ == "__main__":
    unittest.main()
