#!/usr/bin/env bash
# Contrôle local avant envoi (FR-014) : mêmes contrôles, outils et versions que la PR.
# Usage : outils/securite/controles-locaux.sh [--rapide]
#   --rapide : saute « sca » (Grype télécharge sa base de vulnérabilités, plusieurs minutes).
# Non reproduits en local : CodeQL et la push protection (propres à GitHub).
# Code : 0 si tous les contrôles passent, 1 sinon.

set -uo pipefail

ici="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
controles=(lint iac secrets tests sca)
if [[ "${1:-}" == "--rapide" ]]; then
  controles=(lint iac secrets tests)
elif [[ $# -gt 0 ]]; then
  echo "Usage : $0 [--rapide]" >&2
  exit 2
fi

declare -A verdict
echec=0
for c in "${controles[@]}"; do
  echo ""
  echo "=== Contrôle « $c » ==="
  if "$ici/controle.sh" "$c"; then
    verdict[$c]="OK"
  else
    verdict[$c]="ÉCHEC (code $?)"
    echec=1
  fi
done

echo ""
echo "=== Bilan (même verdict que la PR, hors CodeQL) ==="
printf '%-10s %s\n' "Contrôle" "Verdict"
for c in "${controles[@]}"; do
  printf '%-10s %s\n' "$c" "${verdict[$c]}"
done
if [[ "${1:-}" == "--rapide" ]]; then
  echo "(sca sauté : relancer sans --rapide avant de pousser une modification d'outil ou d'image)"
fi
exit "$echec"
