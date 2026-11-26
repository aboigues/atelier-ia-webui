"""Tests de outils/securite/verdict_codeql.py (contrôle sast-codeql, analyse D3)."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "verdict_codeql", RACINE / "outils/securite/verdict_codeql.py"
)
vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vc)


def sarif(resultats, regles):
    d = Path(tempfile.mkdtemp())
    contenu = {
        "runs": [
            {
                "tool": {"driver": {"name": "CodeQL", "rules": regles}},
                "results": resultats,
            }
        ]
    }
    (d / "python.sarif").write_text(json.dumps(contenu))
    return d


REGLE_SECU = {"id": "py/command-line-injection", "properties": {"tags": ["security"]}}
REGLE_QUALITE = {"id": "py/unused-import", "properties": {"tags": ["maintainability"]}}


def resultat(regle, niveau=None):
    r = {
        "ruleId": regle,
        "message": {"text": "constat"},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": "outils/x.py"},
                    "region": {"startLine": 12},
                }
            }
        ],
    }
    if niveau:
        r["level"] = niveau
    return r


class TestVerdictCodeQL(unittest.TestCase):
    def test_aucun_resultat(self):
        self.assertEqual(vc.alertes_bloquantes(sarif([], [REGLE_SECU])), [])

    def test_alerte_securite_bloque(self):
        d = sarif([resultat("py/command-line-injection", "error")], [REGLE_SECU])
        alertes = vc.alertes_bloquantes(d)
        self.assertEqual(len(alertes), 1)
        self.assertIn("outils/x.py:12", alertes[0])

    def test_niveau_par_defaut_warning_bloque(self):
        d = sarif([resultat("py/command-line-injection")], [REGLE_SECU])
        self.assertEqual(len(vc.alertes_bloquantes(d)), 1)

    def test_note_ne_bloque_pas(self):
        d = sarif([resultat("py/command-line-injection", "note")], [REGLE_SECU])
        self.assertEqual(vc.alertes_bloquantes(d), [])

    def test_regle_non_securite_ne_bloque_pas(self):
        d = sarif([resultat("py/unused-import", "warning")], [REGLE_QUALITE])
        self.assertEqual(vc.alertes_bloquantes(d), [])

    def test_dossier_sans_sarif_est_une_erreur(self):
        with self.assertRaises(vc.ErreurSarif):
            vc.alertes_bloquantes(Path(tempfile.mkdtemp()))


if __name__ == "__main__":
    unittest.main()
