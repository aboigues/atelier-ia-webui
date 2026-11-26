#!/usr/bin/env python3
"""Verdict des vulnérabilités trouvées par Grype (FR-007, research.md R3).

Règles, pour chaque vulnérabilité constatée (data-model.md « Vulnérabilité constatée » : gravite,
correctif) :
1. critique ou élevée AVEC correctif publié  -> bloquante, sauf exception individuelle valide ;
2. critique SANS correctif                   -> bloquante, sauf exception individuelle valide ;
3. élevée SANS correctif                     -> tolérée tant que l'exception de classe
   « elevee-sans-correctif » est valide, bloquante sinon ;
4. moyenne, faible, négligeable, inconnue    -> signalée.
La gravité « inconnue » est traitée comme moyenne. Une exception échue ne s'applique plus.

Usage : verdict_vulnerabilites.py [--rapport fichier.md] <grype.json>...
Codes : 0 aucune bloquante, 1 au moins une bloquante, 2 usage ou exceptions invalides,
3 analyse inexploitable (jamais un succès).
"""

import argparse
import datetime as dt
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

CLASSE_ELEVEE = "elevee-sans-correctif"
GRAVES = {"critical": "critique", "high": "élevée"}


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


class ErreurAnalyse(RuntimeError):
    """Résultat de Grype absent ou illisible."""


@dataclass
class Constat:
    id: str
    ids: frozenset
    gravite: str
    correctif: bool
    paquet: str
    image: str

    def libelle(self):
        etat = "correctif publié" if self.correctif else "sans correctif"
        return f"{self.id} ({self.gravite}, {etat}) : {self.paquet} dans {self.image}"


@dataclass
class Verdict:
    bloquantes: list = field(default_factory=list)
    tolerees: list = field(default_factory=list)
    signalees: list = field(default_factory=list)
    avertissements: list = field(default_factory=list)


def depot_image(reference):
    """« registry:ghcr.io/a/b:tag@sha256:... » -> « ghcr.io/a/b » ;
    « file:/sortie/bin/trivy » (binaire d'outil) -> « binaire:trivy »."""
    if reference.startswith(("file:", "/")):
        return "binaire:" + reference.rsplit("/", 1)[-1]
    ref = reference.split(":", 1)[1] if reference.startswith("registry:") else reference
    ref = ref.split("@", 1)[0]
    dernier = ref.rsplit("/", 1)[-1]
    if ":" in dernier:
        ref = ref[: len(ref) - len(dernier)] + dernier.split(":", 1)[0]
    return ref


def lire_grype(fichier):
    try:
        donnees = json.loads(Path(fichier).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erreur:
        raise ErreurAnalyse(f"{fichier} illisible : {erreur}") from erreur
    if not isinstance(donnees, dict) or "matches" not in donnees:
        raise ErreurAnalyse(f"{fichier} : pas de résultat Grype (clé « matches » absente)")
    # Image : « target » est un objet ; fichier (binaire d'outil) : « target » est un chemin.
    cible = (donnees.get("source") or {}).get("target", "?")
    image = depot_image(cible.get("userInput", "?") if isinstance(cible, dict) else str(cible))
    constats = []
    for m in donnees["matches"] or []:
        vuln = m.get("vulnerability", {})
        ids = {vuln.get("id", "?")} | {r.get("id") for r in m.get("relatedVulnerabilities", [])}
        gravite = (vuln.get("severity") or "unknown").lower()
        correctif = vuln.get("fix", {}).get("state") == "fixed"
        paquet = (
            f"{m.get('artifact', {}).get('name', '?')} {m.get('artifact', {}).get('version', '')}"
        )
        constats.append(
            Constat(vuln.get("id", "?"), frozenset(ids), gravite, correctif, paquet.strip(), image)
        )
    return constats


def juger(fichiers, exceptions, jour):
    verdict = Verdict()
    valides = [e for e in exceptions if e.etat(jour) == "valide"]
    for e in exceptions:
        if e.etat(jour) == "echue" and e.type in ("vulnerabilite", "classe"):
            verdict.avertissements.append(
                f"Exception échue (réexamen dû le {e.reexamen_le}) : {e.id}, ne s'applique plus"
            )
    classe_valide = any(e.type == "classe" and e.id == CLASSE_ELEVEE for e in valides)

    for fichier in fichiers:
        for c in lire_grype(fichier):
            individuelle = any(
                e.type == "vulnerabilite"
                and e.id in c.ids
                and (c.image == e.portee or c.image.startswith(e.portee + "/"))
                for e in valides
            )
            if c.gravite not in GRAVES:
                verdict.signalees.append(c)
            elif individuelle:
                verdict.tolerees.append(c)
            elif c.gravite == "high" and not c.correctif and classe_valide:
                verdict.tolerees.append(c)
            else:
                verdict.bloquantes.append(c)
    return verdict


def rapport(verdict):
    lignes = ["## Vulnérabilités des composants tiers", ""]
    lignes.append(
        f"Bloquantes : {len(verdict.bloquantes)} ; Tolérées : {len(verdict.tolerees)} ; "
        f"signalées (moyennes et moins) : {len(verdict.signalees)}"
    )
    for titre, liste in (("Bloquantes", verdict.bloquantes), ("Tolérées", verdict.tolerees)):
        if liste:
            lignes += ["", f"### {titre}", ""]
            lignes += [f"- {c.libelle()}" for c in sorted(liste, key=lambda c: (c.image, c.id))]
    if verdict.avertissements:
        lignes += ["", "### Avertissements", ""] + [f"- {a}" for a in verdict.avertissements]
    return "\n".join(lignes) + "\n"


def main(argv=None):
    parseur = argparse.ArgumentParser(description="Verdict des vulnérabilités (Grype).")
    parseur.add_argument("--rapport", type=Path, help="fichier Markdown à écrire")
    parseur.add_argument("fichiers", nargs="+", type=Path)
    args = parseur.parse_args(argv)
    ex = _module_exceptions()
    jour = dt.date.today()
    try:
        exceptions = ex.charger(jour)
    except ex.ErreurExceptions as erreur:
        print(f"ÉCHEC : securite/exceptions.toml invalide : {erreur}")
        return 2
    try:
        verdict = juger(args.fichiers, exceptions, jour)
    except ErreurAnalyse as erreur:
        print(f"ÉCHEC : {erreur}")
        return 3
    texte = rapport(verdict)
    print(texte)
    if args.rapport:
        args.rapport.write_text(texte, encoding="utf-8")
    if verdict.bloquantes:
        print(f"ÉCHEC : {len(verdict.bloquantes)} vulnérabilité(s) bloquante(s).")
        return 1
    print("OK : aucune vulnérabilité bloquante.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
