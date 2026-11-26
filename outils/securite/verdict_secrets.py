#!/usr/bin/env python3
"""Verdict du contrôle « secrets » à partir des résultats JSON de TruffleHog (FR-006, FR-008).

TruffleHog écrit une trouvaille par ligne JSON. Une trouvaille est ignorée seulement si un faux
positif valide de securite/exceptions.toml porte l'identifiant `<commit>:<fichier>:<ligne>`.
La valeur d'un secret n'est JAMAIS affichée (FR-012) : seuls le détecteur, le fichier, la ligne
et le commit le sont.

Usage : verdict_secrets.py <resultats.jsonl>
Codes : 0 aucune fuite, 1 fuite, 2 exceptions invalides, 3 résultats inexploitables.
"""

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path


def _module_exceptions():
    if "exceptions_securite" in sys.modules:
        return sys.modules["exceptions_securite"]
    spec = importlib.util.spec_from_file_location(
        "exceptions_securite", Path(__file__).with_name("exceptions.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["exceptions_securite"] = module
    spec.loader.exec_module(module)
    return module


class ErreurSecrets(RuntimeError):
    """Résultats de TruffleHog absents ou illisibles : jamais un succès."""


def fuites(fichier, exceptions, jour):
    try:
        lignes = Path(fichier).read_text(encoding="utf-8").splitlines()
    except OSError as erreur:
        raise ErreurSecrets(f"{fichier} illisible : {erreur}") from erreur
    ignorees = {
        e.id for e in exceptions if e.type == "secret-faux-positif" and e.etat(jour) == "valide"
    }
    resultat = []
    for n, ligne in enumerate(lignes, 1):
        if not ligne.strip():
            continue
        try:
            t = json.loads(ligne)
        except json.JSONDecodeError as erreur:
            raise ErreurSecrets(f"{fichier}, ligne {n} : JSON illisible") from erreur
        git = t.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
        commit, chemin, num = git.get("commit", "?"), git.get("file", "?"), git.get("line", "?")
        if f"{commit}:{chemin}:{num}" in ignorees:
            continue
        verifie = "vérifié" if t.get("Verified") else "non vérifié"
        resultat.append(
            f"{chemin}:{num}: secret « {t.get('DetectorName', '?')} » ({verifie}) "
            f"dans le commit {commit[:12]} ; exception éventuelle : {commit}:{chemin}:{num}"
        )
    return resultat


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    ex = _module_exceptions()
    jour = dt.date.today()
    try:
        exceptions = ex.charger(jour)
    except ex.ErreurExceptions as erreur:
        print(f"ÉCHEC : securite/exceptions.toml invalide : {erreur}")
        return 2
    try:
        liste = fuites(sys.argv[1], exceptions, jour)
    except ErreurSecrets as erreur:
        print(f"ÉCHEC : {erreur}")
        return 3
    for f in liste:
        print(f)
    if liste:
        print(f"ÉCHEC : {len(liste)} secret(s) détecté(s). Révoquer le secret, puis le retirer.")
        return 1
    print("OK : aucun secret détecté dans l'historique.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
