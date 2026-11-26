"""Commande `atelier` (specs/001-environnement-tp-session/contracts/cli.md).

Codes de sortie : 0 succès ; 1 échec d'un contrôle ; 2 erreur d'usage ou de configuration ;
3 ressource externe indisponible (Docker, Scaleway, DNS, Open WebUI).
"""

import argparse
import importlib
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]

# (groupe, action) -> (module, fonction)
ACTIONS = {
    ("local", "demarrer"): ("local", "demarrer"),
    ("local", "arreter"): ("local", "arreter"),
    ("local", "controler"): ("controle", "controler_local"),
    ("session", "cout"): ("cout", "afficher"),
    ("session", "creer"): ("session", "creer"),
    ("session", "controler"): ("controle", "controler_session"),
    ("session", "statut"): ("session", "statut"),
    ("session", "exporter"): ("session", "exporter"),
    ("session", "purger"): ("purge", "purger"),
    ("session", "verifier-purge"): ("purge", "verifier"),
}


def analyseur():
    p = argparse.ArgumentParser(prog="atelier", description="Environnement de travaux pratiques.")
    groupes = p.add_subparsers(dest="groupe", required=True)

    local = groupes.add_parser("local", help="poste du formateur (Docker)")
    a_local = local.add_subparsers(dest="action", required=True)
    a_local.add_parser("demarrer", help="démarrer, configurer, charger le jeu fictif")
    arret = a_local.add_parser("arreter", help="arrêter les conteneurs")
    arret.add_argument(
        "--effacer", action="store_true", help="supprimer aussi comptes, discussions et fichiers"
    )
    a_local.add_parser("controler", help="contrôle de bout en bout")

    session = groupes.add_parser("session", help="session hébergée chez Scaleway (Paris)")
    a_session = session.add_subparsers(dest="action", required=True)
    for nom, aide in (
        ("cout", "coût estimé"),
        ("creer", "créer la session"),
        ("controler", "contrôle de bout en bout"),
        ("statut", "état et échéance"),
        ("exporter", "exporter les consignes"),
        ("purger", "tout détruire et produire le rapport"),
        ("verifier-purge", "inventaire seul"),
    ):
        sp = a_session.add_parser(nom, help=aide)
        sp.add_argument("--session", required=True, help="identifiant (dossier sessions/<id>/)")
        if nom in ("creer", "purger"):
            sp.add_argument("--oui", action="store_true", help="ne pas demander de confirmation")
        if nom == "controler":
            sp.add_argument("--charge", type=int, default=0, help="N demandes simultanées")
    return p


def main(argv=None):
    args = analyseur().parse_args(argv)
    nom_module, nom_fonction = ACTIONS[(args.groupe, args.action)]
    module = importlib.import_module(f"atelier.{nom_module}")
    from atelier.config import ErreurConfig
    from atelier.openwebui import ErreurOpenWebUI
    from atelier.scw import ErreurScaleway

    try:
        return getattr(module, nom_fonction)(args) or 0
    except ErreurConfig as erreur:
        print(f"ERREUR de configuration : {erreur}", file=sys.stderr)
        return 2
    except (ErreurScaleway, ErreurOpenWebUI) as erreur:
        print(f"ERREUR : service indisponible : {erreur}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("Interrompu.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
