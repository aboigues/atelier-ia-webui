#!/usr/bin/env python3
"""Verdict du contrôle sast-codeql à partir des fichiers SARIF produits localement par CodeQL.

L'action `analyze` ne fait pas échouer la tâche quand elle trouve une alerte, et une PR issue
d'un fork ne peut pas déposer ses résultats : le verdict est donc rendu ici, identique dans tous
les cas. Bloque toute alerte de niveau `error` ou `warning` (niveau par défaut en SARIF) dont la
règle porte l'étiquette `security`.

Usage : verdict_codeql.py <dossier SARIF>   Codes : 0 aucune alerte, 1 alerte, 3 SARIF absent.
"""

import json
import sys
from pathlib import Path

NIVEAUX_BLOQUANTS = {"error", "warning"}


class ErreurSarif(RuntimeError):
    """Aucun résultat d'analyse exploitable : jamais un succès."""


def _regles(run):
    outil = run.get("tool", {})
    regles = list(outil.get("driver", {}).get("rules", []))
    for extension in outil.get("extensions", []):
        regles += extension.get("rules", [])
    return {r.get("id"): r for r in regles}


def alertes_bloquantes(dossier):
    fichiers = sorted(Path(dossier).glob("*.sarif"))
    if not fichiers:
        raise ErreurSarif(f"aucun fichier SARIF dans {dossier}")
    alertes = []
    for f in fichiers:
        for run in json.loads(f.read_text(encoding="utf-8")).get("runs", []):
            regles = _regles(run)
            for r in run.get("results", []):
                regle = regles.get(r.get("ruleId"), {})
                tags = regle.get("properties", {}).get("tags", [])
                if "security" not in tags or r.get("level", "warning") not in NIVEAUX_BLOQUANTS:
                    continue
                lieu = "?"
                if r.get("locations"):
                    phys = r["locations"][0].get("physicalLocation", {})
                    uri = phys.get("artifactLocation", {}).get("uri", "?")
                    lieu = f"{uri}:{phys.get('region', {}).get('startLine', '?')}"
                texte = r.get("message", {}).get("text", "")
                alertes.append(f"{lieu}: {r.get('ruleId')} : {texte}")
    return alertes


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        alertes = alertes_bloquantes(sys.argv[1])
    except (ErreurSarif, json.JSONDecodeError, OSError) as erreur:
        print(f"ÉCHEC : analyse CodeQL inexploitable : {erreur}")
        return 3
    for a in alertes:
        print(a)
    if alertes:
        print(f"ÉCHEC : {len(alertes)} alerte(s) de sécurité CodeQL.")
        return 1
    print("OK : aucune alerte de sécurité CodeQL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
