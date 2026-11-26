#!/usr/bin/env python3
"""Exceptions de sécurité datées (FR-008, contracts/exceptions.md).

Chaque exception porte les champs de data-model.md « Exception de sécurité » : id, type,
portee, raison, acceptee_par, acceptee_le, reexamen_le. Une exception échue reste un fichier
valide mais cesse de s'appliquer.

Identifiant d'un faux positif de secret : `<commit>:<fichier>:<ligne>` (verdict_secrets.py).

Usage : exceptions.py verifier   valide securite/exceptions.toml (code 1 si invalide)
"""

import datetime as dt
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

FICHIER = Path(__file__).resolve().parents[2] / "securite/exceptions.toml"
TYPES = ("vulnerabilite", "secret-faux-positif", "classe")
CHAMPS = ("id", "type", "portee", "raison", "acceptee_par", "acceptee_le", "reexamen_le")
DELAI_MAX = dt.timedelta(days=90)
ALERTE = dt.timedelta(days=14)
RAISON_MIN = 20


class ErreurExceptions(ValueError):
    """Fichier d'exceptions invalide."""


@dataclass(frozen=True)
class ExceptionSecurite:
    id: str
    type: str
    portee: str
    raison: str
    acceptee_par: str
    acceptee_le: dt.date
    reexamen_le: dt.date

    def etat(self, jour):
        return "valide" if jour <= self.reexamen_le else "echue"

    def proche_echeance(self, jour):
        return self.etat(jour) == "valide" and self.reexamen_le - jour <= ALERTE


def _valider(n, brut, jour):
    lieu = f"exception n° {n}"
    manquants = [c for c in CHAMPS if c not in brut]
    if manquants:
        raise ErreurExceptions(f"{lieu} : champ(s) manquant(s) : {', '.join(manquants)}")
    for c in ("id", "type", "portee", "raison", "acceptee_par"):
        if not isinstance(brut[c], str) or not brut[c].strip():
            raise ErreurExceptions(f"{lieu} : « {c} » doit être un texte non vide")
    for c in ("acceptee_le", "reexamen_le"):
        if type(brut[c]) is not dt.date:
            raise ErreurExceptions(f"{lieu} : « {c} » doit être une date AAAA-MM-JJ")
    e = ExceptionSecurite(**{c: brut[c] for c in CHAMPS})
    if e.type not in TYPES:
        raise ErreurExceptions(f"{lieu} : type « {e.type} » inconnu ({', '.join(TYPES)})")
    if e.portee == "*" and e.type != "classe":
        raise ErreurExceptions(f"{lieu} : portée « * » réservée au type « classe »")
    if len(e.raison.strip()) < RAISON_MIN:
        raise ErreurExceptions(f"{lieu} : raison trop courte ({RAISON_MIN} caractères au moins)")
    if e.acceptee_par != "Alexandre":
        raise ErreurExceptions(f"{lieu} : seule l'acceptation d'Alexandre est valable")
    if e.acceptee_le > jour:
        raise ErreurExceptions(f"{lieu} : date d'acceptation dans le futur ({e.acceptee_le})")
    if not e.acceptee_le < e.reexamen_le <= e.acceptee_le + DELAI_MAX:
        raise ErreurExceptions(
            f"{lieu} : le réexamen doit suivre l'acceptation de 90 jours au plus "
            f"({e.acceptee_le} -> {e.reexamen_le})"
        )
    return e


def charger(jour=None, chemin=FICHIER):
    """Charge et valide toutes les exceptions (valides et échues)."""
    jour = jour or dt.date.today()
    try:
        donnees = tomllib.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        raise ErreurExceptions(f"{chemin} illisible : {erreur}") from erreur
    return [_valider(n, b, jour) for n, b in enumerate(donnees.get("exception", []), 1)]


def main(argv):
    if len(argv) != 2 or argv[1] != "verifier":
        print(__doc__, file=sys.stderr)
        return 2
    jour = dt.date.today()
    try:
        excs = charger(jour)
    except ErreurExceptions as erreur:
        print(f"ÉCHEC : securite/exceptions.toml invalide : {erreur}")
        return 1
    for e in excs:
        if e.etat(jour) == "echue":
            print(f"ÉCHUE (ne s'applique plus) : {e.id} ({e.type}), réexamen dû le {e.reexamen_le}")
        elif e.proche_echeance(jour):
            print(f"À RÉEXAMINER avant le {e.reexamen_le} : {e.id} ({e.type})")
    print(f"OK : {len(excs)} exception(s) au format valide.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
