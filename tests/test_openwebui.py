"""Tests du client REST outils/atelier/openwebui.py contre un faux serveur local."""

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

from atelier import openwebui  # noqa: E402

JOURNAL = []


class FauxServeur(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def _repondre(self, code, corps):
        donnees = json.dumps(corps).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def do_GET(self):
        JOURNAL.append(("GET", self.path, self.headers.get("Authorization")))
        if self.path == "/health":
            self._repondre(200, {"status": True})
        elif self.path == "/api/v1/prompts/":
            self._repondre(200, [{"id": "p1", "command": "scenario-1"}])
        else:
            self._repondre(404, {"detail": "Introuvable"})

    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", 0))
        corps = json.loads(self.rfile.read(longueur) or b"{}")
        JOURNAL.append(("POST", self.path, self.headers.get("Authorization"), corps))
        if self.path == "/api/v1/auths/signin":
            if corps.get("password") == "bon":
                self._repondre(200, {"token": "jeton-test"})
            else:
                self._repondre(400, {"detail": "Identifiants incorrects"})
        else:
            self._repondre(200, {"ok": True})


class TestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serveur = ThreadingHTTPServer(("127.0.0.1", 0), FauxServeur)
        threading.Thread(target=cls.serveur.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.serveur.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()

    def setUp(self):
        JOURNAL.clear()

    def test_sante(self):
        openwebui.Client(self.base).attendre_sante(delai_max=5)

    def test_sante_injoignable(self):
        with self.assertRaises(openwebui.ErreurOpenWebUI):
            openwebui.Client("http://127.0.0.1:9").attendre_sante(delai_max=1, intervalle=0.2)

    def test_connexion_et_jeton(self):
        c = openwebui.Client(self.base)
        c.connexion("admin@exemple.atelier", "bon")
        c.get("/api/v1/prompts/")
        self.assertEqual(JOURNAL[-1][2], "Bearer jeton-test")

    def test_connexion_refusee(self):
        with self.assertRaises(openwebui.ErreurOpenWebUI) as ctx:
            openwebui.Client(self.base).connexion("admin@exemple.atelier", "mauvais")
        self.assertEqual(ctx.exception.code, 400)
        self.assertIn("Identifiants incorrects", str(ctx.exception))

    def test_erreur_http_lisible(self):
        with self.assertRaises(openwebui.ErreurOpenWebUI) as ctx:
            openwebui.Client(self.base).get("/api/v1/absent")
        self.assertEqual(ctx.exception.code, 404)

    def test_post_json(self):
        openwebui.Client(self.base, jeton="j").post("/api/v1/groups/create", {"name": "g"})
        self.assertEqual(JOURNAL[-1][3], {"name": "g"})


if __name__ == "__main__":
    unittest.main()
