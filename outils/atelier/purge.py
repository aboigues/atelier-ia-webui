"""Purge vérifiable d'une session (FR-011, SC-005 ; contracts/cli.md).

`tofu destroy` (relançable après interruption), inventaire Scaleway par étiquette et par nom,
puis suppression de sessions/<id>/ seulement si l'inventaire est vide. Le rapport
(exports/<id>/rapport-purge.md) ne contient aucun nom de personne ni de document.
"""

import datetime as dt
import shutil

from atelier import config, scw
from atelier.session import (
    EXPORTS,
    dossier_session,
    environnement_tofu,
    secrets_session,
    tofu,
    tofu_init,
)


def rapport(session_id, debut, fin, supprimees, restes, locales):
    complet = not restes
    lignes = [
        f"Rapport de purge - session {session_id}",
        f"Début : {debut:%Y-%m-%d %H:%M:%S %Z}   Fin : {fin:%Y-%m-%d %H:%M:%S %Z}",
        "Ressources Scaleway supprimées (OpenTofu) :",
        *[f"  {r}" for r in supprimees or ["(aucune ressource dans l'état)"]],
        f"Inventaire après purge (étiquette atelier-session={session_id}) : "
        f"{len(restes)} ressource(s)",
        *[f"  RESTE {t} {i} {n}" for t, i, n in restes],
        "Données locales supprimées :",
        *[f"  {d}" for d in locales or ["(aucune)"]],
        "Résultat : " + ("purge complète" if complet else "purge incomplète (relancer la purge)"),
    ]
    return "\n".join(lignes) + "\n"


def supprimer_local(dossier, restes):
    """Supprime sessions/<id>/ (participants, identifiants, secrets, état) si rien ne subsiste."""
    if restes or not dossier.exists():
        return []
    shutil.rmtree(dossier)
    return [str(dossier)]


def _ressources_etat(env, dossier):
    try:
        sortie = tofu(env, dossier, "state", "list", capture=True)
    except scw.ErreurScaleway:
        return []
    return [ligne for ligne in sortie.splitlines() if ligne.strip()]


def purger(args):
    dossier = dossier_session(args.session)
    session = config.lire_session(dossier)
    if (
        not args.oui
        and input(f"Détruire la session {session.id} et toutes ses données ? [oui/non] ").strip()
        != "oui"
    ):
        print("Abandon : rien n'a été supprimé.")
        return 1
    debut = dt.datetime.now(dt.UTC)
    env = environnement_tofu(dossier, session, secrets_session(dossier, session))
    supprimees = []
    if (dossier / "tofu").exists():
        tofu_init(env, dossier)
        supprimees = _ressources_etat(env, dossier)
        tofu(env, dossier, "destroy", "-input=false", "-auto-approve")
    restes = scw.inventaire(session.id)
    locales = supprimer_local(dossier, restes)
    texte = rapport(session.id, debut, dt.datetime.now(dt.UTC), supprimees, restes, locales)
    sortie = EXPORTS / session.id
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "rapport-purge.md").write_text(texte, encoding="utf-8")
    print(texte)
    print(f"Rapport : {sortie / 'rapport-purge.md'}")
    return 1 if restes else 0


def verifier(args):
    restes = scw.inventaire(args.session)
    for t, i, n in restes:
        print(f"RESTE {t} {i} {n}")
    print(f"{len(restes)} ressource(s) de la session {args.session} chez Scaleway.")
    return 1 if restes else 0
