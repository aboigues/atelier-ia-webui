"""Démo « IA et analyse de plans » : 5 scénarios sur des documents fictifs.

Modèle : Mistral via Scaleway Generative APIs (hébergement Paris), API compatible OpenAI.
La clé est lue à l'exécution dans le profil `scw --profile telemach` : rien n'est stocké ici.

Usage :
    python3 demo.py 1            # un scénario (1 à 5), résultat affiché et enregistré
    python3 demo.py tout         # les 5 scénarios (pour préparer les résultats de secours)
    python3 demo.py 2 --modele mistral-medium-3.5-128b

Scénarios :
    1. Extraction : cartouche, nomenclature et portes du plan indice B -> tableau
    2. Cohérence : plan indice B / extrait de CCTP / liste d'équipements du négoce
    3. Indices : différences entre les indices A et B, et modifications non déclarées au cartouche
    4. Maquette IFC : question en langage courant sur les espaces du bloc
    5. Limite : demander une cote mesurée sur le plan (ce que l'IA ne sait pas faire de
       façon fiable)
"""

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
DOCS = ICI / "documents"
RES = ICI / "resultats"
MODELE = (
    "mistral-medium-3.5-128b"  # plus rapide mais moins fiable : mistral-small-3.2-24b-instruct-2506
)

SYSTEME = (
    "Tu es un assistant pour le bureau d'études d'un intégrateur de blocs opératoires. "
    "Tu réponds en français, de façon factuelle et concise, en tableaux Markdown quand c'est "
    "utile. "
    "Tu ne dis que ce que tu lis dans les documents fournis ; si une information n'y figure pas "
    "ou n'est pas lisible, tu l'écris explicitement au lieu de la deviner. "
    "Pas d'emoji ni de pictogramme : écris oui ou non."
)


