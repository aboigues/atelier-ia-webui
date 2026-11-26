"""Comptes d'une session (data-model.md Compte) et fiches d'identifiants (hors dépôt).

Compte.courriel : prenom.nom@<id>.atelier, sans accent, suffixe numérique en cas de doublon ;
aucune adresse réelle. Compte.mot_de_passe : 4 mots tirés par `secrets` et un nombre.
Compte.role : formateur (admin Open WebUI) ou participant (user).
"""

import os
import re
import secrets
import unicodedata
from dataclasses import dataclass
from pathlib import Path

MOTS = (
    "abeille acier agrume aile algue amande ancre angle anis arbre arche argile atlas aube avion "
    "baie balcon bambou banane barque bassin baton bergamote bison blason bocal bois bouleau "
    "boussole branche brise brume bulle cactus cadran caillou calme camion canard canal cape "
    "carton castor cedre cerise chalet chameau champ chanvre chardon chene cheval cigale cime "
    "citron clairiere clou coquille corail corde coton crayon criquet cuivre cygne dalle dauphin "
    "delta desert digue dune ebene ecorce ecume eglantier encre epice erable escale etoile etang "
    "falaise fanal fenouil fer feuille figue flamant fleuve flute foret fougere fourmi frene "
    "fruit galet garance gazelle genet girafe glacier gland goeland granit grenade grotte guepe "
    "hamac hamster harpe herbe heron hibou houx hublot iceberg ile indigo iris jade jardin jasmin "
    "jonc kayak kiwi lagune laine lama lampe lande lanterne laurier lavande lezard lierre lilas "
    "lin lion loutre lune lynx magnolia mais manche mangue marais marbre mesange meteore miel "
    "moulin mousse muguet myrtille nacre navire neige nuage oasis ocean olive ombre onde orage "
    "orchidee orge ours paille palme panda papyrus pastel pavot peche pelican perle phare pin "
    "pivoine plage plume pollen pomme pont prairie prisme puits quartz radeau raisin renard "
    "rocher roseau rubis ruche sable safran sapin saule seigle sentier silex soleil source sureau "
    "tapis theiere tigre tilleul tomate torrent toucan tournesol trefle tulipe vague vallee "
    "vanille verger violette volcan voile zebre zinc"
).split()


@dataclass(frozen=True)
class Compte:
    prenom: str
    nom: str
    courriel: str
    mot_de_passe: str
    role: str  # "formateur" ou "participant"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip()

    @property
    def role_openwebui(self):
        return "admin" if self.role == "formateur" else "user"


def _simplifier(texte):
    sans_accent = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sans_accent.lower()).strip("-")


def courriel(prenom, nom, session_id, suffixe=""):
    return f"{_simplifier(prenom)}.{_simplifier(nom)}{suffixe}@{session_id}.atelier"


def mot_de_passe():
    mots = [secrets.choice(MOTS) for _ in range(4)]
    return "-".join(mots + [str(secrets.randbelow(90) + 10)])


def generer(participants, session_id):
    vus, comptes = {}, []
    for p in participants:
        base = courriel(p.prenom, p.nom, session_id)
        vus[base] = vus.get(base, 0) + 1
        suffixe = f"-{vus[base]}" if vus[base] > 1 else ""
        comptes.append(
            Compte(
                p.prenom,
                p.nom,
                courriel(p.prenom, p.nom, session_id, suffixe),
                mot_de_passe(),
                "participant",
            )
        )
    return comptes


def compte_formateur(session_id):
    return Compte("Formateur", "", f"formateur@{session_id}.atelier", mot_de_passe(), "formateur")


def ecrire_fiches(dossier, comptes, client, adresse, lien_acces):
    """Une fiche texte par compte, prête à imprimer (contracts/fichiers-session.md), en 0600."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    os.chmod(dossier, 0o700)
    for c in comptes:
        nom_fichier = (
            "formateur.txt"
            if c.role == "formateur"
            else f"{_simplifier(c.prenom)}-{_simplifier(c.nom)}"
        )
        if c.role != "formateur":
            n = 2
            base = nom_fichier
            while (dossier / f"{nom_fichier}.txt").exists():
                nom_fichier, n = f"{base}-{n}", n + 1
            nom_fichier += ".txt"
        texte = (
            f"Atelier IA et analyse de plans - {client}\n"
            f"1. Ouvrir une fois ce lien d'accès : {lien_acces}\n"
            f"2. Adresse : {adresse}\n"
            f"   Identifiant : {c.courriel}\n"
            f"   Mot de passe : {c.mot_de_passe}\n"
            "Les documents déposés sont supprimés à la fin de la session.\n"
        )
        chemin = dossier / nom_fichier
        descripteur = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descripteur, "w", encoding="utf-8") as f:
            f.write(texte)
