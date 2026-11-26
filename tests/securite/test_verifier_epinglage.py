"""Tests de outils/securite/verifier_epinglage.py (FR-010, FR-015, analyse D1)."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "verifier_epinglage", RACINE / "outils/securite/verifier_epinglage.py"
)
ve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ve)

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
EMP = "a" * 64
LOCK_OK = f"ruff=ghcr.io/astral-sh/ruff:0.17.6@sha256:{EMP}\n"


def depot(workflow="", lock=LOCK_OK, scripts=None, requis=("lint",)):
    """Crée un dépôt fictif minimal et renvoie son chemin."""
    d = Path(tempfile.mkdtemp())
    (d / ".github/workflows").mkdir(parents=True)
    (d / ".github/rulesets").mkdir(parents=True)
    (d / "securite").mkdir()
    (d / "outils/securite").mkdir(parents=True)
    (d / ".github/workflows/controles.yml").write_text(workflow)
    (d / "securite/outils.lock").write_text(lock)
    regles = {
        "rules": [
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [
                        {"context": c, "integration_id": 15368} for c in requis
                    ]
                },
            }
        ]
    }
    (d / ".github/rulesets/main.json").write_text(json.dumps(regles))
    for nom, contenu in (scripts or {}).items():
        (d / "outils/securite" / nom).write_text(contenu)
    return d


def wf(etapes, job_if=""):
    return (
        f"on: pull_request\njobs:\n  lint:\n{job_if}    runs-on: ubuntu-24.04\n    steps:\n{etapes}"
    )


class TestEpinglageActions(unittest.TestCase):
    def test_sha_avec_commentaire_accepte(self):
        d = depot(wf(f"      - uses: actions/checkout@{SHA} # v7.0.1\n"))
        self.assertEqual(ve.verifier(d), [])

    def test_tag_refuse(self):
        d = depot(wf("      - uses: actions/checkout@v7\n"))
        self.assertTrue(any("épinglée" in m for m in ve.verifier(d)))

    def test_sha_sans_commentaire_refuse(self):
        d = depot(wf(f"      - uses: actions/checkout@{SHA}\n"))
        self.assertTrue(any("commentaire" in m for m in ve.verifier(d)))

    def test_sous_action_sha_acceptee(self):
        d = depot(wf(f"      - uses: github/codeql-action/init@{SHA} # v4.39.5\n"))
        self.assertEqual(ve.verifier(d), [])

    def test_action_locale_acceptee(self):
        d = depot(wf("      - uses: ./.github/actions/locale\n"))
        self.assertEqual(ve.verifier(d), [])


class TestImages(unittest.TestCase):
    def test_docker_run_hors_lib_refuse(self):
        d = depot(wf("      - run: docker run --rm alpine:3 true\n"))
        self.assertTrue(any("docker run" in m for m in ve.verifier(d)))

    def test_docker_run_dans_script_refuse(self):
        d = depot(wf(""), scripts={"autre.sh": "docker run --rm alpine:3 true\n"})
        self.assertTrue(any("docker run" in m for m in ve.verifier(d)))

    def test_docker_run_dans_lib_accepte(self):
        d = depot(wf(""), scripts={"lib.sh": 'docker run --rm "$image"\n'})
        self.assertEqual(ve.verifier(d), [])

    def test_image_conteneur_hors_lock_refusee(self):
        d = depot(
            wf("      - run: true\n").replace("    runs-on", "    container: alpine:3\n    runs-on")
        )
        self.assertTrue(any("outils.lock" in m for m in ve.verifier(d)))

    def test_ligne_lock_sans_empreinte_refusee(self):
        d = depot(wf(""), lock="ruff=ghcr.io/astral-sh/ruff:0.17.6\n")
        self.assertTrue(any("empreinte" in m for m in ve.verifier(d)))

    def test_ligne_lock_latest_refusee(self):
        d = depot(wf(""), lock=f"ruff=ghcr.io/astral-sh/ruff:latest@sha256:{EMP}\n")
        self.assertTrue(any("latest" in m for m in ve.verifier(d)))

    def test_ligne_lock_binaire_acceptee(self):
        d = depot(wf(""), lock=f"opentofu=https://exemple.org/tofu_1.13.10.zip#sha256={EMP}\n")
        self.assertEqual(ve.verifier(d), [])


class TestConditionsTachesRequises(unittest.TestCase):
    def test_if_sur_tache_requise_refuse(self):
        d = depot(wf("      - run: true\n", job_if="    if: github.actor == 'x'\n"))
        self.assertTrue(any("if:" in m for m in ve.verifier(d)))

    def test_if_sur_etape_accepte(self):
        d = depot(wf("      - if: always()\n        run: true\n"))
        self.assertEqual(ve.verifier(d), [])

    def test_if_sur_tache_non_requise_accepte(self):
        d = depot(wf("      - run: true\n", job_if="    if: always()\n"), requis=("autre",))
        self.assertEqual(ve.verifier(d), [])


if __name__ == "__main__":
    unittest.main()
