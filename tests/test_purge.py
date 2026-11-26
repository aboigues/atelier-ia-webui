"""Tests du rapport de purge (outils/atelier/purge.py) et de l'export des consignes
(outils/atelier/session.py), sans réseau (contracts/fichiers-session.md)."""

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

from atelier import purge, session  # noqa: E402

DEBUT = dt.datetime(2026, 12, 11, 18, 0, tzinfo=dt.UTC)
FIN = DEBUT + dt.timedelta(minutes=4)


class TestRapport(unittest.TestCase):
    def test_purge_complete(self):
        texte = purge.rapport(
            "repetition", DEBUT, FIN, ["instance abc"], [], ["sessions/repetition/"]
        )
        self.assertIn("Résultat : purge complète", texte)
        self.assertIn("0 ressource", texte)
        self.assertIn("instance abc", texte)

    def test_purge_incomplete(self):
        restes = [("ip", "ip-1", "51.15.0.1")]
        texte = purge.rapport("repetition", DEBUT, FIN, [], restes, [])
        self.assertIn("purge incomplète", texte)
        self.assertIn("ip-1", texte)

    def test_aucun_nom_de_personne_ni_document(self):
        texte = purge.rapport(
            "repetition", DEBUT, FIN, ["instance abc"], [], ["sessions/repetition/"]
        )
        for interdit in ("Élodie", "Martin", ".pdf", ".ifc", "@"):
            self.assertNotIn(interdit, texte)


class TestSuppressionLocale(unittest.TestCase):
    def test_dossier_supprime_seulement_si_inventaire_vide(self):
        d = Path(tempfile.mkdtemp()) / "repetition"
        (d / "identifiants").mkdir(parents=True)
        (d / "participants.csv").write_text("prenom;nom\nA;B\n")
        self.assertEqual(purge.supprimer_local(d, restes=[("ip", "1", "x")]), [])
        self.assertTrue(d.exists())
        self.assertEqual(purge.supprimer_local(d, restes=[]), [str(d)])
        self.assertFalse(d.exists())


class TestExport(unittest.TestCase):
    def test_auteur_reduit_et_champs(self):
        prompts = [
            {"command": "scenario-1", "name": "Extraire", "content": "Texte", "user_id": "f"},
            {"command": "ma-fiche", "name": "Ma fiche", "content": "Autre", "user_id": "p"},
        ]
        consignes = session.exporter_consignes(prompts, "f")
        self.assertEqual(
            consignes,
            [
                {
                    "commande": "ma-fiche",
                    "titre": "Ma fiche",
                    "contenu": "Autre",
                    "auteur": "participant",
                },
                {
                    "commande": "scenario-1",
                    "titre": "Extraire",
                    "contenu": "Texte",
                    "auteur": "formateur",
                },
            ],
        )
        self.assertNotIn("user_id", str(consignes))
        self.assertIn(
            "## /scenario-1 : Extraire (formateur)", session.consignes_markdown(consignes)
        )


if __name__ == "__main__":
    unittest.main()
