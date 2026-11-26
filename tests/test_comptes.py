"""Tests de outils/atelier/comptes.py (data-model.md Compte, contracts/fichiers-session.md)."""

import stat
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

from atelier import comptes  # noqa: E402
from atelier.config import Participant  # noqa: E402


class TestCourriel(unittest.TestCase):
    def test_normalisation(self):
        self.assertEqual(
            comptes.courriel("Élodie", "Le Fèvre", "repetition"),
            "elodie.le-fevre@repetition.atelier",
        )
        self.assertEqual(comptes.courriel("Chloé", "Garçon", "x-1"), "chloe.garcon@x-1.atelier")

    def test_doublons(self):
        liste = comptes.generer(
            [
                Participant("Élodie", "Martin"),
                Participant("Elodie", "Martin"),
                Participant("Théo", "Fontaine"),
            ],
            "repetition",
        )
        self.assertEqual(
            [c.courriel for c in liste],
            [
                "elodie.martin@repetition.atelier",
                "elodie.martin-2@repetition.atelier",
                "theo.fontaine@repetition.atelier",
            ],
        )
        self.assertTrue(all(c.role == "participant" for c in liste))


class TestMotDePasse(unittest.TestCase):
    def test_quatre_mots_et_longueur(self):
        for _ in range(50):
            mdp = comptes.mot_de_passe()
            self.assertGreaterEqual(len(mdp), 16)
            self.assertEqual(len(mdp.split("-")), 5)  # 4 mots et un nombre

    def test_aleatoire(self):
        self.assertEqual(len({comptes.mot_de_passe() for _ in range(200)}), 200)


class TestFiches(unittest.TestCase):
    def test_fiches_ecrites_hors_depot_en_0600(self):
        d = Path(tempfile.mkdtemp())
        liste = comptes.generer([Participant("Théo", "Fontaine")], "repetition")
        formateur = comptes.compte_formateur("repetition")
        comptes.ecrire_fiches(
            d,
            liste + [formateur],
            "Client fictif",
            "https://repetition.atelier.telemach-learning.fr",
            "https://repetition.atelier.telemach-learning.fr/acces/jeton",
        )
        fiche = (d / "theo-fontaine.txt").read_text(encoding="utf-8")
        self.assertIn("theo.fontaine@repetition.atelier", fiche)
        self.assertIn("/acces/jeton", fiche)
        self.assertIn("supprimés à la fin de la session", fiche)
        self.assertTrue((d / "formateur.txt").exists())
        self.assertEqual(stat.S_IMODE((d / "theo-fontaine.txt").stat().st_mode), 0o600)
        self.assertEqual(formateur.role, "formateur")


if __name__ == "__main__":
    unittest.main()
