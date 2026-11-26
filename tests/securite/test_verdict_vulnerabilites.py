"""Tests de outils/securite/verdict_vulnerabilites.py (FR-007, research.md R3,
contracts/exceptions.md, data-model.md Vulnérabilité constatée)."""

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
vv = _charger("verdict_vulnerabilites", "outils/securite/verdict_vulnerabilites.py")

JOUR = dt.date(2026, 12, 1)
IMAGE = "registry:ghcr.io/open-webui/open-webui:v0.13.5@sha256:" + "c" * 64


def correspondance(vid, gravite, etat_correctif, paquet="openssl", liees=()):
    return {
        "vulnerability": {
            "id": vid,
            "severity": gravite,
            "fix": {
                "versions": ["9.9"] if etat_correctif == "fixed" else [],
                "state": etat_correctif,
            },
        },
        "relatedVulnerabilities": [{"id": i} for i in liees],
        "artifact": {"name": paquet, "version": "1.0"},
    }


def rapport_grype(*correspondances, image=IMAGE):
    f = Path(tempfile.mkdtemp()) / "grype.json"
    f.write_text(
        json.dumps({"matches": list(correspondances), "source": {"target": {"userInput": image}}})
    )
    return f


def exc(
    id_,
    type_="vulnerabilite",
    portee="ghcr.io/open-webui/open-webui",
    acceptee=dt.date(2026, 11, 26),
    reexamen=dt.date(2027, 1, 15),
):
    return ex.ExceptionSecurite(
        id_,
        type_,
        portee,
        "Raison détaillée de plus de vingt caractères.",
        "Alexandre",
        acceptee,
        reexamen,
    )


CLASSE = exc("elevee-sans-correctif", "classe", "*")


def juger(fichier, exceptions):
    return vv.juger([fichier], exceptions, JOUR)


class TestRegles(unittest.TestCase):
    def test_elevee_avec_correctif_bloque(self):
        v = juger(rapport_grype(correspondance("CVE-1", "High", "fixed")), [CLASSE])
        self.assertEqual([c.id for c in v.bloquantes], ["CVE-1"])

    def test_critique_avec_correctif_bloque(self):
        v = juger(rapport_grype(correspondance("CVE-2", "Critical", "fixed")), [CLASSE])
        self.assertEqual(len(v.bloquantes), 1)

    def test_critique_sans_correctif_bloque_malgre_la_classe(self):
        v = juger(rapport_grype(correspondance("CVE-3", "Critical", "not-fixed")), [CLASSE])
        self.assertEqual(len(v.bloquantes), 1)

    def test_elevee_sans_correctif_toleree_par_la_classe(self):
        v = juger(rapport_grype(correspondance("CVE-4", "High", "not-fixed")), [CLASSE])
        self.assertEqual(v.bloquantes, [])
        self.assertEqual([c.id for c in v.tolerees], ["CVE-4"])

    def test_elevee_sans_correctif_bloque_sans_la_classe(self):
        v = juger(rapport_grype(correspondance("CVE-4", "High", "wont-fix")), [])
        self.assertEqual(len(v.bloquantes), 1)

    def test_elevee_sans_correctif_bloque_si_classe_echue(self):
        echue = exc(
            "elevee-sans-correctif", "classe", "*", dt.date(2026, 8, 1), dt.date(2026, 10, 1)
        )
        v = juger(rapport_grype(correspondance("CVE-4", "High", "not-fixed")), [echue])
        self.assertEqual(len(v.bloquantes), 1)
        self.assertTrue(any("échue" in a for a in v.avertissements))

    def test_moyenne_et_inconnue_signalees(self):
        v = juger(
            rapport_grype(
                correspondance("CVE-5", "Medium", "fixed"),
                correspondance("CVE-6", "Unknown", "not-fixed"),
                correspondance("CVE-7", "Negligible", "fixed"),
            ),
            [],
        )
        self.assertEqual(v.bloquantes, [])
        self.assertEqual(len(v.signalees), 3)


