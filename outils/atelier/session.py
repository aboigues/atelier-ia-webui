"""Session hébergée chez Scaleway (histoires 3 et 4 ; contracts/cli.md).

Tout ce qui est propre à une session vit dans sessions/<id>/ (ignoré par Git, 0700) :
session.toml et participants.csv (écrits par le formateur), secrets.json et comptes.json
(générés une fois, 0600), identifiants/ (fiches), tofu/ (état OpenTofu, qui contient la clé IAM).
"""

import datetime as dt
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

from atelier import comptes, config, cout, openwebui, scw

RACINE = Path(__file__).resolve().parents[2]
INFRA = RACINE / "infra" / "scaleway"
EXPORTS = RACINE / "exports"


def dossier_session(session_id):
    dossier = RACINE / "sessions" / session_id
    if not (dossier / "session.toml").exists():
        raise config.ErreurConfig(
            f"{dossier}/session.toml absent : copier exemples/session/ dans sessions/{session_id}/"
        )
    os.chmod(dossier, 0o700)
    return dossier


def _ecrire_prive(chemin, contenu):
    descripteur = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descripteur, "w", encoding="utf-8") as f:
        f.write(contenu)


def secrets_session(dossier, session):
    """Secrets générés une fois puis relus (secret de session, jeton d'accès, formateur)."""
    fichier = dossier / "secrets.json"
    if fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))
    formateur = comptes.compte_formateur(session.id)
    valeurs = {
        "webui_secret_key": secrets.token_urlsafe(32),
        "acces_jeton": secrets.token_urlsafe(32),
        "formateur_courriel": formateur.courriel,
        "formateur_mot_de_passe": formateur.mot_de_passe,
    }
    _ecrire_prive(fichier, json.dumps(valeurs, indent=1))
    return valeurs


def comptes_session(dossier, session):
    """Comptes des participants, générés une fois (mots de passe stables entre deux relances)."""
    fichier = dossier / "comptes.json"
    if fichier.exists():
        return [comptes.Compte(**c) for c in json.loads(fichier.read_text(encoding="utf-8"))]
    liste = comptes.generer(config.lire_participants(dossier), session.id)
    _ecrire_prive(fichier, json.dumps([c.__dict__ for c in liste], ensure_ascii=False, indent=1))
    return liste


# --- OpenTofu ------------------------------------------------------------------------------


