"""Environnement local sur le poste du formateur (histoire 1, FR-001).

La clé Scaleway est lue à l'exécution (profil telemach) et transmise au seul processus
`docker compose` par son environnement : elle n'est jamais écrite sur disque. Les identifiants
formateur locaux vivent dans sessions/local/ (ignoré par Git), en mode 0600.
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

from atelier import openwebui, scw

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_LOCAL = RACINE / "sessions" / "local"
COMPOSE = RACINE / "openwebui" / "compose.yaml"
ADRESSE = "http://127.0.0.1:3000"
PROJET_COMPOSE = "atelier-ia"


def commande_compose(*arguments, profil=None):
    commande = ["docker", "compose", "-p", PROJET_COMPOSE, "-f", str(COMPOSE)]
    if profil:
        commande += ["--profile", profil]
    return commande + list(arguments)


def identifiants_locaux(dossier=DOSSIER_LOCAL):
    """Génère au premier appel, puis relit, le compte formateur et le secret de session locaux."""
    fichier = Path(dossier) / "identifiants.txt"
    if fichier.exists():
        champs = dict(
            ligne.split("=", 1)
            for ligne in fichier.read_text(encoding="utf-8").splitlines()
            if "=" in ligne
        )
        return {k: champs[k] for k in ("courriel", "mot_de_passe", "secret")}
    Path(dossier).mkdir(parents=True, exist_ok=True)
    os.chmod(dossier, 0o700)
    ident = {
        "courriel": "formateur@local.atelier",
        "mot_de_passe": secrets.token_urlsafe(18),
        "secret": secrets.token_urlsafe(32),
    }
    descripteur = os.open(fichier, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descripteur, "w", encoding="utf-8") as f:
        f.write("# Compte formateur de l'environnement LOCAL (ne pas versionner)\n")
        f.writelines(f"{k}={v}\n" for k, v in ident.items())
    return ident


def environnement(cle, projet, ident, base=None):
    env = dict(os.environ if base is None else base)
    env.update(
        {
            "OPENAI_API_BASE_URL": f"https://api.scaleway.ai/{projet}/v1",
            "OPENAI_API_KEY": cle,
            "WEBUI_SECRET_KEY": ident["secret"],
            "WEBUI_ADMIN_EMAIL": ident["courriel"],
            "WEBUI_ADMIN_PASSWORD": ident["mot_de_passe"],
            "WEBUI_URL": "http://localhost:3000",
        }
    )
    return env


def _compose(env, *arguments):
    resultat = subprocess.run(commande_compose(*arguments), env=env, check=False)  # noqa: S603
    if resultat.returncode != 0:
        raise openwebui.ErreurOpenWebUI(f"docker compose {' '.join(arguments)} a échoué")


def client_formateur():
    """Client connecté en formateur sur l'environnement local."""
    ident = identifiants_locaux()
    client = openwebui.Client(ADRESSE)
    client.connexion(ident["courriel"], ident["mot_de_passe"])
    return client


def demarrer(args):
    ident = identifiants_locaux()
    cle, projet = scw.cle_secrete(), scw.projet()
    print("Démarrage d'Open WebUI (premier lancement : téléchargement de l'image)...")
    _compose(environnement(cle, projet, ident), "up", "-d")
    client = openwebui.Client(ADRESSE)
    client.attendre_sante()
    client.connexion(ident["courriel"], ident["mot_de_passe"])
    print("Configuration (connexion Scaleway, modèles, filtre IFC, consignes)...")
    openwebui.configurer(client, f"https://api.scaleway.ai/{projet}/v1", cle)
    print(f"\nPrêt : {ADRESSE}")
    print(
        f"Compte formateur : {ident['courriel']} "
        "(mot de passe dans sessions/local/identifiants.txt)"
    )
    print(
        "Rappel : tout document déposé reste dans le volume Docker local jusqu'à "
        "`atelier local arreter --effacer`."
    )
    return 0


def arreter(args):
    # Valeurs factices : `down` n'a besoin que de l'interpolation de compose.yaml.
    ident = {"courriel": "x@local.atelier", "mot_de_passe": "x", "secret": "x"}
    env = environnement("x", "x", ident)
    _compose(env, "down", *(["--volumes"] if args.effacer else []))
    if args.effacer:
        print("Arrêté ; comptes, discussions et documents déposés supprimés (volume effacé).")
    else:
        print(
            "Arrêté. ATTENTION : les documents déposés restent dans le volume Docker local ; "
            "`atelier local arreter --effacer` les supprime.",
            file=sys.stderr,
        )
    return 0
