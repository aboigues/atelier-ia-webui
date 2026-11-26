#!/usr/bin/env bash
# Bibliothèque commune de la chaîne de contrôle (à sourcer, pas à exécuter).
# Seul endroit du dépôt autorisé à lancer `docker run` : chaque outil y est pris dans
# securite/outils.lock, figé par version et empreinte (verifier_epinglage.py le contrôle).
#
# Codes de sortie (contracts/commandes.md) : 0 succès, 1 contrôle en échec, 2 erreur d'usage ou
# de configuration, 3 outil ou service indisponible.

RACINE="$(git rev-parse --show-toplevel)"
LOCK="$RACINE/securite/outils.lock"
# Répertoire des sorties (rapports, SARIF, caches) : hors dépôt.
SORTIE="${SORTIE:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/controles-atelier}"
# Dossiers personnels et temporaires des outils : certaines images n'ont pas de /tmp
# accessible en écriture pour un utilisateur sans droits root.
mkdir -p "$SORTIE/home" "$SORTIE/tmp"
export RACINE LOCK SORTIE

# Valeur figée d'un outil (image@sha256:... ou URL#sha256=...), code 2 si absente ou non épinglée.
image_outil() {
  local nom="$1" valeur
  valeur="$(sed -n "s/^${nom}=//p" "$LOCK" | head -n 1)"
  if [[ -z "$valeur" ]]; then
    echo "ERREUR : outil « $nom » absent de securite/outils.lock" >&2
    return 2
  fi
  if [[ ! "$valeur" =~ @sha256:[0-9a-f]{64}$ && ! "$valeur" =~ \#sha256=[0-9a-f]{64}$ ]]; then
    echo "ERREUR : outil « $nom » sans empreinte sha256 dans securite/outils.lock" >&2
    return 2
  fi
  printf '%s\n' "$valeur"
}

# lancer_outil <nom> [--reseau] [--env NOM=VALEUR]... [--env NOM]... -- <arguments de l'outil>
# Dépôt monté en lecture seule sur /src, sorties sur /sortie ; réseau coupé sauf --reseau.
# `--env NOM` transmet la variable du même nom sans l'écrire sur la ligne de commande.
lancer_outil() {
  local nom="$1" reseau="none" image code
  local -a envs=()
  shift
  while [[ $# -gt 0 && "$1" != "--" ]]; do
    case "$1" in
      --reseau) reseau="bridge" ;;
      --env) envs+=(-e "$2"); shift ;;
      *) echo "ERREUR : option inconnue pour lancer_outil : $1" >&2; return 2 ;;
    esac
    shift
  done
  [[ "${1:-}" == "--" ]] && shift
  image="$(image_outil "$nom")" || return 2
  docker run --rm --network="$reseau" \
    --user "$(id -u):$(id -g)" -e HOME=/sortie/home -e TMPDIR=/sortie/tmp "${envs[@]}" \
    -v "$RACINE:/src:ro" -v "$SORTIE:/sortie" -w /src \
    "$image" "$@"
  code=$?
  # 125 : erreur du démon Docker ; 126/127 : commande introuvable dans l'image.
  if [[ $code -eq 125 || $code -eq 126 || $code -eq 127 ]]; then
    echo "ERREUR : impossible de lancer l'outil « $nom » (code Docker $code)" >&2
    return 3
  fi
  return "$code"
}

# Ajoute une ligne au résumé (GITHUB_STEP_SUMMARY en CI, sortie standard en local).
resume() {
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    printf '%s\n' "$*" >> "$GITHUB_STEP_SUMMARY"
  else
    printf '%s\n' "$*"
  fi
}
