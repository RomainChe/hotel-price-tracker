"""Tests de la Phase 3 : historique, alertes, tableau de suivi. Sans réseau."""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tests.test_itineraire import cfg
from tracker.__main__ import CityResult
from tracker.models import Hotel, Offer
from tracker.suivi import alerts, dashboard, load_history, rows_for, write_history

HIER, AUJ = date(2026, 10, 12), date(2026, 10, 13)


def result(ville, *offers):
    return CityResult(ville, "2027-05-06", "2027-05-10", 4, [Offer(Hotel(k, k, "Hotel", r, 500), "Agoda", p, 4, 1)
                                                            for k, r, p in offers])


def config(**alertes):
    c = cfg()
    for k, v in alertes.items():
        setattr(c, k, v)
    return c


class SuiviTest(unittest.TestCase):
    def setUp(self):
        self.hier = rows_for([result("osaka", ("a", 4.5, 100), ("b", 4.0, 80))], HIER)

    def test_historique_ecrit_relu_et_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "h" / "prix.csv"
            new = rows_for([result("osaka", ("a", 4.5, 100))], AUJ)
            write_history(path, [], new)
            rows = write_history(path, load_history(path), new)  # même jour relancé
            self.assertEqual(len(rows), 1)
            self.assertEqual(load_history(path)[0]["hotel"], "a")

    def test_baisse_au_dela_du_seuil(self):
        found = alerts(config(), [result("osaka", ("a", 4.5, 90), ("b", 4.0, 80))], self.hier, AUJ)
        self.assertEqual(len(found), 1)
        self.assertIn("a baisse de 100 à 90", found[0])

    def test_petite_baisse_ignoree(self):
        self.assertEqual(alerts(config(), [result("osaka", ("a", 4.5, 98), ("b", 4.0, 80))], self.hier, AUJ), [])

    def test_hotel_disparu(self):
        found = alerts(config(), [result("osaka", ("b", 4.0, 80), ("c", 3.5, 70))], self.hier, AUJ)
        self.assertIn("a n'a plus de tarif", found[0])

    def test_ville_en_panne_pas_de_fausse_alerte(self):
        self.assertEqual(alerts(config(), [CityResult("osaka", "2027-05-06", "2027-05-10", 4, [], "panne")],
                                self.hier, AUJ), [])

    def test_premier_releve_sans_alerte(self):
        self.assertEqual(alerts(config(), [result("osaka", ("a", 4.5, 50))], [], AUJ), [])

    def test_total_sous_le_seuil_seulement_si_complet(self):
        full = [result(v, ("x", 4.5, 100)) for v in ("osaka", "kyoto", "tokyo")]  # 3 × 400
        self.assertEqual(len(alerts(config(alerte_total_sous=1500), full, [], AUJ)), 1)
        self.assertEqual(alerts(config(alerte_total_sous=1000), full, [], AUJ), [])
        self.assertEqual(alerts(config(alerte_total_sous=1500), full[:2] + [result("tokyo")], [], AUJ), [])

    def test_dashboard_marque_les_releves_incomplets(self):
        rows = rows_for([result("osaka", ("a", 4.5, 100)), result("kyoto", ("k", 4.5, 50))], AUJ) \
            + rows_for([result("osaka", ("a", 4.5, 90))], HIER)
        text = dashboard(config(), rows)
        self.assertIn("| 2026-10-13 | 50 | 100 | 600 |", text)
        self.assertIn("| 2026-10-12 | — | 90 | incomplet |", text)


if __name__ == "__main__":
    unittest.main()
