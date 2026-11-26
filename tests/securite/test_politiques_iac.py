"""Tests des politiques IaC maison (outils/securite/politiques_iac.py, research.md R2)."""

import importlib.util
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "politiques_iac", RACINE / "outils/securite/politiques_iac.py"
)
pol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pol)

EMP = "b" * 64

GS_OK = """
resource "scaleway_instance_security_group" "web" {
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"
  tags = ["atelier-session=demo"]
  inbound_rule {
    action = "accept"
    port   = 80
  }
  inbound_rule {
    action = "accept"
    port   = 443
  }
}
"""

CLE_OK = """
resource "scaleway_iam_api_key" "session" {
  application_id = scaleway_iam_application.session.id
  expires_at     = var.echeance
}
"""

POLITIQUE_OK = """
resource "scaleway_iam_policy" "session" {
  application_id = scaleway_iam_application.session.id
  tags = ["atelier-session=demo"]
  rule {
    project_ids          = [var.projet]
    permission_set_names = ["GenerativeApisModelAccess"]
  }
}
"""


class TestTerraform(unittest.TestCase):
    def test_groupe_de_securite_conforme(self):
        self.assertEqual(pol.verifier_terraform(GS_OK, "main.tf"), [])

    def test_port_22_refuse(self):
        texte = GS_OK.replace("port   = 443", "port   = 22")
        self.assertTrue(any("22" in m for m in pol.verifier_terraform(texte, "main.tf")))

    def test_port_hors_80_443_refuse(self):
        texte = GS_OK.replace("port   = 443", "port   = 8080")
        self.assertTrue(any("8080" in m for m in pol.verifier_terraform(texte, "main.tf")))

    def test_plage_de_ports_refusee(self):
        texte = GS_OK.replace("port   = 443", 'port_range = "1-65535"')
        self.assertTrue(any("plage" in m for m in pol.verifier_terraform(texte, "main.tf")))

    def test_politique_entree_par_defaut_drop(self):
        texte = GS_OK.replace(
            'inbound_default_policy  = "drop"', 'inbound_default_policy  = "accept"'
        )
        self.assertTrue(any("drop" in m for m in pol.verifier_terraform(texte, "main.tf")))

    def test_etiquette_session_obligatoire(self):
        texte = GS_OK.replace('  tags = ["atelier-session=demo"]\n', "")
        self.assertTrue(
            any("atelier-session" in m for m in pol.verifier_terraform(texte, "main.tf"))
        )

    def test_cle_api_avec_expiration(self):
        self.assertEqual(pol.verifier_terraform(CLE_OK, "main.tf"), [])
        texte = CLE_OK.replace("  expires_at     = var.echeance\n", "")
        self.assertTrue(any("expires_at" in m for m in pol.verifier_terraform(texte, "main.tf")))

    def test_politique_iam_limitee(self):
        self.assertEqual(pol.verifier_terraform(POLITIQUE_OK, "main.tf"), [])
        texte = POLITIQUE_OK.replace(
            '"GenerativeApisModelAccess"', '"GenerativeApisModelAccess", "InstancesFullAccess"'
        )
        self.assertTrue(
            any("InstancesFullAccess" in m for m in pol.verifier_terraform(texte, "main.tf"))
        )

    def test_ressource_sans_etiquette_possible_ignoree(self):
        texte = 'resource "scaleway_domain_record" "a" {\n  name = "x"\n}\n'
        self.assertEqual(pol.verifier_terraform(texte, "main.tf"), [])


COMPOSE_OK = f"""
services:
  openwebui:
    image: ghcr.io/open-webui/open-webui:v0.13.5@sha256:{EMP}
    ports:
      - "127.0.0.1:3000:8080"
  caddy:
    image: caddy:2.11.9@sha256:{EMP}
    ports:
      - "80:80"
      - "443:443"
    profiles: ["session"]
"""


class TestCompose(unittest.TestCase):
    def test_compose_conforme(self):
        self.assertEqual(pol.verifier_compose(COMPOSE_OK, "compose.yaml"), [])

    def test_image_sans_empreinte(self):
        texte = COMPOSE_OK.replace(
            f'@sha256:{EMP}\n    ports:\n      - "127', '\n    ports:\n      - "127', 1
        )
        self.assertTrue(any("empreinte" in m for m in pol.verifier_compose(texte, "compose.yaml")))

    def test_privileged_refuse(self):
        texte = COMPOSE_OK.replace(
            '    ports:\n      - "127', '    privileged: true\n    ports:\n      - "127'
        )
        self.assertTrue(any("privileged" in m for m in pol.verifier_compose(texte, "compose.yaml")))

    def test_openwebui_expose_hors_localhost(self):
        texte = COMPOSE_OK.replace('"127.0.0.1:3000:8080"', '"3000:8080"')
        self.assertTrue(any("127.0.0.1" in m for m in pol.verifier_compose(texte, "compose.yaml")))


class TestCloudInit(unittest.TestCase):
    def test_image_epinglee(self):
        texte = f"runcmd:\n  - docker pull caddy:2.11.9@sha256:{EMP}\n"
        self.assertEqual(pol.verifier_cloud_init(texte, "cloud-init.yaml.tftpl"), [])

    def test_image_non_epinglee(self):
        texte = "runcmd:\n  - docker pull caddy:2.11.9\n"
        self.assertTrue(pol.verifier_cloud_init(texte, "cloud-init.yaml.tftpl"))


@unittest.skipUnless(
    (RACINE / "infra").exists() or (RACINE / "openwebui").exists(),
    "pas encore d'infrastructure ni de Compose dans le dépôt (fonctionnalité 001)",
)
class TestFichiersDuDepot(unittest.TestCase):
    def test_depot_conforme(self):
        self.assertEqual(pol.verifier(RACINE), [])


if __name__ == "__main__":
    unittest.main()
