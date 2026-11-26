"""Coût estimé d'une session (FR-015, research.md R10), affiché avant toute création."""

from pathlib import Path

from atelier import config, scw

RACINE = Path(__file__).resolve().parents[2]


def estimer(prix_horaire, tarifs, participants, modele):
    h = tarifs.hypotheses
    if modele not in tarifs.modeles:
        raise config.ErreurConfig(f"tarifs.toml : aucun tarif pour « {modele} »")
    t = tarifs.modeles[modele]
    demandes = participants * h["demandes_par_participant"]
    entree = demandes * h["jetons_entree_par_demande"] / 1e6 * t["entree_eur_par_million"]
    sortie = demandes * h["jetons_sortie_par_demande"] / 1e6 * t["sortie_eur_par_million"]
    e = {
        "instance": prix_horaire * h["heures_instance"],
        "ip": h["ip_eur_par_heure"] * h["heures_instance"],
        "modele": entree + sortie,
    }
    e["total"] = sum(e.values())
    return {k: round(v, 2) for k, v in e.items()}


def _eur(v):
    return f"{v:,.2f} EUR".replace(",", " ").replace(".", ",")


def texte(e, participants, type_instance):
    return "\n".join(
        [
            f"Coût estimé de la session ({participants} participants, instance {type_instance}) :",
            f"  Instance       {_eur(e['instance'])}",
            f"  Adresse IP     {_eur(e['ip'])}",
            f"  Modèle         {_eur(e['modele'])}",
            f"  Total estimé   {_eur(e['total'])}",
            "Hypothèses et tarifs : infra/tarifs.toml (à revérifier tous les 30 jours).",
        ]
    )


def calculer(session_dir):
    session = config.lire_session(session_dir)
    participants = config.lire_participants(session_dir)
    tarifs = config.lire_tarifs(RACINE / "infra" / "tarifs.toml")
    e = estimer(
        scw.prix_horaire(session.type_instance), tarifs, len(participants), session.modele_reference
    )
    return session, participants, e


def afficher(args):
    from atelier.session import dossier_session

    session, participants, e = calculer(dossier_session(args.session))
    print(texte(e, len(participants), session.type_instance))
    return 0