def environnement_tofu(dossier, session, valeurs):
    env = dict(os.environ)
    env.update(
        {
            "SCW_ACCESS_KEY": scw._scw("config", "get", "access-key", json_attendu=False),
            "SCW_SECRET_KEY": scw.cle_secrete(),
            "SCW_DEFAULT_PROJECT_ID": scw.projet(),
            "SCW_DEFAULT_ORGANIZATION_ID": scw._scw(
                "config", "get", "default-organization-id", json_attendu=False
            ),
            "TF_DATA_DIR": str(dossier / "tofu" / ".terraform"),
            "TF_IN_AUTOMATION": "1",
            "TF_VAR_session_id": session.id,
            "TF_VAR_projet_id": scw.projet(),
            "TF_VAR_type_instance": session.type_instance,
            "TF_VAR_echeance_garde_fou": session.echeance_garde_fou.astimezone(dt.UTC).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
    )
    for cle in ("webui_secret_key", "formateur_courriel", "formateur_mot_de_passe", "acces_jeton"):
        env[f"TF_VAR_{cle}"] = valeurs[cle]
    return env


def tofu(env, dossier, *arguments, capture=False):
    (dossier / "tofu").mkdir(exist_ok=True)
    commande = ["tofu", f"-chdir={INFRA}", *arguments]
    resultat = subprocess.run(  # noqa: S603 (commande fixe, sans shell)
        commande, env=env, check=False, capture_output=capture, text=True
    )
    if resultat.returncode != 0:
        raise scw.ErreurScaleway(f"tofu {arguments[0]} a échoué (code {resultat.returncode})")
    return resultat.stdout if capture else None


def tofu_init(env, dossier):
    etat = dossier / "tofu" / "terraform.tfstate"
    tofu(env, dossier, "init", "-input=false", f"-backend-config=path={etat}", "-reconfigure")


# --- Accès à Open WebUI ------------------------------------------------------------------


def cookie_acces(valeurs):
    return f"atelier_acces={valeurs['acces_jeton']}"


def client_formateur(session, valeurs, delai_max=0):
    client = openwebui.Client(f"https://{session.adresse}", cookie=cookie_acces(valeurs))
    if delai_max:
        client.attendre_sante(delai_max=delai_max, intervalle=10)
    client.connexion(valeurs["formateur_courriel"], valeurs["formateur_mot_de_passe"])
    return client


def configurer_session(client, session, cle_api, liste):
    """Appels 1 à 7 de contracts/configuration-openwebui.md pour une session hébergée."""
    groupe = openwebui.assurer_groupe(
        client, f"participants-{session.id}", "Participants de la session (comptes du formateur)"
    )
    droits = [{"principal_type": "group", "principal_id": groupe, "permission": "read"}]
    openwebui.configurer(client, f"https://api.scaleway.ai/{scw.projet()}/v1", cle_api, droits)
    ids = [
        openwebui.assurer_utilisateur(
            client, c.nom_complet, c.courriel, c.mot_de_passe, c.role_openwebui
        )
        for c in liste
    ]
    client.post(f"/api/v1/groups/id/{groupe}/users/add", {"user_ids": ids})
    return groupe


# --- Commandes ---------------------------------------------------------------------------


def creer(args):
    dossier = dossier_session(args.session)
    session, participants, estimation = cout.calculer(dossier)
    print(cout.texte(estimation, len(participants), session.type_instance))
    if (
        not args.oui
        and input("\nCréer la session chez Scaleway (Paris) ? [oui/non] ").strip() != "oui"
    ):
        print("Abandon : rien n'a été créé.")
        return 1
    debut = time.monotonic()
    valeurs = secrets_session(dossier, session)
    liste = comptes_session(dossier, session)
    env = environnement_tofu(dossier, session, valeurs)
    tofu_init(env, dossier)
    tofu(env, dossier, "apply", "-input=false", "-auto-approve")
    cle_api = tofu(env, dossier, "output", "-raw", "cle_api", capture=True)
    print(
        f"Infrastructure créée ; attente de https://{session.adresse} "
        "(DNS, certificat, démarrage)..."
    )
    client = client_formateur(session, valeurs, delai_max=1200)
    configurer_session(client, session, cle_api, liste)
    lien = f"https://{session.adresse}/acces/{valeurs['acces_jeton']}"
    formateur = comptes.Compte(
        "Formateur",
        "",
        valeurs["formateur_courriel"],
        valeurs["formateur_mot_de_passe"],
        "formateur",
    )
    comptes.ecrire_fiches(
        dossier / "identifiants",
        liste + [formateur],
        session.client,
        f"https://{session.adresse}",
        lien,
    )
    print(f"Session prête en {(time.monotonic() - debut) / 60:.0f} min : https://{session.adresse}")
    print(f"Fiches d'identifiants : {dossier / 'identifiants'}")
    print("Contrôle de bout en bout :")
    from atelier import controle

    return controler(args, controle.controler)


def controler(args, fonction_controle):
    dossier = dossier_session(args.session)
    session = config.lire_session(dossier)
    valeurs = secrets_session(dossier, session)
    return fonction_controle(
        f"https://{session.adresse}",
        client_formateur(session, valeurs),
        f"{session.id}.atelier",
        cookie=cookie_acces(valeurs),
        charge=getattr(args, "charge", 0),
    )


def statut(args):
    dossier = dossier_session(args.session)
    session = config.lire_session(dossier)
    etat = dossier / "tofu" / "terraform.tfstate"
    restant = session.echeance_garde_fou - dt.datetime.now(dt.UTC)
    print(f"Session {session.id} : https://{session.adresse}")
    print(
        f"État OpenTofu : {'présent' if etat.exists() else 'absent (session non créée ou purgée)'}"
    )
    if etat.exists() and (dossier / "secrets.json").exists():
        try:
            client = openwebui.Client(
                f"https://{session.adresse}", cookie=cookie_acces(secrets_session(dossier, session))
            )
            client.get("/health")
            print("Service : répond")
        except openwebui.ErreurOpenWebUI as erreur:
            print(f"Service : ne répond pas ({erreur})")
    heures = restant.total_seconds() / 3600
    print(f"Garde-fou : {session.echeance_garde_fou:%Y-%m-%d %H:%M} (dans {heures:.0f} h)")
    if etat.exists():
        print(
            f"RAPPEL : lancer `atelier session purger --session {session.id}` après la formation."
        )
    return 0


def exporter_consignes(prompts, formateur_id):
    """Consignes exportées (data-model.md Consigne) : auteur réduit à formateur ou participant."""
    return [
        {
            "commande": p["command"],
            "titre": p.get("name") or p.get("title") or "",
            "contenu": p["content"],
            "auteur": "formateur" if p.get("user_id") == formateur_id else "participant",
        }
        for p in sorted(prompts, key=lambda p: p["command"])
    ]


def consignes_markdown(consignes):
    lignes = ["# Bibliothèque de consignes de la session", ""]
    for c in consignes:
        lignes += [
            f"## /{c['commande'].lstrip('/')} : {c['titre']} ({c['auteur']})",
            "",
            c["contenu"],
            "",
        ]
    return "\n".join(lignes)


def exporter(args):
    dossier = dossier_session(args.session)
    session = config.lire_session(dossier)
    client = client_formateur(session, secrets_session(dossier, session))
    moi = client.get("/api/v1/auths/")
    consignes = exporter_consignes(client.get("/api/v1/prompts/") or [], moi["id"])
    sortie = EXPORTS / session.id
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "consignes.json").write_text(
        json.dumps(consignes, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (sortie / "consignes.md").write_text(consignes_markdown(consignes), encoding="utf-8")
    print(
        f"{len(consignes)} consigne(s) exportée(s) dans {sortie}/ (aucun document ni discussion)."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit("Utiliser la commande ./atelier.")
