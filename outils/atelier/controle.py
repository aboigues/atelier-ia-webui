"""Contrôle de bout en bout (FR-013 ; contracts/cli.md, « Contrôle de bout en bout »).

Étapes : santé ; connexion d'un compte ; inscription libre refusée ; appel du modèle ; plan en
image (scénario 1) ; maquette IFC (si le filtre est installé) ; isolement entre comptes ;
connexions sortantes (local seulement : relevé de /proc/net/tcp du conteneur). Les comptes de
contrôle sont supprimés à la fin, avec leurs discussions et fichiers.
"""

import base64
import concurrent.futures
import ipaddress
import re
import secrets
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path

from atelier import openwebui

RACINE = Path(__file__).resolve().parents[2]
EXEMPLES = RACINE / "exemples" / "bloc-operatoire"
MODELE = "assistant-bureau-etudes"
CONTENEUR_LOCAL = "atelier-ia-openwebui-1"
DESTINATIONS_AUTORISEES = ("api.scaleway.ai",)
SCENARIO_1 = (RACINE / "openwebui" / "consignes" / "scenario-1.md").read_text(encoding="utf-8")
SCENARIO_1 = SCENARIO_1.partition("\n---\n")[2].strip()


class Bilan:
    def __init__(self):
        self.lignes, self.echec = [], False

    def etape(self, nom, fonction, *args):
        debut = time.monotonic()
        try:
            detail = fonction(*args) or ""
            etat = "OK"
        except Exception as erreur:  # noqa: BLE001 (toute erreur d'étape est un échec affiché)
            detail, etat, self.echec = str(erreur), "ÉCHEC", True
        duree = time.monotonic() - debut
        self.lignes.append(f"{etat:6} {nom} ({duree:.0f} s){' : ' + detail if detail else ''}")
        print(self.lignes[-1], flush=True)
        return etat == "OK"


def _texte_reponse(reponse):
    return reponse["choices"][0]["message"]["content"]


def demander(client, contenu, fichiers=None):
    corps = {"model": MODELE, "stream": False, "messages": [{"role": "user", "content": contenu}]}
    if fichiers:
        corps["files"] = fichiers
    return _texte_reponse(client.post("/api/chat/completions", corps))


def deposer(client, chemin):
    """Dépôt d'un fichier (multipart/form-data) ; renvoie son identifiant."""
    limite = uuid.uuid4().hex
    corps = (
        (
            f"--{limite}\r\nContent-Disposition: form-data; "
            f'name="file"; filename="{chemin.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + chemin.read_bytes()
        + f"\r\n--{limite}--\r\n".encode()
    )
    reponse = client.requete(
        "POST",
        "/api/v1/files/?process=true",
        brut=corps,
        entetes={"Content-Type": f"multipart/form-data; boundary={limite}"},
    )
    return reponse["id"]


def image_png(chemin):
    return {
        "type": "image_url",
        "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(chemin.read_bytes()).decode()
        },
    }


def verifier_scenario_1(texte):
    reperes = {f"E{n:02d}" for n in range(1, 11)} & set(re.findall(r"\bE\d{2}\b", texte))
    portes = {f"P{n}" for n in range(1, 5)} & set(re.findall(r"\bP\d\b", texte))
    if len(reperes) < 8 or len(portes) < 4 or not re.search(r"\bB\b", texte):
        raise AssertionError(f"réponse incomplète : {len(reperes)} repères, {len(portes)} portes")
    return f"{len(reperes)} repères, {len(portes)} portes, indice B"


