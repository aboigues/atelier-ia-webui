"""Client REST minimal d'Open WebUI et configuration idempotente.

Routes et formulaires vérifiés dans le code d'Open WebUI v0.13.5 (research.md R13) ; ordre des
appels : contracts/configuration-openwebui.md.
"""

import json
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_OWUI = RACINE / "openwebui"


# Lecture pour tous les comptes connectés (et non « anyone », qui vaudrait sans connexion).
TOUS_LES_COMPTES = [{"principal_type": "user", "principal_id": "*", "permission": "read"}]


class ErreurOpenWebUI(RuntimeError):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class Client:
    def __init__(self, base, jeton=None, delai=180, cookie=None):
        self.base = base.rstrip("/")
        self.jeton = jeton
        self.delai = delai
        # Cookie d'accès posé par Caddy en session hébergée (lien d'accès secret).
        self.cookie = cookie

    def requete(self, methode, chemin, corps=None, brut=None, entetes=None):
        donnees = brut if brut is not None else (json.dumps(corps).encode() if corps is not None else None)
        en_tetes = {"Accept": "application/json"}
        if corps is not None:
            en_tetes["Content-Type"] = "application/json"
        if self.jeton:
            en_tetes["Authorization"] = f"Bearer {self.jeton}"
        if self.cookie:
            en_tetes["Cookie"] = self.cookie
        en_tetes.update(entetes or {})
        req = urllib.request.Request(self.base + chemin, data=donnees, headers=en_tetes, method=methode)
        try:
            with urllib.request.urlopen(req, timeout=self.delai) as reponse:  # noqa: S310
                texte = reponse.read().decode("utf-8")
        except urllib.error.HTTPError as erreur:
            detail = erreur.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise ErreurOpenWebUI(f"{methode} {chemin} : HTTP {erreur.code} : {detail}", erreur.code) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as erreur:
            raise ErreurOpenWebUI(f"{methode} {chemin} : injoignable ({erreur})") from None
        return json.loads(texte) if texte.strip() else None

    def get(self, chemin):
        return self.requete("GET", chemin)

    def post(self, chemin, corps=None):
        return self.requete("POST", chemin, corps if corps is not None else {})

    def delete(self, chemin):
        return self.requete("DELETE", chemin)

    def attendre_sante(self, delai_max=300, intervalle=3):
        fin = time.monotonic() + delai_max
        derniere = None
        while time.monotonic() < fin:
            try:
                if (self.get("/health") or {}).get("status"):
                    return
            except ErreurOpenWebUI as erreur:
                derniere = erreur
            time.sleep(intervalle)
        raise ErreurOpenWebUI(f"Open WebUI ne répond pas après {delai_max} s ({derniere})")

    def connexion(self, courriel, mot_de_passe, tentatives=6):
        """Connexion ; Open WebUI limite les connexions par minute : attente croissante sur 429."""
        for essai in range(tentatives):
            try:
                reponse = self.post("/api/v1/auths/signin", {"email": courriel, "password": mot_de_passe})
                break
            except ErreurOpenWebUI as erreur:
                if erreur.code != 429 or essai == tentatives - 1:
                    raise
                time.sleep(5 * 2**essai)
        self.jeton = reponse["token"]
        return self.jeton


# --- Configuration idempotente (contracts/configuration-openwebui.md) -----------------------


def configurer_connexion(client, url_api, cle, modeles):
    """Appel 1 : une seule connexion, Scaleway, limitée aux modèles listés."""
    client.post(
        "/openai/config/update",
        {
            "ENABLE_OPENAI_API": True,
            "OPENAI_API_BASE_URLS": [url_api],
            "OPENAI_API_KEYS": [cle],
            "OPENAI_API_CONFIGS": {"0": {"enable": True, "model_ids": sorted(modeles)}},
        },
    )


def assurer_fonction(client, ident, nom, contenu, description=""):
    """Appel 2 : crée ou met à jour une fonction, puis l'active."""
    formulaire = {"id": ident, "name": nom, "content": contenu, "meta": {"description": description}}
    try:
        existante = client.get(f"/api/v1/functions/id/{ident}")
    except ErreurOpenWebUI as erreur:
        if erreur.code not in (401, 404):
            raise
        existante = None
    if existante:
        client.post(f"/api/v1/functions/id/{ident}/update", formulaire)
    else:
        client.post("/api/v1/functions/create", formulaire)
        existante = client.get(f"/api/v1/functions/id/{ident}")
    if not (existante or {}).get("is_active"):
        client.post(f"/api/v1/functions/id/{ident}/toggle")


def assurer_modele(client, formulaire):
    """Appels 3 et 4 : crée ou met à jour un modèle personnalisé (identifiant dans le formulaire)."""
    try:
        existe = client.get(f"/api/v1/models/model?id={formulaire['id']}") is not None
    except ErreurOpenWebUI as erreur:
        if erreur.code not in (401, 404):
            raise
        existe = False
    if existe:
        client.post("/api/v1/models/model/update", formulaire)
    else:
        client.post("/api/v1/models/create", formulaire)
    # Les droits s'enregistrent par une route dédiée (le formulaire du modèle les ignore).
    client.post(
        "/api/v1/models/model/access/update",
        {"id": formulaire["id"], "access_grants": formulaire.get("access_grants") or []},
    )


