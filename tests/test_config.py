"""Tests de outils/atelier/config.py (data-model.md Session et Compte, contracts/fichiers-session.md)."""

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

from atelier import config  # noqa: E402

TOML = """id = "{id}"
client = "Client fictif"
debut = {debut}
fin = {fin}
"""


def dossier_session(id_="repetition", debut="2026-12-07", fin="2026-12-08", csv=None):
    d = Path(tempfile.mkdtemp())
    (d / "session.toml").write_text(TOML.format(id=id_, debut=debut, fin=fin), encoding="utf-8")
    (d / "participants.csv").write_text(
        csv if csv is not None else "prenom;nom\nÉlodie;Martin\n", encoding="utf-8"
    )
    return d


class TestSession(unittest.TestCase):
    def test_valeurs_par_defaut(self):
        s = config.lire_session(dossier_session())
        self.assertEqual(s.id, "repetition")
        self.assertEqual(s.type_instance, "DEV1-L")
        self.assertEqual(s.modele_reference, "mistral-medium-3.5-128b")
        self.assertEqual(s.modele_secours, "mistral-small-3.2-24b-instruct-2506")

    def test_echeance_garde_fou(self):
        s = config.lire_session(dossier_session(fin="2026-12-08"))
        attendu = dt.datetime(2026, 12, 10, 18, 0, tzinfo=config.PARIS)
        self.assertEqual(s.echeance_garde_fou, attendu)

    def test_identifiant_invalide(self):
        for id_ in ("A", "ab", "Majuscule", "trop_" + "x" * 30, "espace x"):
            with self.subTest(id_=id_), self.assertRaises(config.ErreurConfig):
                config.lire_session(dossier_session(id_=id_))

    def test_dates(self):
        with self.assertRaises(config.ErreurConfig):
            config.lire_session(dossier_session(debut="2026-12-08", fin="2026-12-07"))
        with self.assertRaises(config.ErreurConfig):
            config.lire_session(dossier_session(debut="2026-12-01", fin="2026-12-09"))

    def test_fichier_absent(self):
        with self.assertRaises(config.ErreurConfig):
            config.lire_session(Path(tempfile.mkdtemp()))

    def test_exemple_du_depot(self):
        s = config.lire_session(RACINE / "exemples/session")
        self.assertEqual(s.id, "repetition")


class TestParticipants(unittest.TestCase):
    def test_point_virgule_et_virgule(self):
        for csv in ("prenom;nom\nÉlodie;Martin\nThéo;Fontaine\n", "prenom,nom\nÉlodie,Martin\nThéo,Fontaine\n"):
            with self.subTest(csv=csv):
                p = config.lire_participants(dossier_session(csv=csv))
                self.assertEqual([(x.prenom, x.nom) for x in p], [("Élodie", "Martin"), ("Théo", "Fontaine")])

    def test_entete_obligatoire(self):
        with self.assertRaises(config.ErreurConfig):
            config.lire_participants(dossier_session(csv="Élodie;Martin\n"))

    def test_nombre_de_lignes(self):
        with self.assertRaises(config.ErreurConfig):
            config.lire_participants(dossier_session(csv="prenom;nom\n"))
        lignes = "".join(f"P{i};N{i}\n" for i in range(16))
        with self.assertRaises(config.ErreurConfig):
            config.lire_participants(dossier_session(csv="prenom;nom\n" + lignes))

    def test_champ_vide(self):
        with self.assertRaises(config.ErreurConfig):
            config.lire_participants(dossier_session(csv="prenom;nom\n;Martin\n"))

    def test_exemple_du_depot(self):
        self.assertEqual(len(config.lire_participants(RACINE / "exemples/session")), 10)


class TestTarifs(unittest.TestCase):
    def test_tarifs_recents(self):
        t = config.lire_tarifs(RACINE / "infra/tarifs.toml", dt.date(2026, 12, 1))
        self.assertEqual(t.modeles["mistral-medium-3.5-128b"]["entree_eur_par_million"], 1.5)

    def test_tarifs_perimes(self):
        with self.assertRaises(config.ErreurConfig):
            config.lire_tarifs(RACINE / "infra/tarifs.toml", dt.date(2027, 1, 1))


if __name__ == "__main__":
    unittest.main()
