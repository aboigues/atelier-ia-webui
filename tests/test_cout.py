"""Tests de outils/atelier/cout.py (FR-015, research.md R10)."""

import datetime as dt
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

from atelier import config, cout  # noqa: E402

TARIFS = config.Tarifs(
    dt.date(2026, 11, 26),
    {"mistral-medium-3.5-128b": {"entree_eur_par_million": 1.5, "sortie_eur_par_million": 7.5}},
    {
        "demandes_par_participant": 150,
        "jetons_entree_par_demande": 8000,
        "jetons_sortie_par_demande": 1000,
        "heures_instance": 72,
        "ip_eur_par_heure": 0.004,
    },
)


class TestCout(unittest.TestCase):
    def test_estimation_de_reference(self):
        e = cout.estimer(0.0428, TARIFS, 10, "mistral-medium-3.5-128b")
        self.assertAlmostEqual(e["instance"], 3.08, places=2)
        self.assertAlmostEqual(e["ip"], 0.29, places=2)
        self.assertAlmostEqual(e["modele"], 29.25, places=2)
        self.assertAlmostEqual(e["total"], 32.62, places=2)

    def test_modele_sans_tarif(self):
        with self.assertRaises(config.ErreurConfig):
            cout.estimer(0.0428, TARIFS, 10, "modele-inconnu")

    def test_texte(self):
        texte = cout.texte(
            cout.estimer(0.0428, TARIFS, 10, "mistral-medium-3.5-128b"), 10, "DEV1-L"
        )
        self.assertIn("Total estimé", texte)
        self.assertIn("32,62", texte)


if __name__ == "__main__":
    unittest.main()