def formulaires_modeles(filtres=(), droits=None):
    """Modèles personnalisés décrits par openwebui/modele-assistant.toml."""
    config = tomllib.loads((DOSSIER_OWUI / "modele-assistant.toml").read_text(encoding="utf-8"))
    formulaires = []
    for m in config["modele"]:
        formulaires.append(
            {
                "id": m["id"],
                "base_model_id": m["base"],
                "name": m["nom"],
                "meta": {
                    "description": m.get("description", ""),
                    "capabilities": {"vision": True, "file_upload": True, "citations": True},
                    "filterIds": list(filtres),
                },
                "params": {"system": config["invite_systeme"], "temperature": m.get("temperature", 0.1)},
                "access_grants": droits or [],
                "is_active": True,
            }
        )
    return formulaires


def lire_consignes():
    """Consignes de départ : en-tête « commande: », « titre: », puis le contenu."""
    consignes = []
    for f in sorted((DOSSIER_OWUI / "consignes").glob("*.md")):
        entete, _, contenu = f.read_text(encoding="utf-8").partition("\n---\n")
        champs = dict(
            ligne.split(":", 1) for ligne in entete.strip().splitlines() if ":" in ligne
        )
        consignes.append(
            {
                "command": champs["commande"].strip(),
                "name": champs["titre"].strip(),
                "content": contenu.strip(),
            }
        )
    return consignes


def assurer_consigne(client, consigne, droits=None):
    """Appel 7 : crée ou met à jour une consigne (par commande)."""
    existantes = {p["command"].lstrip("/"): p for p in client.get("/api/v1/prompts/") or []}
    formulaire = dict(consigne, access_grants=droits or [])
    actuelle = existantes.get(consigne["command"].lstrip("/"))
    if actuelle:
        ident = actuelle["id"]
        client.post(f"/api/v1/prompts/id/{ident}/update", formulaire)
    else:
        ident = client.post("/api/v1/prompts/create", formulaire)["id"]
    client.post(f"/api/v1/prompts/id/{ident}/access/update", {"access_grants": droits or []})


def assurer_groupe(client, nom, description):
    """Appel 5 : crée le groupe s'il n'existe pas ; renvoie son identifiant."""
    for g in client.get("/api/v1/groups/") or []:
        if g["name"] == nom:
            return g["id"]
    permissions = {
        "workspace": {"prompts": True, "models": False, "knowledge": False, "tools": False},
        # Consignes partageables au groupe, jamais publiquement (data-model.md Consigne.auteur).
        "sharing": {"prompts": True, "public_prompts": False, "public_models": False},
        "chat": {"stt": False, "tts": False, "call": False},
    }
    return client.post(
        "/api/v1/groups/create", {"name": nom, "description": description, "permissions": permissions}
    )["id"]


def assurer_utilisateur(client, nom, courriel, mot_de_passe, role="user"):
    """Appel 6 : crée le compte s'il n'existe pas (idempotent par courriel) ; renvoie son id."""
    try:
        return client.post(
            "/api/v1/auths/add",
            {"name": nom, "email": courriel, "password": mot_de_passe, "role": role},
        )["id"]
    except ErreurOpenWebUI as erreur:
        if erreur.code != 400:
            raise
    for u in (client.get(f"/api/v1/users/search?query={courriel}") or {}).get("users", []):
        if u.get("email") == courriel:
            return u["id"]
    raise ErreurOpenWebUI(f"compte {courriel} ni créé ni retrouvé")


def configurer(client, url_api, cle, droits_groupe=None):
    """Configuration complète et idempotente (contracts/configuration-openwebui.md).

    droits_groupe : accès en lecture accordé à un groupe (session hébergée), None en local.
    """
    config = tomllib.loads((DOSSIER_OWUI / "modele-assistant.toml").read_text(encoding="utf-8"))
    modeles = {m["base"] for m in config["modele"]}
    configurer_connexion(client, url_api, cle, modeles)  # appel 1
    filtres = []
    filtre = DOSSIER_OWUI / "fonctions" / "filtre_ifc.py"
    if filtre.exists():  # appel 2 (histoire 2)
        assurer_fonction(
            client,
            "filtre_ifc",
            "Conversion IFC",
            filtre.read_text(encoding="utf-8"),
            "Réduit une maquette IFC à un tableau des espaces ; avertit sur les PDF vectoriels.",
        )
        filtres.append("filtre_ifc")
    # Modèles de base : lisibles par tous les comptes (sinon un participant ne peut pas utiliser
    # un assistant construit dessus), mais masqués du sélecteur.
    for base in sorted(modeles):
        assurer_modele(
            client,
            {
                "id": base,
                "base_model_id": None,
                "name": base,
                "meta": {"hidden": True, "description": "Modèle de base Scaleway (masqué)."},
                "params": {},
                "access_grants": TOUS_LES_COMPTES,
                "is_active": True,
            },
        )
    # Assistants utilisables par tous les comptes (tous créés par le formateur).
    for formulaire in formulaires_modeles(filtres, TOUS_LES_COMPTES):  # appels 3 et 4
        assurer_modele(client, formulaire)
    # Consignes : groupe des participants en session, tous les comptes en local.
    for consigne in lire_consignes():  # appel 7
        assurer_consigne(client, consigne, droits_groupe or TOUS_LES_COMPTES)
