"""
title: Conversion IFC
description: Réduit une maquette IFC jointe à un tableau des espaces et de leurs propriétés ;
  avertit quand un PDF semble être un plan vectoriel.
version: 1.0.0
"""

# Filtre Open WebUI (contracts/filtre-ifc.md). Un seul fichier, bibliothèque standard, aucun
# appel réseau. Les fonctions pures (espaces_ifc, tableau_markdown, pdf_texte_pauvre) sont
# testées hors d'Open WebUI (tests/test_filtre_ifc.py).

import os
import re

try:  # Open WebUI fournit pydantic ; les tests tournent sans.
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover

    class BaseModel:
        def __init__(self, **valeurs):
            for nom, valeur in type(self).__dict__.items():
                if not nom.startswith("_") and not callable(valeur):
                    setattr(self, nom, valeurs.get(nom, valeur))

    def Field(default=None, **_):  # noqa: N802
        return default


class ErreurIFC(ValueError):
    """Maquette illisible ou trop volumineuse."""


RE_ENTITE = re.compile(r"^#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*)\)$", re.S)
RE_X2 = re.compile(r"\\X2\\((?:[0-9A-Fa-f]{4})+)\\X0\\")
RE_X = re.compile(r"\\X\\([0-9A-Fa-f]{2})")


def _instructions(texte):
    """Découpe la section DATA en instructions terminées par « ; » hors des chaînes."""
    debut = texte.find("DATA;")
    if (
        not texte.lstrip().startswith("ISO-10303-21")
        or debut < 0
        or "END-ISO-10303-21" not in texte
    ):
        raise ErreurIFC(
            "fichier IFC illisible : en-tête ou fin de fichier absent (fichier tronqué ?)"
        )
    courant, dans_chaine = [], False
    for c in texte[debut + 5 :]:
        if c == "'":
            dans_chaine = not dans_chaine
        if c == ";" and not dans_chaine:
            instruction = "".join(courant).strip()
            if instruction == "ENDSEC":
                return
            yield instruction
            courant = []
        else:
            courant.append(c)
    raise ErreurIFC("fichier IFC illisible : section DATA non terminée")


def _arguments(texte):
    """Sépare les arguments de premier niveau (virgules hors chaînes et parenthèses)."""
    args, courant, profondeur, dans_chaine = [], [], 0, False
    for c in texte:
        if c == "'":
            dans_chaine = not dans_chaine
        elif not dans_chaine and c == "(":
            profondeur += 1
        elif not dans_chaine and c == ")":
            profondeur -= 1
        if c == "," and profondeur == 0 and not dans_chaine:
            args.append("".join(courant).strip())
            courant = []
        else:
            courant.append(c)
    args.append("".join(courant).strip())
    return args


def _texte(valeur):
    if not (valeur.startswith("'") and valeur.endswith("'")):
        return ""
    s = valeur[1:-1].replace("''", "'")
    s = RE_X2.sub(
        lambda m: "".join(
            chr(int(m.group(1)[i : i + 4], 16)) for i in range(0, len(m.group(1)), 4)
        ),
        s,
    )
    return RE_X.sub(lambda m: bytes([int(m.group(1), 16)]).decode("latin-1"), s)


def _valeur(brut):
    m = re.match(r"^[A-Z0-9_]+\((.*)\)$", brut.strip(), re.S)
    v = (m.group(1) if m else brut).strip()
    if v in (".T.", ".F.", ".U."):
        return {".T.": "oui", ".F.": "non", ".U.": "inconnu"}[v]
    if v.startswith("'"):
        return _texte(v)
    try:
        nombre = float(v)
    except ValueError:
        return v
    return str(int(nombre)) if nombre.is_integer() else str(nombre)


def _references(liste):
    return re.findall(r"#(\d+)", liste)


def espaces_ifc(texte, espaces_max=2000):
    """Espaces IFC et leurs propriétés simples, triés par code (data-model.md)."""
    entites = {}
    for instruction in _instructions(texte):
        m = RE_ENTITE.match(instruction)
        if m and m.group(2) in (
            "IFCSPACE",
            "IFCPROPERTYSINGLEVALUE",
            "IFCPROPERTYSET",
            "IFCRELDEFINESBYPROPERTIES",
        ):
            entites[m.group(1)] = (m.group(2), m.group(3))
    espaces = {}
    for num, (type_, corps) in entites.items():
        if type_ == "IFCSPACE":
            a = _arguments(corps)
            nom = _texte(a[7]) if len(a) > 7 else ""
            espaces[num] = {
                "code": _texte(a[2]),
                "nom": nom or (_texte(a[3]) if len(a) > 3 else ""),
            }
    if len(espaces) > espaces_max:
        raise ErreurIFC(
            f"maquette trop volumineuse : {len(espaces)} espaces (limite {espaces_max})"
        )
    for type_, corps in entites.values():
        if type_ != "IFCRELDEFINESBYPROPERTIES":
            continue
        a = _arguments(corps)
        pset = entites.get(_references(a[-1])[0]) if _references(a[-1]) else None
        if not pset or pset[0] != "IFCPROPERTYSET":
            continue
        proprietes = {}
        for ref in _references(_arguments(pset[1])[4]):
            p = entites.get(ref)
            if p and p[0] == "IFCPROPERTYSINGLEVALUE":
                pa = _arguments(p[1])
                proprietes[_texte(pa[0])] = _valeur(pa[2])
        for cible in _references(a[4]):
            if cible in espaces:
                espaces[cible].update(proprietes)
    return sorted(espaces.values(), key=lambda e: e["code"])


