#!/usr/bin/env bash
# Démonstration des blocages (SC-002, SC-003 ; research.md R8). À lancer par Alexandre, après
# la mise en service de la protection de main (regles_github.py appliquer).
#
# Usage : outils/securite/demonstration.sh [--tenter-push-main]
#   1. vérifie la protection de main (regles_github.py verifier) : arrêt si elle n'est pas conforme ;
#   2. crée une branche jetable avec un défaut par famille de contrôle, ouvre une PR brouillon,
#      attend les contrôles et vérifie que les 6 contrôles requis échouent et que la PR est bloquée
#      (aucune tentative de merge : seul l'état « BLOCKED » est lu) ;
#   3. avec --tenter-push-main seulement : tente un push direct puis un force-push sur main et
#      vérifie qu'ils sont refusés (si la protection est conforme, main ne peut pas être modifiée) ;
#   4. ferme la PR et supprime la branche jetable, même en cas d'erreur.
# Le faux secret est généré à l'exécution (jamais écrit dans le dépôt) ; s'il est refusé à
# l'envoi par la push protection, c'est le comportement attendu (US3) et il est retiré de la PR.

set -uo pipefail

ici="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
racine="$(git -C "$ici" rev-parse --show-toplevel)"
cd "$racine" || exit 2

tenter_push_main=""
[[ "${1:-}" == "--tenter-push-main" ]] && tenter_push_main=1

branche="demonstration-blocages-$(date +%Y%m%d%H%M%S)"
depart="$(git rev-parse --abbrev-ref HEAD)"
pr=""
bilan=()
echec=0

note() {
  bilan+=("$1 : $2")
  [[ "$2" == OK* ]] || echec=1
}

# shellcheck disable=SC2329 # appelée par trap EXIT
nettoyer() {
  if [[ -n "$pr" ]]; then
    gh pr close "$pr" --delete-branch >/dev/null 2>&1 || true
  fi
  git push origin --delete "$branche" >/dev/null 2>&1 || true
  git checkout -q "$depart" 2>/dev/null || true
  git branch -D "$branche" >/dev/null 2>&1 || true
}
trap nettoyer EXIT

if ! python3 "$ici/regles_github.py" verifier; then
  echo "ARRÊT : la protection de main n'est pas conforme ; aucune démonstration lancée." >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ARRÊT : arbre de travail non propre." >&2
  exit 2
fi

git fetch -q origin main
git checkout -q -b "$branche" origin/main

# --- Un défaut par famille -----------------------------------------------------------------
mkdir -p demonstration infra/demonstration openwebui
cat > demonstration/defauts.py <<'EOF'
import subprocess,sys
def lancer():
    subprocess.run(sys.argv[1], shell=True)
EOF
cat > tests/test_demonstration.py <<'EOF'
import unittest


class TestDemonstration(unittest.TestCase):
    def test_echoue(self):
        self.assertEqual(1, 2)
EOF
cat > infra/demonstration/main.tf <<'EOF'
resource "scaleway_instance_security_group" "demo" {
  inbound_default_policy = "accept"
  inbound_rule {
    action = "accept"
    port   = 22
  }
}
EOF
image_vulnerable="python:3.8.0-slim"
empreinte="$(docker buildx imagetools inspect "$image_vulnerable" --format '{{json .Manifest.Digest}}' | tr -d '"')"
cat > openwebui/compose.yaml <<EOF
services:
  demonstration:
    image: ${image_vulnerable}@${empreinte}
EOF
git add demonstration tests/test_demonstration.py infra openwebui
git -c commit.gpgsign=false commit -qm "Démonstration jetable : un défaut par famille de contrôle"

# Faux secret généré à l'exécution, dans un commit séparé.
python3 - > demonstration/config.ini <<'EOF'
import secrets, string
alphabet = string.ascii_uppercase + string.digits
print("aws_access_key_id = AKIA" + "".join(secrets.choice(alphabet) for _ in range(16)))
print("aws_secret_access_key = " + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40)))
EOF
git add demonstration/config.ini
git -c commit.gpgsign=false commit -qm "Démonstration jetable : faux secret"

if git push -q -u origin "$branche" 2>/dev/null; then
  note "secrets (envoi)" "OK (à confirmer sur la PR) : accepté à l'envoi, le contrôle secrets doit le bloquer"
else
  note "secrets (envoi)" "OK : refusé par la push protection"
  git reset -q --hard HEAD~1
  git push -q -u origin "$branche" || { echo "ÉCHEC : envoi de la branche impossible" >&2; exit 3; }
  "$ici/controle.sh" secrets >/dev/null 2>&1 || true
fi

pr="$(gh pr create --draft --base main --head "$branche" \
  --title "Démonstration jetable des blocages (ne pas merger)" \
  --body "PR jetable ouverte par outils/securite/demonstration.sh ; fermée automatiquement.")"
echo "PR de démonstration : $pr"
gh pr checks "$pr" --watch --interval 20 >/dev/null 2>&1 || true

for controle in lint sast-codeql sca iac secrets tests; do
  etat="$(gh pr checks "$pr" --json name,state --jq ".[] | select(.name == \"$controle\") | .state")"
  if [[ "$etat" == "FAILURE" ]]; then
    note "$controle" "OK : en échec comme attendu"
  else
    note "$controle" "INATTENDU : état « ${etat:-absent} »"
  fi
done

etat_merge="$(gh pr view "$pr" --json mergeStateStatus --jq .mergeStateStatus)"
if [[ "$etat_merge" == "BLOCKED" ]]; then
  note "merge d'une PR rouge" "OK : bloqué"
else
  note "merge d'une PR rouge" "INATTENDU : état « $etat_merge »"
fi

if [[ -n "$tenter_push_main" ]]; then
  if git push -q origin "HEAD:main" 2>/dev/null; then
    note "push direct sur main" "INATTENDU : accepté"
  else
    note "push direct sur main" "OK : refusé"
  fi
  if git push -q --force origin "HEAD:main" 2>/dev/null; then
    note "force-push sur main" "INATTENDU : accepté"
  else
    note "force-push sur main" "OK : refusé"
  fi
else
  note "push direct et force-push sur main" "OK : non tentés (option --tenter-push-main)"
fi

echo ""
echo "=== Bilan de la démonstration ==="
printf '%s\n' "${bilan[@]}"
exit "$echec"
