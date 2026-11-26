"""Tests de outils/securite/verdict_secrets.py (FR-006, FR-008, FR-012)."""

import datetime as dt
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def _charger(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, RACINE / chemin)
    module = importlib.util.module_from_spec(spec)
    sys.modules[nom] = module
    spec.loader.exec_module(module)
    return module


ex = _charger("exceptions_securite", "outils/securite/exceptions.py")
vs = _charger("verdict_secrets", "outils/securite/verdict_secrets.py")

JOUR = dt.date(2026, 12, 1)
# Faux jeton construit à l'exécution : jamais écrit en clair, donc jamais détecté dans le dépôt.
VALEUR_TEST = "ghp_" + "X" * 36


def trouvaille(commit="a1b2c3d4e5f6a7b8", fichier="config.py", ligne=3, detecteur="Github"):
    return {
        "SourceMetadata": {"Data": {"Git": {"commit": commit, "file": fichier, "line": ligne}}},
        "DetectorName": detecteur,
        "Verified": False,
        "Raw": VALEUR_TEST,
        "Redacted": "",
    }


def resultats(*lignes, brut=None):
    f = Path(tempfile.mkdtemp()) / "trufflehog.jsonl"
    f.write_text(brut if brut is not None else "\n".join(json.dumps(x) for x in lignes))
    return f


def faux_positif(id_, reexamen=dt.date(2027, 1, 15)):
    return ex.ExceptionSecurite(
        id_,
        "secret-faux-positif",
        "config.py",
        "Valeur fictive du jeu d'exemples, sans usage réel.",
        "Alexandre",
        dt.date(2026, 11, 26),
        reexamen,
    )


class TestVerdictSecrets(unittest.TestCase):
    def test_aucun_resultat(self):
        self.assertEqual(vs.fuites(resultats(brut=""), [], JOUR), [])

    def test_fuite_detectee_sans_afficher_le_secret(self):
        fuites = vs.fuites(resultats(trouvaille()), [], JOUR)
        self.assertEqual(len(fuites), 1)
        self.assertIn("config.py:3", fuites[0])
        self.assertIn("Github", fuites[0])
        self.assertNotIn(VALEUR_TEST, fuites[0])

    def test_faux_positif_valide_ignore(self):
        e = faux_positif("a1b2c3d4e5f6a7b8:config.py:3")
        self.assertEqual(vs.fuites(resultats(trouvaille()), [e], JOUR), [])

    def test_faux_positif_echu_ne_masque_plus(self):
        e = faux_positif("a1b2c3d4e5f6a7b8:config.py:3", reexamen=dt.date(2026, 11, 30))
        self.assertEqual(len(vs.fuites(resultats(trouvaille()), [e], JOUR)), 1)

    def test_faux_positif_autre_ligne_ne_masque_pas(self):
        e = faux_positif("a1b2c3d4e5f6a7b8:config.py:4")
        self.assertEqual(len(vs.fuites(resultats(trouvaille()), [e], JOUR)), 1)

    def test_ligne_illisible_est_une_erreur(self):
        with self.assertRaises(vs.ErreurSecrets):
            vs.fuites(resultats(brut="{pas du json"), [], JOUR)

    def test_fichier_absent_est_une_erreur(self):
        with self.assertRaises(vs.ErreurSecrets):
            vs.fuites(Path(tempfile.mkdtemp()) / "absent.jsonl", [], JOUR)


if __name__ == "__main__":
    unittest.main()
