"""Tests de openwebui/fonctions/filtre_ifc.py (contracts/filtre-ifc.md, data-model.md
« Tableau des espaces IFC »)."""

import asyncio
import importlib.util
import tempfile
import time
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("filtre_ifc", RACINE / "openwebui/fonctions/filtre_ifc.py")
fi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fi)

MAQUETTE = (RACINE / "exemples/bloc-operatoire/maquette-bloc.ifc").read_text(encoding="utf-8")


def ifc(entites, schema="IFC4"):
    return (
        "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION((''),'2;1');\n"
        f"FILE_SCHEMA(('{schema}'));\nENDSEC;\nDATA;\n" + "\n".join(entites) + "\nENDSEC;\nEND-ISO-10303-21;\n"
    )


ESPACE = [
    "#1=IFCSPACE('g1',$,'B02','Bloc',$,$,$,'Salle d''op\\X2\\00E9\\X0\\ration',.ELEMENT.,.INTERNAL.,$);",
    "#2=IFCPROPERTYSINGLEVALUE('PlafondSoufflant',$,IFCBOOLEAN(.F.),$);",
    "#3=IFCPROPERTYSINGLEVALUE('SurpressionPa',$,IFCREAL(15.),$);",
    "#4=IFCPROPERTYSET('p1',$,'Pset',$,(#2,#3));",
    "#5=IFCRELDEFINESBYPROPERTIES('r1',$,$,$,(#1),#4);",
]


class TestEspaces(unittest.TestCase):
    def test_maquette_du_jeu_fictif(self):
        espaces = {e["code"]: e for e in fi.espaces_ifc(MAQUETTE)}
        salles = sorted(c for c in espaces if c.startswith("SO"))
        self.assertEqual(salles, ["SO1", "SO2", "SO3", "SO4"])
        self.assertEqual(espaces["SO2"]["PlafondSoufflant"], "non")
        self.assertEqual(espaces["SO1"]["PlafondSoufflant"], "oui")
        self.assertEqual(espaces["SO4"]["SurpressionPa"], "10")
        self.assertEqual(espaces["SO1"]["nom"], "Salle d'opération 1")

    def test_tri_par_code(self):
        codes = [e["code"] for e in fi.espaces_ifc(MAQUETTE)]
        self.assertEqual(codes, sorted(codes))

    def test_entites_sur_plusieurs_lignes_et_decodage(self):
        multi = [ESPACE[0].replace(",'B02',", ",\n'B02',\n")] + ESPACE[1:]
        e = fi.espaces_ifc(ifc(multi))[0]
        self.assertEqual(e["code"], "B02")
        self.assertEqual(e["nom"], "Salle d'opération")
        self.assertEqual(e["PlafondSoufflant"], "non")
        self.assertEqual(e["SurpressionPa"], "15")

    def test_ifc2x3(self):
        self.assertEqual(len(fi.espaces_ifc(ifc(ESPACE, "IFC2X3"))), 1)

    def test_propriete_absente_vide(self):
        entites = ESPACE + ["#6=IFCSPACE('g2',$,'B01','Couloir',$,$,$,$,.ELEMENT.,.INTERNAL.,$);"]
        tableau = fi.tableau_markdown(fi.espaces_ifc(ifc(entites)))
        ligne_b01 = next(l for l in tableau.splitlines() if l.startswith("| B01"))
        self.assertIn("|  |", ligne_b01)

    def test_fichier_tronque(self):
        with self.assertRaises(fi.ErreurIFC):
            fi.espaces_ifc(MAQUETTE[: len(MAQUETTE) // 2])

    def test_pas_un_ifc(self):
        with self.assertRaises(fi.ErreurIFC):
            fi.espaces_ifc("bonjour")

    def test_trop_d_espaces(self):
        entites = [
            f"#{i}=IFCSPACE('g{i}',$,'S{i}','N',$,$,$,$,.ELEMENT.,.INTERNAL.,$);" for i in range(1, 2003)
        ]
        with self.assertRaises(fi.ErreurIFC) as ctx:
            fi.espaces_ifc(ifc(entites), espaces_max=2000)
        self.assertIn("2002", str(ctx.exception))

    def test_maquette_volumineuse(self):
        """Une maquette de plusieurs dizaines de Mo est convertie en un temps raisonnable (AS 2.3)."""
        remplissage = [f"#{100000 + i}=IFCCARTESIANPOINT(({i}.,{i}.,0.));" for i in range(1_200_000)]
        espaces = [
            f"#{i}=IFCSPACE('g{i}',$,'S{i:04d}','Local {i}',$,$,$,$,.ELEMENT.,.INTERNAL.,$);"
            for i in range(1, 1501)
        ]
        texte = ifc(espaces + remplissage)
        self.assertGreater(len(texte), 40_000_000)
        debut = time.monotonic()
        self.assertEqual(len(fi.espaces_ifc(texte)), 1500)
        self.assertLess(time.monotonic() - debut, 60)


class TestTableau(unittest.TestCase):
    def test_colonnes(self):
        tableau = fi.tableau_markdown(fi.espaces_ifc(MAQUETTE))
        entete = tableau.splitlines()[0]
        self.assertTrue(entete.startswith("| code | nom |"))
        self.assertIn("PlafondSoufflant", entete)


class TestPdf(unittest.TestCase):
    def test_pdf_pauvre(self):
        self.assertTrue(fi.pdf_texte_pauvre("E01 E02 P1", pages=1))
        self.assertFalse(fi.pdf_texte_pauvre("x" * 500, pages=2))


class TestInlet(unittest.TestCase):
    def test_ifc_remplace_par_le_tableau_et_retire(self):
        dossier = Path(tempfile.mkdtemp())
        (dossier / "m.ifc").write_text(MAQUETTE, encoding="utf-8")
        filtre = fi.Filter()
        evenements = []

        async def emetteur(e):
            evenements.append(e)

        async def lire(ident):
            return dossier / "m.ifc", ""

        filtre._fichier = lire
        body = {
            "messages": [{"role": "user", "content": "Quelles salles ?"}],
            "files": [{"type": "file", "id": "f1", "name": "maquette-bloc.ifc"}],
        }
        resultat = asyncio.run(filtre.inlet(body, __event_emitter__=emetteur))
        self.assertEqual(resultat["files"], [])
        self.assertIn("SO2", resultat["messages"][-1]["content"])
        self.assertTrue(any(e["type"] == "citation" for e in evenements))

    def test_ifc_illisible_retire_avec_message(self):
        dossier = Path(tempfile.mkdtemp())
        (dossier / "m.ifc").write_text("tronqué", encoding="utf-8")
        filtre = fi.Filter()
        evenements = []

        async def emetteur(e):
            evenements.append(e)

        async def lire(ident):
            return dossier / "m.ifc", ""

        filtre._fichier = lire
        body = {"messages": [{"role": "user", "content": "?"}], "files": [{"id": "f1", "name": "x.ifc"}]}
        resultat = asyncio.run(filtre.inlet(body, __event_emitter__=emetteur))
        self.assertEqual(resultat["files"], [])
        self.assertTrue(any("Conversion IFC impossible" in str(e) for e in evenements))


if __name__ == "__main__":
    unittest.main()