def scw(champ):
    # Commande fixe, arguments en liste, sans shell : aucune entrée non maîtrisée.
    return subprocess.run(  # noqa: S603
        ["scw", "--profile", "telemach", "config", "get", champ],  # noqa: S607 (scw du PATH)
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def image(nom):
    b64 = base64.b64encode((DOCS / nom).read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def texte(s):
    return {"type": "text", "text": s}


def lire(nom):
    return (DOCS / nom).read_text(encoding="utf-8")


def espaces_ifc():
    """Lit les espaces et leurs propriétés dans la maquette IFC (sans bibliothèque externe)."""
    src = lire("maquette-bloc.ifc")
    ent = dict(re.findall(r"^#(\d+)=(.+);$", src, flags=re.M))

    def dec(s):
        return re.sub(r"\\X2\\([0-9A-F]{4})\\X0\\", lambda m: chr(int(m.group(1), 16)), s)

    espaces = {}
    for k, v in ent.items():
        if v.startswith("IFCSPACE("):
            champs = [c.replace("''", "'") for c in re.findall(r"'((?:[^']|'')*)'", v)]
            espaces[k] = {"code": champs[1], "nom": dec(champs[2])}
    for v in ent.values():
        if not v.startswith("IFCRELDEFINESBYPROPERTIES("):
            continue
        cibles, pset = re.search(r"\(([#\d,]+)\),#(\d+)\)$", v).groups()
        props = re.search(r"\(([#\d,]+)\)\)$", ent[pset]).group(1)
        for c in cibles.split(","):
            for p in props.split(","):
                nom, val = re.match(
                    r"IFCPROPERTYSINGLEVALUE\('(\w+)',\$,\w+\((.*)\),\$\)", ent[p[1:]]
                ).groups()
                val = {".T.": True, ".F.": False}.get(val, val.strip("'"))
                espaces[c[1:]][nom] = val
    return list(espaces.values())


SCENARIOS = {
    1: (
        "Extraction du cartouche et de la nomenclature",
        lambda: [
            texte(
                "Voici un plan d'aménagement de salle d'opération. Extrais : (1) le cartouche "
                "(maître d'ouvrage, opération, lot, n° de plan, phase, échelle, indice en vigueur "
                "et "
                "sa date) ; (2) la nomenclature des équipements (repère, désignation, quantité) ; "
                "(3) la liste des portes. Présente le tout en tableaux."
            ),
            image("plan-salle3-indB.png"),
        ],
    ),
    2: (
        "Cohérence plan / CCTP / liste d'équipements",
        lambda: [
            texte(
                "Compare le plan (indice B, image), l'extrait de CCTP et la liste d'équipements du "
                "négoce ci-dessous. Dresse un tableau des écarts : sujet, ce que dit le plan, ce "
                "que "
                "dit le CCTP, ce que dit la liste, gravité (bloquant / à vérifier). Termine par "
                "les "
                "points que tu ne peux pas vérifier à partir de ces documents.\n\n"
                "=== EXTRAIT DE CCTP ===\n"
                + lire("cctp-extrait-lot-salles-propres.txt")
                + "\n=== LISTE D'ÉQUIPEMENTS (CSV) ===\n"
                + lire("liste-equipements-salle3.csv")
            ),
            image("plan-salle3-indB.png"),
        ],
    ),
    3: (
        "Différences entre deux indices",
        lambda: [
            texte(
                "Voici deux indices du même plan : d'abord l'indice A, puis l'indice B. Liste "
                "toutes "
                "les différences (équipements, portes, plafond soufflant, nomenclature, "
                "cartouche). "
                "Indique ensuite, pour chacune, si elle est déclarée dans le tableau des indices "
                "du "
                "cartouche de l'indice B. Signale clairement les modifications non déclarées."
            ),
            image("plan-salle3-indA.png"),
            image("plan-salle3-indB.png"),
        ],
    ),
    4: (
        "Interroger une maquette IFC en langage courant",
        lambda: [
            texte(
                "Voici les espaces d'une maquette IFC de bloc opératoire, avec leurs propriétés "
                "(extraites automatiquement du fichier) :\n"
                + json.dumps(espaces_ifc(), ensure_ascii=False, indent=1)
                + "\n\nQuestion : quelles salles d'opération n'ont pas de plafond soufflant ? "
                "Y a-t-il d'autres valeurs qui détonnent entre les quatre salles d'opération ?"
            ),
        ],
    ),
    5: (
        "Limite : mesurer une cote sur le plan",
        lambda: [
            texte(
                "Sur ce plan, à quelle distance en mètres le bras chirurgien E02 se trouve-t-il de "
                "l'axe de la table d'opération E04 ? Le CCTP impose moins de 2,00 m : est-ce "
                "conforme ?"
            ),
            image("plan-salle3-indB.png"),
        ],
    ),
}


def appel(modele, contenu):
    cle, projet = scw("secret-key"), scw("default-project-id")
    corps = json.dumps(
        {
            "model": modele,
            "temperature": 0.1,
            "max_tokens": 2000,
            "messages": [
                {"role": "system", "content": SYSTEME},
                {"role": "user", "content": contenu},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        f"https://api.scaleway.ai/{projet}/v1/chat/completions",
        data=corps,
        headers={"Authorization": f"Bearer {cle}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    # URL construite sur https://api.scaleway.ai, jamais fournie par l'utilisateur.
    with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310
        d = json.load(r)
    return d["choices"][0]["message"]["content"], time.time() - t0


def lancer(n, modele):
    titre, construire = SCENARIOS[n]
    print(f"\n=== Scénario {n} : {titre} ({modele}) ===\n", flush=True)
    rep, duree = appel(modele, construire())
    print(rep)
    print(f"\n[{duree:.0f} s]")
    RES.mkdir(exist_ok=True)
    (RES / f"scenario-{n}.md").write_text(
        f"# Scénario {n} : {titre}\n\nModèle : `{modele}` (Scaleway, Paris) - durée : {duree:.0f} "
        "s\n\n"
        f"{rep}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", help="1 à 5, ou « tout »")
    ap.add_argument("--modele", default=MODELE)
    a = ap.parse_args()
    for n in SCENARIOS if a.scenario == "tout" else [int(a.scenario)]:
        try:
            lancer(n, a.modele)
        except Exception as e:  # noqa: BLE001
            print(f"Échec du scénario {n} : {e}", file=sys.stderr)
