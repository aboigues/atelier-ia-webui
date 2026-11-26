#!/usr/bin/env python3
"""Protection de main et réglages de sécurité du dépôt GitHub (FR-004, FR-005, FR-006).

appliquer : crée ou met à jour le ruleset décrit par .github/rulesets/main.json, active le
            secret scanning et la push protection, désactive le « default setup » de CodeQL
            (l'analyse est faite par le workflow controles.yml). Idempotent.
verifier  : compare l'état réel au fichier versionné ; code 1 et liste des écarts sinon.

Nécessite `gh` connecté avec les droits d'administration du dépôt.
Usage : regles_github.py appliquer|verifier [--depot propriétaire/nom]
Codes : 0 conforme, 1 écart, 2 usage, 3 GitHub injoignable.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / ".github/rulesets/main.json"
GITHUB_ACTIONS = 15368
METHODES_AUTORISEES = {"squash", "rebase"}


class ErreurGitHub(RuntimeError):
    """Appel à l'API GitHub impossible."""


def appel_gh(methode, chemin, corps=None):
    """Appel à l'API REST par `gh api` (commande fixe, arguments en liste, sans shell)."""
    commande = ["gh", "api", "--method", methode, chemin]  # gh pris dans le PATH
    if corps is not None:
        commande += ["--input", "-"]
    resultat = subprocess.run(  # noqa: S603
        commande,
        input=json.dumps(corps) if corps is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        raise ErreurGitHub(f"gh api {methode} {chemin} : {resultat.stderr.strip()}")
    return json.loads(resultat.stdout) if resultat.stdout.strip() else {}


def _regles(etat):
    return {r["type"]: r.get("parameters", {}) for r in etat.get("rules", [])}


def ecarts(attendu, reel, depot):
    """Liste des écarts entre le ruleset attendu, le ruleset réel et les réglages du dépôt."""
    messages = []
    if reel.get("enforcement") != "active":
        messages.append(f"enforcement = {reel.get('enforcement')} (attendu : active)")
    if reel.get("bypass_actors"):
        messages.append("acteurs de contournement présents (attendu : aucun)")
    cibles = reel.get("conditions", {}).get("ref_name", {}).get("include", [])
    if "refs/heads/main" not in cibles:
        messages.append(f"le ruleset ne cible pas main ({cibles})")

    r_att, r_reel = _regles(attendu), _regles(reel)
    for type_ in r_att:
        if type_ not in r_reel:
            messages.append(f"règle absente : {type_}")

    methodes = set(r_reel.get("pull_request", {}).get("allowed_merge_methods", []))
    if "pull_request" in r_reel and methodes != METHODES_AUTORISEES:
        messages.append(f"méthodes de merge {sorted(methodes)} (attendu : squash et rebase)")

    controles = r_reel.get("required_status_checks", {})
    if controles and not controles.get("strict_required_status_checks_policy"):
        messages.append("contrôles requis non stricts (branche à jour exigée)")
    reels = {
        c.get("context"): c.get("integration_id")
        for c in controles.get("required_status_checks", [])
    }
    att = r_att.get("required_status_checks", {}).get("required_status_checks", [])
    for c in att:
        nom = c["context"]
        if nom not in reels:
            messages.append(f"contrôle requis absent : {nom}")
        elif reels[nom] != GITHUB_ACTIONS:
            messages.append(
                f"contrôle requis « {nom} » non lié à GitHub Actions ({GITHUB_ACTIONS})"
            )
    for nom in set(reels) - {c["context"] for c in att}:
        messages.append(f"contrôle requis inattendu : {nom}")

    reglages = depot.get("security_and_analysis") or {}
    for cle in ("secret_scanning", "secret_scanning_push_protection"):
        if (reglages.get(cle) or {}).get("status") != "enabled":
            messages.append(f"{cle} n'est pas activé")
    return messages


def _attendu():
    return json.loads(FICHIER.read_text(encoding="utf-8"))


def _trouver(depot, appel, nom):
    for r in appel("GET", f"repos/{depot}/rulesets") or []:
        if r.get("name") == nom:
            return r["id"]
    return None


def appliquer(depot, appel=appel_gh):
    attendu = _attendu()
    ident = _trouver(depot, appel, attendu["name"])
    if ident is None:
        appel("POST", f"repos/{depot}/rulesets", attendu)
    else:
        appel("PUT", f"repos/{depot}/rulesets/{ident}", attendu)
    appel(
        "PATCH",
        f"repos/{depot}",
        {
            "security_and_analysis": {
                "secret_scanning": {"status": "enabled"},
                "secret_scanning_push_protection": {"status": "enabled"},
            }
        },
    )
    appel("PATCH", f"repos/{depot}/code-scanning/default-setup", {"state": "not-configured"})


def verifier(depot, appel=appel_gh):
    attendu = _attendu()
    ident = _trouver(depot, appel, attendu["name"])
    if ident is None:
        return [f"ruleset « {attendu['name']} » absent du dépôt {depot}"]
    reel = appel("GET", f"repos/{depot}/rulesets/{ident}")
    return ecarts(attendu, reel, appel("GET", f"repos/{depot}"))


def depot_courant():
    resultat = subprocess.run(  # noqa: S603
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        cwd=RACINE,
    )
    if resultat.returncode != 0:
        raise ErreurGitHub(resultat.stderr.strip())
    return resultat.stdout.strip()


def main(argv=None):
    parseur = argparse.ArgumentParser(description="Protection de main (ruleset GitHub).")
    parseur.add_argument("action", choices=["appliquer", "verifier"])
    parseur.add_argument("--depot", help="propriétaire/nom (par défaut : dépôt courant)")
    args = parseur.parse_args(argv)
    try:
        depot = args.depot or depot_courant()
        if args.action == "appliquer":
            appliquer(depot)
            print(f"Ruleset et réglages de sécurité appliqués à {depot}.")
        messages = verifier(depot)
    except ErreurGitHub as erreur:
        print(f"ÉCHEC : GitHub injoignable ou droits insuffisants : {erreur}")
        return 3
    for m in messages:
        print(f"ÉCART : {m}")
    if messages:
        print(f"ÉCHEC : {len(messages)} écart(s) avec .github/rulesets/main.json.")
        return 1
    print(f"OK : protection de main conforme sur {depot}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