class TestExceptionsIndividuelles(unittest.TestCase):
    def test_exception_valide_tolere(self):
        v = juger(rapport_grype(correspondance("CVE-8", "Critical", "fixed")), [exc("CVE-8")])
        self.assertEqual(v.bloquantes, [])
        self.assertEqual(len(v.tolerees), 1)

    def test_exception_par_identifiant_lie(self):
        v = juger(
            rapport_grype(correspondance("GHSA-xxxx", "High", "fixed", liees=("CVE-9",))),
            [exc("CVE-9")],
        )
        self.assertEqual(v.bloquantes, [])

    def test_exception_autre_image_ignoree(self):
        v = juger(
            rapport_grype(correspondance("CVE-8", "Critical", "fixed")),
            [exc("CVE-8", portee="caddy")],
        )
        self.assertEqual(len(v.bloquantes), 1)

    def test_exception_echue_ignoree(self):
        echue = exc("CVE-8", acceptee=dt.date(2026, 8, 1), reexamen=dt.date(2026, 10, 1))
        v = juger(rapport_grype(correspondance("CVE-8", "Critical", "fixed")), [echue])
        self.assertEqual(len(v.bloquantes), 1)


class TestRobustesse(unittest.TestCase):
    def test_json_illisible(self):
        f = Path(tempfile.mkdtemp()) / "grype.json"
        f.write_text("{pas du json")
        with self.assertRaises(vv.ErreurAnalyse):
            vv.juger([f], [], JOUR)

    def test_fichier_vide(self):
        f = Path(tempfile.mkdtemp()) / "grype.json"
        f.write_text("")
        with self.assertRaises(vv.ErreurAnalyse):
            vv.juger([f], [], JOUR)

    def test_sans_cle_matches(self):
        f = Path(tempfile.mkdtemp()) / "grype.json"
        f.write_text("{}")
        with self.assertRaises(vv.ErreurAnalyse):
            vv.juger([f], [], JOUR)

    def test_rapport_markdown(self):
        v = juger(
            rapport_grype(
                correspondance("CVE-1", "High", "fixed"),
                correspondance("CVE-4", "High", "not-fixed"),
            ),
            [CLASSE],
        )
        texte = vv.rapport(v)
        self.assertIn("Bloquantes", texte)
        self.assertIn("CVE-1", texte)
        self.assertIn("Tolérées", texte)


class TestDepotImage(unittest.TestCase):
    def test_reduction_au_depot(self):
        self.assertEqual(vv.depot_image(IMAGE), "ghcr.io/open-webui/open-webui")
        self.assertEqual(vv.depot_image("caddy:2.11.9@sha256:" + "d" * 64), "caddy")
        self.assertEqual(vv.depot_image("localhost:5000/x/y:1"), "localhost:5000/x/y")
        self.assertEqual(vv.depot_image("file:/sortie/bin/trivy"), "binaire:trivy")
        self.assertEqual(vv.depot_image("/sortie/bin/trivy"), "binaire:trivy")

    def test_source_fichier_cible_chaine(self):
        f = Path(tempfile.mkdtemp()) / "grype.json"
        f.write_text(
            json.dumps(
                {
                    "matches": [correspondance("GO-1", "High", "fixed")],
                    "source": {"type": "file", "target": "/sortie/bin/abc/trivy"},
                }
            )
        )
        v = juger(f, [])
        self.assertEqual(v.bloquantes[0].image, "binaire:trivy")

    def test_exception_sur_binaire(self):
        f = rapport_grype(
            correspondance("GO-2026-6865", "High", "fixed"), image="/sortie/bin/trivy"
        )
        v = juger(f, [exc("GO-2026-6865", portee="binaire:trivy")])
        self.assertEqual(v.bloquantes, [])


if __name__ == "__main__":
    unittest.main()
