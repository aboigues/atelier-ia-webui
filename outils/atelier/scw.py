"""Appels à Scaleway (toujours avec --profile telemach). La clé n'est jamais journalisée."""

import json
import subprocess
import urllib.request

PROFIL = ["--profile", "telemach"]
ETIQUETTE = "atelier-session"
ZONE_DNS = "atelier.telemach-learning.fr"


class ErreurScaleway(RuntimeError):
    """Scaleway injoignable ou profil telemach absent (code de sortie 3)."""


def _scw(*arguments, json_attendu=True):
    """Lance `scw --profile telemach ...` (liste d'arguments, sans shell)."""
    commande = ["scw", *PROFIL, *arguments]
    if json_attendu:
        commande += ["-o", "json"]
    resultat = subprocess.run(  # noqa: S603 (commande fixe, sans shell)
        commande, capture_output=True, text=True, check=False
    )
    if resultat.returncode != 0:
        # Message d'erreur seul : jamais la sortie standard, qui peut contenir un secret.
        raise ErreurScaleway(f"scw {arguments[0]} {arguments[1]} : {resultat.stderr.strip()[:300]}")
    return json.loads(resultat.stdout or "null") if json_attendu else resultat.stdout.strip()


def cle_secrete():
    return _scw("config", "get", "secret-key", json_attendu=False)


def projet():
    return _scw("config", "get", "default-project-id", json_attendu=False)


def url_api_modeles():
    return f"https://api.scaleway.ai/{projet()}/v1"


def modeles_disponibles():
    requete = urllib.request.Request(
        url_api_modeles() + "/models", headers={"Authorization": f"Bearer {cle_secrete()}"}
    )
    with urllib.request.urlopen(requete, timeout=30) as reponse:  # noqa: S310 (URL https fixe)
        return {m["id"] for m in json.load(reponse)["data"]}


def prix_horaire(type_instance, zone="fr-par-1"):
    """Prix horaire en euros d'un type d'instance, lu en direct chez Scaleway."""
    for t in _scw("instance", "server-type", "list", f"zone={zone}") or []:
        if t["name"] == type_instance:
            prix = t["hourly_price"]
            if isinstance(prix, dict):
                return prix.get("units", 0) + prix.get("nanos", 0) / 1e9
            return float(prix)
    raise ErreurScaleway(f"type d'instance « {type_instance} » inconnu en {zone}")


def inventaire(session_id):
    """Ressources restantes portant l'étiquette atelier-session=<id> (ou rattachées à la session)."""
    tag = f"{ETIQUETTE}={session_id}"
    restes = []
    for type_, args in (
        ("instance", ("instance", "server", "list", f"tags.0={tag}", "zone=fr-par-1")),
        ("volume", ("block", "volume", "list", "zone=fr-par-1")),
        ("ip", ("instance", "ip", "list", f"tags.0={tag}", "zone=fr-par-1")),
        ("groupe de sécurité", ("instance", "security-group", "list", "zone=fr-par-1")),
        ("application IAM", ("iam", "application", "list", f"name=atelier-{session_id}")),
    ):
        for r in _scw(*args) or []:
            if type_ in ("volume", "groupe de sécurité") and tag not in (r.get("tags") or []):
                continue
            restes.append((type_, r.get("id"), r.get("name")))
    for r in _scw("dns", "record", "list", ZONE_DNS, f"name={session_id}") or []:
        restes.append(("enregistrement DNS", r.get("id"), r.get("name")))
    return restes
