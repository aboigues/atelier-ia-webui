#!/usr/bin/env python3
"""Politiques de sécurité propres au projet pour l'infrastructure en code (research.md R2).

Les analyseurs du marché couvrent peu Scaleway ; ces règles complètent Trivy :
- groupe de sécurité : politique d'entrée par défaut « drop », entrée limitée aux ports 80 et
  443, ni port 22 ni plage de ports ;
- étiquette `atelier-session` sur toute ressource Scaleway qui accepte des étiquettes ;
- clé d'API IAM avec date d'expiration (`expires_at`) ;
- politique IAM limitée à `GenerativeApisModelAccess` ;
- Compose : aucune image sans empreinte, aucun `privileged`, Open WebUI publié sur 127.0.0.1
  seulement ;
- cloud-init : toute image citée est épinglée par empreinte.

Analyse textuelle, bibliothèque standard uniquement. Usage : politiques_iac.py [racine]
Codes : 0 conforme, 1 non conforme.
"""

import re
import sys
from pathlib import Path

ETIQUETABLES = {
    "scaleway_instance_ip",
    "scaleway_instance_security_group",
    "scaleway_instance_server",
    "scaleway_iam_application",
    "scaleway_iam_policy",
}
PORTS_AUTORISES = {80, 443}
PERMISSIONS_AUTORISEES = {"GenerativeApisModelAccess"}
RE_RESSOURCE = re.compile(r'^\s*resource\s+"([\w-]+)"\s+"([\w-]+)"\s*\{', re.M)
RE_IMAGE_CITEE = re.compile(
    r"(?:image:|docker pull|docker run)\s+['\"]?([\w./-]+:[\w.-]+(?:@sha256:[0-9a-f]{64})?)"
)


def _corps(texte, debut):
    """Renvoie le texte entre l'accolade ouvrante située avant `debut` et sa fermante."""
    profondeur, i = 1, debut
    while i < len(texte) and profondeur:
        profondeur += {"{": 1, "}": -1}.get(texte[i], 0)
        i += 1
    return texte[debut : i - 1]


def _sous_blocs(corps, nom):
    return [_corps(corps, m.end()) for m in re.finditer(rf"\b{nom}\s*\{{", corps)]


def verifier_terraform(texte, fichier):
    messages = []
    for m in RE_RESSOURCE.finditer(texte):
        type_, nom = m.group(1), m.group(2)
        ligne = texte.count("\n", 0, m.start()) + 1
        lieu = f"{fichier}:{ligne}: {type_}.{nom}"
        corps = _corps(texte, m.end())

        if type_ in ETIQUETABLES and "atelier-session" not in corps:
            messages.append(f"{lieu} : étiquette « atelier-session » absente")

        if type_ == "scaleway_instance_security_group":
            politique = re.search(r'inbound_default_policy\s*=\s*"(\w+)"', corps)
            if not politique or politique.group(1) != "drop":
                messages.append(f"{lieu} : inbound_default_policy doit valoir « drop »")
            for regle in _sous_blocs(corps, "inbound_rule"):
                if "port_range" in regle:
                    messages.append(f"{lieu} : plage de ports interdite en entrée")
                for port in map(int, re.findall(r"\bport\s*=\s*(\d+)", regle)):
                    if port not in PORTS_AUTORISES:
                        messages.append(
                            f"{lieu} : port {port} ouvert en entrée (80 et 443 seulement)"
                        )

        if type_ == "scaleway_iam_api_key" and not re.search(r"\bexpires_at\s*=", corps):
            messages.append(f"{lieu} : clé d'API sans expires_at")

        if type_ == "scaleway_iam_policy":
            for liste in re.findall(r"permission_set_names\s*=\s*\[([^\]]*)\]", corps):
                for perm in re.findall(r'"([^"]+)"', liste):
                    if perm not in PERMISSIONS_AUTORISEES:
                        messages.append(f"{lieu} : permission « {perm} » interdite")
    return messages


def verifier_compose(texte, fichier):
    messages, service, dans_ports = [], None, False
    for n, ligne in enumerate(texte.splitlines(), 1):
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        retrait = len(ligne) - len(ligne.lstrip(" "))
        contenu = ligne.strip()
        if retrait == 2 and contenu.endswith(":"):
            service, dans_ports = contenu[:-1], False
            continue
        if retrait == 4:
            dans_ports = contenu.startswith("ports:")
        lieu = f"{fichier}:{n}"
        if contenu.startswith("image:") and "@sha256:" not in contenu:
            messages.append(f"{lieu} : image sans empreinte sha256 ({contenu[6:].strip()})")
        if re.match(r"privileged:\s*true", contenu):
            messages.append(f"{lieu} : « privileged: true » interdit")
        if dans_ports and service == "openwebui" and contenu.startswith("-"):
            port = contenu.lstrip("- ").strip("'\"")
            if not port.startswith("127.0.0.1:"):
                messages.append(
                    f"{lieu} : Open WebUI doit être publié sur 127.0.0.1 seulement ({port})"
                )
    return messages


def verifier_cloud_init(texte, fichier):
    messages = []
    for n, ligne in enumerate(texte.splitlines(), 1):
        for image in RE_IMAGE_CITEE.findall(ligne):
            if "@sha256:" not in image:
                messages.append(f"{fichier}:{n} : image sans empreinte sha256 ({image})")
    return messages


def verifier(racine):
    racine = Path(racine)
    messages = []
    for tf in sorted(racine.glob("infra/**/*.tf")):
        messages += verifier_terraform(tf.read_text(encoding="utf-8"), tf.relative_to(racine))
    for ci in sorted(racine.glob("infra/**/*cloud-init*")):
        messages += verifier_cloud_init(ci.read_text(encoding="utf-8"), ci.relative_to(racine))
    for compose in sorted(racine.glob("openwebui/compose*.y*ml")):
        messages += verifier_compose(
            compose.read_text(encoding="utf-8"), compose.relative_to(racine)
        )
    return messages


def main():
    racine = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    messages = verifier(racine)
    for m in messages:
        print(m)
    if messages:
        print(f"ÉCHEC : {len(messages)} écart(s) aux politiques IaC du projet.")
        return 1
    print("OK : politiques IaC du projet respectées (ou aucune infrastructure à analyser).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