def tableau_markdown(espaces):
    proprietes = sorted({k for e in espaces for k in e} - {"code", "nom"})
    colonnes = ["code", "nom", *proprietes]
    lignes = ["| " + " | ".join(colonnes) + " |", "|" + "---|" * len(colonnes)]
    for e in espaces:
        lignes.append("| " + " | ".join(str(e.get(c, "")) for c in colonnes) + " |")
    return "\n".join(lignes)


def pdf_texte_pauvre(contenu, pages=1):
    """Vrai si le texte extrait fait moins de 200 caractères par page (plan vectoriel probable)."""
    return len((contenu or "").strip()) < 200 * max(pages, 1)


def _nom(fichier):
    return fichier.get("name") or (fichier.get("file") or {}).get("filename") or ""


def _ajouter_au_message(body, texte):
    for message in reversed(body.get("messages", [])):
        if message.get("role") == "user":
            if isinstance(message.get("content"), list):
                message["content"].append({"type": "text", "text": texte})
            else:
                message["content"] = f"{message.get('content', '')}\n\n{texte}"
            return


class Filter:
    class Valves(BaseModel):
        taille_max_mo: int = Field(default=200, description="Taille maximale d'une maquette (Mo)")
        espaces_max: int = Field(default=2000, description="Nombre maximal d'espaces convertis")

    def __init__(self):
        self.valves = self.Valves()

    async def _fichier(self, ident):
        """Chemin local et texte extrait d'un fichier déposé (API d'Open WebUI v0.13.5)."""
        from open_webui.models.files import Files
        from open_webui.storage.provider import Storage

        fichier = await Files.get_file_by_id(ident)
        if fichier is None:
            raise ErreurIFC("fichier introuvable")
        return Storage.get_file(fichier.path), (fichier.data or {}).get("content", "")

    async def inlet(self, body, __user__=None, __event_emitter__=None):
        async def emettre(evenement):
            if __event_emitter__:
                await __event_emitter__(evenement)

        gardes = []
        for f in body.get("files") or []:
            nom = _nom(f)
            ident = f.get("id") or (f.get("file") or {}).get("id")
            if nom.lower().endswith(".ifc"):
                try:
                    chemin, _ = await self._fichier(ident)
                    if os.path.getsize(chemin) > self.valves.taille_max_mo * 1024 * 1024:
                        raise ErreurIFC(f"maquette de plus de {self.valves.taille_max_mo} Mo")
                    with open(chemin, encoding="utf-8", errors="replace") as flux:
                        espaces = espaces_ifc(flux.read(), self.valves.espaces_max)
                    tableau = tableau_markdown(espaces)
                    _ajouter_au_message(
                        body,
                        f"Tableau des espaces extrait de {nom} ({len(espaces)} espaces) :\n"
                        f"{tableau}",
                    )
                    await emettre(
                        {
                            "type": "citation",
                            "data": {
                                "document": [tableau],
                                "metadata": [{"source": nom}],
                                "source": {"name": f"Tableau des espaces ({nom})"},
                            },
                        }
                    )
                except (ErreurIFC, OSError) as erreur:
                    await emettre(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Conversion IFC impossible : {erreur}",
                                "done": True,
                            },
                        }
                    )
                continue  # jamais de STEP brut envoyé au modèle
            if nom.lower().endswith(".pdf"):
                try:
                    _, contenu = await self._fichier(ident)
                except (ErreurIFC, ImportError):
                    contenu = None
                if contenu is not None and pdf_texte_pauvre(contenu):
                    note = (
                        f"Le PDF {nom} semble être un plan vectoriel : exportez-le en PNG "
                        "pour que le modèle le lise."
                    )
                    _ajouter_au_message(body, f"Note : {note}")
                    await emettre({"type": "status", "data": {"description": note, "done": True}})
            gardes.append(f)
        body["files"] = gardes
        return body
