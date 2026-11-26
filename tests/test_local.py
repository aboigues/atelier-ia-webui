"""Tests de outils/atelier/local.py (fonctions pures, sans Docker ni réseau)."""

import stat
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

from atelier import local  # noqa: E402


class TestEnvironnement(unittest.TestCase):
    def test_variables_et_secrets_passes_par_l_environnement(self):
        ident = {
            "courriel": "formateur@local.atelier",
            "mot_de_passe": "m" * 24,
            "secret": "s" * 43,
        }
        env = local.environnement("cle-scaleway", "projet-1", ident, base={"PATH": "/usr/bin"})
        self.assertEqual(env["OPENAI_API_KEY"], "cle-scaleway")
        self.assertEqual(env["OPENAI_API_BASE_URL"], "https://api.scaleway.ai/projet-1/v1")
        self.assertEqual(env["WEBUI_ADMIN_EMAIL"], "formateur@local.atelier")
        self.assertEqual(env["WEBUI_SECRET_KEY"], "s" * 43)
        self.assertEqual(env["PATH"], "/usr/bin")

    def test_commande_compose_sans_profil_session(self):
        cmd = local.commande_compose("up", "-d")
        self.assertIn("openwebui/compose.yaml", " ".join(cmd))
        self.assertNotIn("--profile", cmd)
        self.assertEqual(cmd[-2:], ["up", "-d"])


class TestIdentifiantsLocaux(unittest.TestCase):
    def test_generes_une_fois_puis_relus(self):
        d = Path(tempfile.mkdtemp()) / "local"
        premier = local.identifiants_locaux(d)
        second = local.identifiants_locaux(d)
        self.assertEqual(premier, second)
        self.assertGreaterEqual(len(premier["mot_de_passe"]), 16)
        self.assertGreaterEqual(len(premier["secret"]), 32)
        self.assertTrue(premier["courriel"].endswith("@local.atelier"))

    def test_fichier_reserve_au_formateur(self):
        d = Path(tempfile.mkdtemp()) / "local"
        local.identifiants_locaux(d)
        mode = stat.S_IMODE((d / "identifiants.txt").stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_dossier_ignore_par_git(self):
        self.assertTrue(str(local.DOSSIER_LOCAL).endswith("sessions/local"))


if __name__ == "__main__":
    unittest.main()