class Releve:
    """Relevé des connexions sortantes établies du conteneur local pendant les demandes."""

    def __init__(self, conteneur):
        self.conteneur, self.ips, self.actif = conteneur, set(), False

    def _lire(self):
        sortie = subprocess.run(  # noqa: S603 (commande fixe, sans shell)
            ["docker", "exec", self.conteneur, "cat", "/proc/net/tcp", "/proc/net/tcp6"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        for ligne in sortie.splitlines()[1:]:
            champs = ligne.split()
            if len(champs) > 3 and champs[3] == "01":  # ESTABLISHED
                hexa = champs[2].split(":")[0]
                brut = bytes.fromhex(hexa)
                if len(brut) == 4:
                    ip = ipaddress.IPv4Address(brut[::-1])
                else:
                    mots = [brut[i : i + 4][::-1] for i in range(0, 16, 4)]
                    ip = ipaddress.IPv6Address(b"".join(mots))
                    ip = ip.ipv4_mapped or ip
                if not (ip.is_loopback or ip.is_private or ip.is_unspecified):
                    self.ips.add(str(ip))

    def _boucle(self):
        while self.actif:
            self._lire()
            time.sleep(0.5)

    def __enter__(self):
        self.actif = True
        self.fil = threading.Thread(target=self._boucle, daemon=True)
        self.fil.start()
        return self

    def __exit__(self, *exc):
        self.actif = False
        self.fil.join(timeout=5)

    def verifier(self):
        autorisees = {
            info[4][0] for nom in DESTINATIONS_AUTORISEES for info in socket.getaddrinfo(nom, 443)
        }
        inconnues = self.ips - autorisees
        if inconnues:
            raise AssertionError(
                f"connexions vers des destinations non autorisées : {sorted(inconnues)}"
            )
        return f"{len(self.ips)} destination(s), toutes chez {', '.join(DESTINATIONS_AUTORISEES)}"


def controler(base, client_admin, domaine, conteneur=None, cookie=None, charge=0):
    """Déroule le contrôle ; renvoie 0 si tout est OK, 1 sinon."""
    bilan, comptes = Bilan(), []

    def nouveau_client():
        return openwebui.Client(base, cookie=cookie)

    def creer_compte(n):
        courriel = f"controle-{n}-{secrets.token_hex(3)}@{domaine}"
        mot_de_passe = secrets.token_urlsafe(18)
        ident = openwebui.assurer_utilisateur(client_admin, f"Contrôle {n}", courriel, mot_de_passe)
        comptes.append(ident)
        client = nouveau_client()
        client.connexion(courriel, mot_de_passe)
        # Comme l'interface web : la liste des modèles alimente le cache du serveur.
        client.get("/api/models")
        return client

    etat = {}
    bilan.etape("Santé du service", lambda: nouveau_client().attendre_sante(delai_max=60))

    def connexion():
        etat["c1"], etat["c2"] = creer_compte(1), creer_compte(2)
        return "deux comptes de contrôle connectés"

    if not bilan.etape("Connexion d'un compte participant", connexion):
        return _conclure(bilan, client_admin, comptes)

    def inscription_refusee():
        try:
            nouveau_client().post(
                "/api/v1/auths/signup",
                {
                    "name": "Intrus",
                    "email": f"intrus@{domaine}",
                    "password": secrets.token_urlsafe(12),
                },
            )
        except openwebui.ErreurOpenWebUI as erreur:
            return f"refusée (HTTP {erreur.code})"
        raise AssertionError("une inscription libre a été acceptée")

    bilan.etape("Inscription libre refusée", inscription_refusee)

    releve = Releve(conteneur) if conteneur else None
    if releve:
        releve.__enter__()
    try:
        bilan.etape(
            "Appel du modèle",
            lambda: f"{len(demander(etat['c1'], 'Réponds seulement : prêt.'))} caractères",
        )

        def plan():
            plan_png = EXEMPLES / "plan-salle3-indB.png"
            etat["fichier"] = deposer(etat["c1"], plan_png)
            return verifier_scenario_1(
                demander(etat["c1"], [{"type": "text", "text": SCENARIO_1}, image_png(plan_png)])
            )

        bilan.etape("Plan en image, scénario 1", plan)

        if (RACINE / "openwebui" / "fonctions" / "filtre_ifc.py").exists():

            def ifc():
                ident = deposer(etat["c1"], EXEMPLES / "maquette-bloc.ifc")
                texte = demander(
                    etat["c1"],
                    "Quelles salles d'opération n'ont pas de plafond soufflant ? "
                    "Y a-t-il d'autres valeurs qui détonnent entre les salles d'opération ?",
                    [{"type": "file", "id": ident, "name": "maquette-bloc.ifc"}],
                )
                if "SO2" not in texte or "SO4" not in texte:
                    raise AssertionError("la réponse ne cite pas SO2 et SO4")
                return "SO2 et SO4 cités"

            bilan.etape("Maquette IFC", ifc)
    finally:
        if releve:
            releve.__exit__()

    def isolement():
        if "fichier" not in etat:
            raise AssertionError("aucun fichier déposé à contrôler")
        try:
            etat["c2"].get(f"/api/v1/files/{etat['fichier']}")
        except openwebui.ErreurOpenWebUI as erreur:
            return f"fichier invisible pour un autre compte (HTTP {erreur.code})"
        raise AssertionError("un autre compte voit le fichier déposé")

    bilan.etape("Isolement entre comptes", isolement)

    if releve:
        bilan.etape("Connexions sortantes", releve.verifier)
    else:
        bilan.lignes.append(
            "SAUTÉ  Connexions sortantes : vérifiées en local (même image et configuration)"
        )
        print(bilan.lignes[-1])

    if charge:
        bilan.etape(f"Charge : {charge} scénarios 1 simultanés", _charge, creer_compte, charge)

    return _conclure(bilan, client_admin, comptes)


def _charge(creer_compte, n):
    clients = [creer_compte(10 + i) for i in range(n)]
    plan_png = EXEMPLES / "plan-salle3-indB.png"

    def un(client):
        debut = time.monotonic()
        demander(client, [{"type": "text", "text": SCENARIO_1}, image_png(plan_png)])
        return time.monotonic() - debut

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        durees = list(pool.map(un, clients))
    if max(durees) > 60:
        raise AssertionError(f"réponse la plus lente : {max(durees):.0f} s (limite 60 s)")
    return f"la plus lente en {max(durees):.0f} s, médiane {sorted(durees)[n // 2]:.0f} s"


def _conclure(bilan, client_admin, comptes):
    for ident in comptes:
        try:
            client_admin.delete(f"/api/v1/users/{ident}")
        except openwebui.ErreurOpenWebUI:
            print(f"ATTENTION : compte de contrôle {ident} non supprimé")
    print(
        f"\nContrôle {'en ÉCHEC' if bilan.echec else 'réussi'} "
        f"({len(comptes)} compte(s) de contrôle supprimé(s))."
    )
    return 1 if bilan.echec else 0


def controler_local(args):
    from atelier import local

    return controler(
        local.ADRESSE, local.client_formateur(), "local.atelier", conteneur=CONTENEUR_LOCAL
    )


def controler_session(args):
    from atelier import session

    return session.controler(args, controler)
