"""Tests de outils/securite/regles_github.py (FR-004, FR-005, FR-006, analyses D1 et D2)."""

import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "regles_github", RACINE / "outils/securite/regles_github.py"
)
rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rg)

ATTENDU = json.loads((RACINE / ".github/rulesets/main.json").read_text(encoding="utf-8"))
SECURITE_OK = {
    "security_and_analysis": {
        "secret_scanning": {"status": "enabled"},
        "secret_scanning_push_protection": {"status": "enabled"},
    }
}


def regle(etat, type_):
    return next(r for r in etat["rules"] if r["type"] == type_)


class TestComparaison(unittest.TestCase):
    def setUp(self):
        self.reel = copy.deepcopy(ATTENDU) | {"id": 42}

    def ecarts(self, depot=SECURITE_OK):
        return rg.ecarts(ATTENDU, self.reel, depot)

    def test_identique(self):
        self.assertEqual(self.ecarts(), [])

    def test_regle_manquante(self):
        self.reel["rules"] = [r for r in self.reel["rules"] if r["type"] != "non_fast_forward"]
        self.assertTrue(any("non_fast_forward" in e for e in self.ecarts()))

    def test_controle_requis_manquant(self):
        p = regle(self.reel, "required_status_checks")["parameters"]
        p["required_status_checks"] = p["required_status_checks"][:-1]
        self.assertTrue(any("tests" in e for e in self.ecarts()))

    def test_controle_requis_sans_integration_github_actions(self):
        p = regle(self.reel, "required_status_checks")["parameters"]
        del p["required_status_checks"][0]["integration_id"]
        self.assertTrue(any("15368" in e for e in self.ecarts()))

    def test_acteur_de_contournement(self):
        self.reel["bypass_actors"] = [{"actor_id": 5, "actor_type": "RepositoryRole"}]
        self.assertTrue(any("contournement" in e for e in self.ecarts()))

    def test_enforcement_desactive(self):
        self.reel["enforcement"] = "evaluate"
        self.assertTrue(any("enforcement" in e for e in self.ecarts()))

    def test_merge_classique_autorise(self):
        regle(self.reel, "pull_request")["parameters"]["allowed_merge_methods"].append("merge")
        self.assertTrue(any("merge" in e for e in self.ecarts()))

    def test_politique_non_stricte(self):
        p = regle(self.reel, "required_status_checks")["parameters"]
        p["strict_required_status_checks_policy"] = False
        self.assertTrue(any("strict" in e for e in self.ecarts()))

    def test_branche_cible(self):
        self.reel["conditions"]["ref_name"]["include"] = ["refs/heads/autre"]
        self.assertTrue(any("main" in e for e in self.ecarts()))

    def test_secret_scanning_desactive(self):
        depot = copy.deepcopy(SECURITE_OK)
        depot["security_and_analysis"]["secret_scanning"]["status"] = "disabled"
        self.assertTrue(any("secret_scanning" in e for e in self.ecarts(depot)))

    def test_push_protection_desactivee(self):
        depot = copy.deepcopy(SECURITE_OK)
        depot["security_and_analysis"]["secret_scanning_push_protection"]["status"] = "disabled"
        self.assertTrue(any("push_protection" in e for e in self.ecarts(depot)))


class TestAppels(unittest.TestCase):
    def test_verifier_sans_ruleset(self):
        def appel(methode, chemin, corps=None):
            if chemin.endswith("/rulesets"):
                return []
            return SECURITE_OK

        self.assertTrue(any("absent" in e for e in rg.verifier("o/d", appel)))

    def test_appliquer_cree_puis_met_a_jour(self):
        journal = []

        def appel(methode, chemin, corps=None):
            journal.append((methode, chemin))
            if chemin.endswith("/rulesets") and methode == "GET":
                return [{"id": 7, "name": "protection-main"}] if len(journal) > 3 else []
            return {}

        rg.appliquer("o/d", appel)
        self.assertIn(("POST", "repos/o/d/rulesets"), journal)
        rg.appliquer("o/d", appel)
        self.assertIn(("PUT", "repos/o/d/rulesets/7"), journal)
        self.assertIn(("PATCH", "repos/o/d"), journal)


class TestCoherenceAvecLeWorkflow(unittest.TestCase):
    """Les contrôles requis sont exactement les tâches de controles.yml, sans condition if:."""

    def setUp(self):
        self.workflow = (RACINE / ".github/workflows/controles.yml").read_text(encoding="utf-8")
        p = regle(ATTENDU, "required_status_checks")["parameters"]["required_status_checks"]
        self.requis = {c["context"] for c in p}

    def taches(self):
        bloc = self.workflow.split("\njobs:\n", 1)[1]
        return re.findall(r"^  ([\w-]+):\n    name: ([\w-]+)", bloc, flags=re.M)

    def test_noms_identiques(self):
        taches = self.taches()
        self.assertTrue(all(ident == nom for ident, nom in taches))
        self.assertEqual({nom for _, nom in taches}, self.requis)

    def test_aucune_condition_sur_les_taches_requises(self):
        for ligne in self.workflow.splitlines():
            self.assertFalse(ligne.startswith("    if:"), ligne)

    def test_integration_github_actions(self):
        p = regle(ATTENDU, "required_status_checks")["parameters"]["required_status_checks"]
        self.assertTrue(all(c.get("integration_id") == 15368 for c in p))


if __name__ == "__main__":
    unittest.main()
