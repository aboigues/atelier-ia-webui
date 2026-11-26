"""Tests de outils/securite/exceptions.py (FR-008, data-model.md Exception de sécurité)."""

import datetime as dt
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "exceptions_securite", RACINE / "outils/securite/exceptions.py"
)
ex = importlib.util.module_from_spec(_spec)
sys.modules["exceptions_securite"] = ex
_spec.loader.exec_module(ex)

JOUR = dt.date(2026, 12, 1)


def fichier(*blocs):
    f = Path(tempfile.mkdtemp()) / "exceptions.toml"
    f.write_text("\n".join(blocs), encoding="utf-8")
    return f


def bloc(**champs):
    base = {
        "id": '"CVE-2026-0001"',
        "type": '"vulnerabilite"',
        "portee": '"ghcr.io/open-webui/open-webui"',
        "raison": '"Composant non exposé sur internet, suivi chaque semaine."',
        "acceptee_par": '"Alexandre"',
        "acceptee_le": "2026-11-26",
        "reexamen_le": "2027-01-15",
    }
    base.update(champs)
    corps = "\n".join(f"{k} = {v}" for k, v in base.items() if v is not None)
    return "[[exception]]\n" + corps + "\n"


class TestValidation(unittest.TestCase):
    def test_fichier_valide(self):
        excs = ex.charger(JOUR, fichier(bloc()))
        self.assertEqual(len(excs), 1)
        self.assertEqual(excs[0].etat(JOUR), "valide")

    def test_fichier_vide_accepte(self):
        self.assertEqual(ex.charger(JOUR, fichier("")), [])

    def test_champ_manquant(self):
        for champ in (
            "id",
            "type",
            "portee",
            "raison",
            "acceptee_par",
            "acceptee_le",
            "reexamen_le",
        ):
            with self.subTest(champ=champ), self.assertRaises(ex.ErreurExceptions):
                ex.charger(JOUR, fichier(bloc(**{champ: None})))

    def test_type_inconnu(self):
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(type='"autre"')))

    def test_portee_etoile_reservee_aux_classes(self):
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(portee='"*"')))
        ex.charger(JOUR, fichier(bloc(id='"elevee-sans-correctif"', type='"classe"', portee='"*"')))

    def test_raison_trop_courte(self):
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(raison='"trop court"')))

    def test_acceptee_par_alexandre_seulement(self):
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(acceptee_par='"Claude"')))

    def test_acceptation_dans_le_futur(self):
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(acceptee_le="2026-12-02", reexamen_le="2027-01-02")))

    def test_reexamen_au_plus_90_jours(self):
        ex.charger(JOUR, fichier(bloc(acceptee_le="2026-11-26", reexamen_le="2027-02-24")))
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(acceptee_le="2026-11-26", reexamen_le="2027-02-25")))

    def test_reexamen_apres_acceptation(self):
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(acceptee_le="2026-11-26", reexamen_le="2026-11-26")))

    def test_dates_au_mauvais_format(self):
        with self.assertRaises(ex.ErreurExceptions):
            ex.charger(JOUR, fichier(bloc(acceptee_le='"26/11/2026"')))


class TestEtats(unittest.TestCase):
    def test_echue_apres_reexamen(self):
        e = ex.charger(JOUR, fichier(bloc()))[0]
        self.assertEqual(e.etat(dt.date(2027, 1, 15)), "valide")
        self.assertEqual(e.etat(dt.date(2027, 1, 16)), "echue")

    def test_proche_echeance(self):
        e = ex.charger(JOUR, fichier(bloc()))[0]
        self.assertTrue(e.proche_echeance(dt.date(2027, 1, 2)))
        self.assertFalse(e.proche_echeance(dt.date(2026, 12, 1)))

    def test_charger_accepte_une_exception_deja_echue(self):
        # Une exception échue reste un fichier valide : elle cesse seulement de s'appliquer.
        excs = ex.charger(dt.date(2027, 6, 1), fichier(bloc()))
        self.assertEqual(excs[0].etat(dt.date(2027, 6, 1)), "echue")


class TestFichierDuDepot(unittest.TestCase):
    def test_exceptions_du_depot_valides(self):
        excs = ex.charger(dt.date(2026, 11, 26), RACINE / "securite/exceptions.toml")
        classes = [e for e in excs if e.type == "classe"]
        self.assertEqual([e.id for e in classes], ["elevee-sans-correctif"])


if __name__ == "__main__":
    unittest.main()
