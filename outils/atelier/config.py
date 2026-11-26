"""Lecture et validation des fichiers de session (contracts/fichiers-session.md).

Champs et règles : data-model.md, entités Session et Compte. Le libellé du client
(Session.client) n'est jamais recopié dans un fichier versionné ni dans un journal.
"""

import csv
import datetime as dt
import io
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
RE_ID = re.compile(r"^[a-z0-9-]{3,30}$")
DUREE_MAX = dt.timedelta(days=7)
TARIFS_VALIDITE = dt.timedelta(days=30)
PARTICIPANTS_MAX = 15


class ErreurConfig(ValueError):
    """Fichier de session absent ou invalide (code de sortie 2)."""


@dataclass(frozen=True)
class Session:
    id: str
    client: str
    debut: dt.date
    fin: dt.date
    type_instance: str = "DEV1-L"
    modele_reference: str = "mistral-medium-3.5-128b"
    modele_secours: str = "mistral-small-3.2-24b-instruct-2506"

    @property
    def echeance_garde_fou(self):
        """Fin de session à 18 h (heure de Paris), plus 48 heures."""
        fin = dt.datetime.combine(self.fin, dt.time(18, 0), tzinfo=PARIS)
        return fin + dt.timedelta(hours=48)

    @property
    def adresse(self):
        return f"{self.id}.atelier.telemach-learning.fr"


@dataclass(frozen=True)
class Participant:
    prenom: str
    nom: str


@dataclass(frozen=True)
class Tarifs:
    verifie_le: dt.date
    modeles: dict
    hypotheses: dict


def _lire_toml(chemin):
    try:
        return tomllib.loads(Path(chemin).read_text(encoding="utf-8"))
    except FileNotFoundError as erreur:
        raise ErreurConfig(f"fichier absent : {chemin}") from erreur
    except tomllib.TOMLDecodeError as erreur:
        raise ErreurConfig(f"{chemin} illisible : {erreur}") from erreur


def lire_session(dossier):
    """Lit <dossier>/session.toml et applique les règles de data-model.md (Session)."""
    brut = _lire_toml(Path(dossier) / "session.toml")
    for champ in ("id", "client", "debut", "fin"):
        if champ not in brut:
            raise ErreurConfig(f"session.toml : champ « {champ} » manquant")
    if not isinstance(brut["id"], str) or not RE_ID.match(brut["id"]):
        raise ErreurConfig("session.toml : « id » doit respecter [a-z0-9-]{3,30}")
    for champ in ("debut", "fin"):
        if type(brut[champ]) is not dt.date:
            raise ErreurConfig(f"session.toml : « {champ} » doit être une date AAAA-MM-JJ")
    if brut["fin"] < brut["debut"]:
        raise ErreurConfig("session.toml : « fin » précède « debut »")
    if brut["fin"] - brut["debut"] > DUREE_MAX:
        raise ErreurConfig("session.toml : la session dépasse 7 jours")
    options = {
        k: brut[k] for k in ("type_instance", "modele_reference", "modele_secours") if k in brut
    }
    return Session(brut["id"], str(brut["client"]), brut["debut"], brut["fin"], **options)


def lire_participants(dossier):
    """Lit <dossier>/participants.csv (UTF-8, séparateur ; ou , , en-tête prenom;nom)."""
    chemin = Path(dossier) / "participants.csv"
    try:
        texte = chemin.read_text(encoding="utf-8-sig")
    except FileNotFoundError as erreur:
        raise ErreurConfig(f"fichier absent : {chemin}") from erreur
    premiere = texte.splitlines()[0] if texte.strip() else ""
    separateur = ";" if ";" in premiere else ","
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=separateur)
    if [c.strip().lower() for c in (lecteur.fieldnames or [])][:2] != ["prenom", "nom"]:
        raise ErreurConfig("participants.csv : en-tête « prenom;nom » obligatoire")
    participants = []
    for n, ligne in enumerate(lecteur, 2):
        prenom = (ligne.get("prenom") or "").strip()
        nom = (ligne.get("nom") or "").strip()
        if not prenom or not nom:
            raise ErreurConfig(f"participants.csv, ligne {n} : prénom ou nom vide")
        participants.append(Participant(prenom, nom))
    if not 1 <= len(participants) <= PARTICIPANTS_MAX:
        raise ErreurConfig(f"participants.csv : 1 à {PARTICIPANTS_MAX} participants attendus")
    return participants


def lire_tarifs(chemin, jour=None):
    """Lit infra/tarifs.toml ; refuse des tarifs vérifiés il y a plus de 30 jours."""
    jour = jour or dt.date.today()
    brut = _lire_toml(chemin)
    verifie = brut.get("verifie_le")
    if type(verifie) is not dt.date:
        raise ErreurConfig("tarifs.toml : « verifie_le » manquant ou invalide")
    if jour - verifie > TARIFS_VALIDITE:
        raise ErreurConfig(
            f"tarifs.toml vérifiés le {verifie}, il y a plus de 30 jours : les revérifier"
        )
    return Tarifs(verifie, brut.get("modeles", {}), brut.get("hypotheses", {}))
