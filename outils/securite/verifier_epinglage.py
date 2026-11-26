#!/usr/bin/env python3
"""Vérifie l'épinglage de la chaîne d'approvisionnement (FR-010, FR-015, constitution VII).

Règles :
- chaque `uses:` d'un workflow est épinglé par SHA de 40 caractères, suivi d'un commentaire de
  version (`# v1.2.3`) ; les actions locales (`./...`) sont acceptées ;
- `docker run` n'apparaît que dans outils/securite/lib.sh, qui prend les images dans
  securite/outils.lock ; toute image de conteneur d'un workflow vient de ce fichier ;
- chaque ligne de securite/outils.lock porte une version explicite (jamais `latest`) et une
  empreinte sha256 ;
- aucune tâche requise par le ruleset de main ne porte de condition `if:` au niveau de la tâche
  (GitHub compte un contrôle requis « ignoré » comme réussi).

Usage : verifier_epinglage.py [racine]   Codes : 0 conforme, 1 non conforme, 2 configuration.
"""

import json
import re
import sys
from pathlib import Path

RE_USES = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)\s*(#.*)?$")
RE_SHA = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")
RE_COMMENTAIRE_VERSION = re.compile(r"#\s*v?\d+(\.\d+)*")
RE_IMAGE = re.compile(r"^\s*(?:-\s*)?(?:image|container):\s*['\"]?([^\s'\"#]+)")
RE_LOCK_IMAGE = re.compile(r"^[\w.-]+=[\w./-]+:([\w.-]+)@sha256:[0-9a-f]{64}$")
RE_LOCK_BINAIRE = re.compile(r"^[\w.-]+=https://\S+#sha256=[0-9a-f]{64}$")
# Appel réel de « docker run » : commande shell, ou liste d'arguments de subprocess en Python.
RE_DOCKER_RUN_SH = re.compile(r"(^|[;&|(]|\s)docker\s+run\b")
RE_DOCKER_RUN_PY = re.compile(r"[\"']docker[\"']\s*,\s*[\"']run[\"']")


def lire_lock(racine):
    messages, valeurs = [], set()
    chemin = racine / "securite/outils.lock"
    if not chemin.exists():
        return [f"{chemin}: fichier absent"], valeurs
    for n, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        lieu = f"securite/outils.lock:{n}"
        m = RE_LOCK_IMAGE.match(ligne)
        if m:
            if m.group(1) == "latest":
                messages.append(f"{lieu}: version « latest » interdite")
            valeurs.add(ligne.split("=", 1)[1])
        elif RE_LOCK_BINAIRE.match(ligne):
            valeurs.add(ligne.split("=", 1)[1])
        else:
            messages.append(f"{lieu}: ligne sans version explicite ou sans empreinte sha256")
    return messages, valeurs


def contextes_requis(racine):
    chemin = racine / ".github/rulesets/main.json"
    if not chemin.exists():
        return set()
    regles = json.loads(chemin.read_text(encoding="utf-8")).get("rules", [])
    return {
        c["context"]
        for r in regles
        if r.get("type") == "required_status_checks"
        for c in r.get("parameters", {}).get("required_status_checks", [])
    }


def taches_avec_if(texte):
    """Renvoie {nom de contrôle: numéro de ligne du if} pour les `if:` de niveau tâche."""
    resultat, dans_jobs, tache, nom = {}, False, None, {}
    for n, ligne in enumerate(texte.splitlines(), 1):
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        retrait = len(ligne) - len(ligne.lstrip(" "))
        cle = ligne.strip().split(":", 1)[0]
        if retrait == 0:
            dans_jobs = cle == "jobs"
            tache = None
        elif dans_jobs and retrait == 2:
            tache = cle
            nom[tache] = tache
        elif dans_jobs and tache and retrait == 4:
            if cle == "name":
                nom[tache] = ligne.split(":", 1)[1].strip().strip("'\"")
            elif cle == "if":
                resultat[tache] = n
    return {nom.get(t, t): n for t, n in resultat.items()}


def verifier(racine):
    racine = Path(racine)
    messages, valeurs_lock = lire_lock(racine)
    requis = contextes_requis(racine)

    for wf in sorted((racine / ".github/workflows").glob("*.y*ml")):
        rel = wf.relative_to(racine)
        texte = wf.read_text(encoding="utf-8")
        for n, ligne in enumerate(texte.splitlines(), 1):
            m = RE_USES.match(ligne)
            if m:
                cible, commentaire = m.group(1), m.group(2) or ""
                if cible.startswith("./"):
                    pass
                elif not RE_SHA.match(cible):
                    messages.append(
                        f"{rel}:{n}: action non épinglée par SHA de 40 caractères : {cible}"
                    )
                elif not RE_COMMENTAIRE_VERSION.search(commentaire):
                    messages.append(
                        f"{rel}:{n}: commentaire de version manquant après le SHA ({cible})"
                    )
            m = RE_IMAGE.match(ligne)
            if m and m.group(1) not in valeurs_lock:
                messages.append(f"{rel}:{n}: image hors de securite/outils.lock : {m.group(1)}")
            if "docker run" in ligne:
                messages.append(
                    f"{rel}:{n}: « docker run » interdit hors de outils/securite/lib.sh"
                )
        for controle, n in sorted(taches_avec_if(texte).items()):
            if controle in requis:
                messages.append(
                    f"{rel}:{n}: condition « if: » interdite sur la tâche requise « {controle} » "
                    "(un contrôle ignoré compterait comme réussi)"
                )

    for script in sorted((racine / "outils/securite").glob("*")):
        if script.name == "lib.sh" or not script.is_file() or script.suffix not in (".sh", ".py"):
            continue
        if script.name == "verifier_epinglage.py":
            continue
        motif = RE_DOCKER_RUN_PY if script.suffix == ".py" else RE_DOCKER_RUN_SH
        for n, ligne in enumerate(script.read_text(encoding="utf-8").splitlines(), 1):
            if motif.search(ligne) and not ligne.lstrip().startswith("#"):
                messages.append(
                    f"{script.relative_to(racine)}:{n}: « docker run » interdit hors de "
                    "outils/securite/lib.sh"
                )
    return messages


def main():
    racine = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    messages = verifier(racine)
    for m in messages:
        print(m)
    if messages:
        print(f"ÉCHEC : {len(messages)} problème(s) d'épinglage.")
        return 1
    print("OK : actions, images et outils épinglés ; aucune tâche requise conditionnelle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
