#!/usr/bin/env bash
# Exécute un contrôle de la chaîne de sécurité (contracts/controles.md, contracts/commandes.md).
# Usage : outils/securite/controle.sh <lint|iac|secrets|sca|tests>
# Même script en CI (.github/workflows/) et en local (controles-locaux.sh) : mêmes outils, mêmes
# versions, mêmes fichiers de configuration (FR-014). Outils pris dans securite/outils.lock :
# images épinglées par empreinte (lancées par lib.sh) ou binaires officiels à somme vérifiée.
# Codes : 0 succès, 1 contrôle en échec, 2 usage ou configuration, 3 outil indisponible.

set -uo pipefail

# shellcheck source=outils/securite/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$RACINE" || exit 2

CODE=0
EN_CI="${GITHUB_ACTIONS:-}"
# Binaires d'outils officiels, tels que listés dans securite/outils.lock.
BINAIRES=(actionlint tflint osv-scanner trufflehog trivy opentofu)

# etape <libellé> <commande...> : exécute, journalise, et reporte le verdict dans le résumé.
etape() {
  local libelle="$1" journal code
  shift
  journal="$SORTIE/journal-$(echo "$libelle" | tr -c 'a-zA-Z0-9' '-').txt"
  echo "::group::$libelle"
  "$@" 2>&1 | tee "$journal"
  code=${PIPESTATUS[0]}
  echo "::endgroup::"
  if [[ $code -eq 0 ]]; then
    resume "| $libelle | OK |"
  else
    resume "| $libelle | ÉCHEC (code $code) |"
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
      {
        echo ""
        echo "<details><summary>$libelle : détail (fichier, ligne, règle)</summary>"
        echo ""
        echo '```text'
        tail -n 60 "$journal"
        echo '```'
        echo "</details>"
        echo ""
      } >> "$GITHUB_STEP_SUMMARY"
    fi
    [[ $CODE -eq 0 ]] && CODE=$code
  fi
}

saute() {
  resume "| $1 | sauté : $2 |"
}

# Fichiers suivis ou nouveaux (non ignorés) : un fichier pas encore commité est aussi contrôlé.
fichiers_depot() {
  git ls-files --cached --others --exclude-standard "$@" | grep -vE '^(\.specify|\.claude)/' || true
}

fichiers_tf() {
  fichiers_depot '*.tf'
}

# --- Binaires officiels à somme vérifiée --------------------------------------------------

# Nom du fichier exécutable fourni par l'outil (OpenTofu livre « tofu »).
executable_de() {
  case "$1" in
    opentofu) echo tofu ;;
    *) echo "$1" ;;
  esac
}

# installer_binaire <nom> : télécharge, vérifie la somme figée, extrait ; affiche le chemin.
# Le cache est rangé par somme : un changement de version dans outils.lock force le
# téléchargement de la nouvelle version.
installer_binaire() {
  local nom="$1" valeur url somme exe dossier archive
  valeur="$(image_outil "$nom")" || return 2
  url="${valeur%%#*}"
  somme="${valeur##*#sha256=}"
  exe="$(executable_de "$nom")"
  dossier="$SORTIE/bin/$somme"
  if [[ ! -x "$dossier/$exe" ]]; then
    mkdir -p "$dossier"
    archive="$dossier/$(basename "$url")"
    curl -fsSL --retry 3 "$url" -o "$archive" || return 3
    if ! echo "$somme  $archive" | sha256sum -c --quiet - >&2; then
      echo "ERREUR : somme SHA-256 de « $nom » différente de securite/outils.lock" >&2
      rm -f "$archive"
      return 1
    fi
    case "$archive" in
      *.tar.gz) tar -xzf "$archive" -C "$dossier" "$exe" || return 3 ;;
      *.zip)
        python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extract(sys.argv[2], sys.argv[3])" \
          "$archive" "$exe" "$dossier" || return 3
        ;;
      *) mv "$archive" "$dossier/$exe" ;;
    esac
    chmod +x "$dossier/$exe"
  fi
  printf '%s\n' "$dossier/$exe"
}

# outil <nom> <arguments...> : installe si besoin puis exécute le binaire vérifié.
# shellcheck disable=SC2329 # appelée indirectement par etape
outil() {
  local nom="$1" chemin
  shift
  chemin="$(installer_binaire "$nom")" || return $?
  "$chemin" "$@"
}

installer_yamllint() {
  local venv="$SORTIE/venv-yamllint"
  if [[ ! -x "$venv/bin/yamllint" ]]; then
    python3 -m venv "$venv" || return 3
    "$venv/bin/pip" install --quiet --disable-pip-version-check --require-hashes \
      --only-binary=:all: -r securite/requirements-yamllint.txt || return 3
  fi
}

# --- Contrôles ---------------------------------------------------------------------------

controle_lint() {
  local format_ruff="concise" format_yaml="parsable" scripts dossier
  if [[ -n "$EN_CI" ]]; then
    format_ruff="github"
    format_yaml="github"
  fi
  etape "Épinglage (actions, images, tâches requises)" python3 outils/securite/verifier_epinglage.py
  etape "Ruff (lint et sécurité)" lancer_outil ruff -- check --no-cache --output-format "$format_ruff" .
  etape "Ruff (format)" lancer_outil ruff -- format --no-cache --check .

  mapfile -t scripts < <(fichiers_depot '*.sh')
  if [[ ${#scripts[@]} -gt 0 ]]; then
    etape "ShellCheck" lancer_outil shellcheck -- --format=gcc --external-sources \
      --source-path=SCRIPTDIR "${scripts[@]}"
  else
    saute "ShellCheck" "aucun script shell"
  fi

  if [[ -n "$(fichiers_tf)" ]]; then
    etape "OpenTofu (format)" outil opentofu fmt -check -recursive -diff infra
    while read -r dossier; do
      # shellcheck disable=SC2016 # script passé à bash -c, variables développées par lui
      etape "OpenTofu (validate $dossier)" bash -c \
        'tofu="$1"; d="$2"; "$tofu" -chdir="$d" init -backend=false -input=false >/dev/null \
         && "$tofu" -chdir="$d" validate' _ "$(installer_binaire opentofu)" "$dossier"
      etape "TFLint ($dossier)" outil tflint --config="$RACINE/.tflint.hcl" \
        --chdir="$dossier" --format=compact
    done < <(fichiers_tf | xargs -n1 dirname | sort -u)
  else
    saute "OpenTofu et TFLint" "aucun fichier .tf"
  fi

  if installer_yamllint; then
    etape "yamllint" "$SORTIE/venv-yamllint/bin/yamllint" --strict -f "$format_yaml" .
  else
    etape "yamllint (installation vérifiée)" false
  fi

  if [[ -z "$(fichiers_depot '.github/workflows/*.yml' '.github/workflows/*.yaml')" ]]; then
    saute "actionlint et zizmor" "aucun workflow"
    return
  fi
  etape "actionlint" outil actionlint -no-color
  if [[ -n "${GH_TOKEN:-}" ]]; then
    etape "zizmor (en ligne)" lancer_outil zizmor --reseau --env GH_TOKEN -- --quiet \
      --min-severity=medium .github/workflows
    if [[ -n "$EN_CI" ]]; then
      lancer_outil zizmor --reseau --env GH_TOKEN -- --quiet --format=sarif .github/workflows \
        > "$SORTIE/zizmor.sarif" || true
    fi
  else
    etape "zizmor (hors ligne)" lancer_outil zizmor -- --quiet --offline --min-severity=medium \
      .github/workflows
  fi
}

controle_iac() {
  etape "Politiques IaC du projet" python3 outils/securite/politiques_iac.py
  # Trivy en mode config, règles embarquées (aucun téléchargement), sans recherche de secrets
  # (couverte par le contrôle « secrets ») ; bloque à partir de la gravité moyenne.
  etape "Trivy (configuration IaC)" outil trivy config --quiet --skip-check-update \
    --cache-dir "$SORTIE/trivy-cache" --severity MEDIUM,HIGH,CRITICAL --exit-code 1 \
    --skip-dirs .specify --skip-dirs .claude --skip-dirs .git .
}

controle_tests() {
  etape "Tests unitaires" python3 -m unittest discover -s tests -t .
}

controle_secrets() {
  # Résultats écrits dans un fichier hors dépôt, jamais dans le journal : ils contiennent la
  # valeur des secrets. Seul verdict_secrets.py les lit et n'affiche que détecteur et lieu.
  # --no-verification : aucun secret n'est envoyé à un service tiers pour vérification.
  rm -f "$SORTIE/trufflehog.jsonl"
  # shellcheck disable=SC2016 # script passé à bash -c, variables développées par lui
  etape "TruffleHog (historique complet)" bash -c \
    'outil="$1"; sortie="$2"; "$outil" git "file://$PWD" --no-verification --no-update \
       --json --exclude-paths securite/trufflehog-exclusions.txt > "$sortie"' \
    _ "$(installer_binaire trufflehog)" "$SORTIE/trufflehog.jsonl"
  etape "Verdict des secrets (exceptions datées)" \
    python3 outils/securite/verdict_secrets.py "$SORTIE/trufflehog.jsonl"
}

# Images à analyser : celles de Compose (fonctionnalité 001) et celles des outils eux-mêmes.
images_a_analyser() {
  local compose
  for compose in openwebui/compose*.y*ml; do
    [[ -f "$compose" ]] && sed -nE "s/^[[:space:]]*image:[[:space:]]*['\"]?([^'\" ]+).*/\1/p" "$compose"
  done
  grep -vE '^[[:space:]]*(#|$)' "$LOCK" | cut -d= -f2- | grep -F '@sha256:' || true
}

# shellcheck disable=SC2329 # appelée indirectement par etape
grype() {
  lancer_outil grype --reseau --env GRYPE_DB_CACHE_DIR=/sortie/grype-db \
    --env GRYPE_CHECK_FOR_APP_UPDATE=false -- "$@"
}

controle_sca() {
  local images image nom chemin n=0 fichiers=() verrous
  etape "Exceptions (format et échéances)" python3 outils/securite/exceptions.py verifier
  mkdir -p "$SORTIE/sca" "$SORTIE/sarif-sca" "$SORTIE/grype-db"
  rm -f "$SORTIE"/sca/*.json "$SORTIE"/sarif-sca/*.sarif

  mapfile -t images < <(images_a_analyser | sort -u)
  for image in "${images[@]}"; do
    n=$((n + 1))
    etape "Grype : ${image%%@*}" grype "registry:$image" --quiet \
      -o "json=/sortie/sca/cible-$n.json" -o "sarif=/sortie/sarif-sca/cible-$n.sarif"
    fichiers+=("$SORTIE/sca/cible-$n.json")
  done
  for nom in "${BINAIRES[@]}"; do
    n=$((n + 1))
    if chemin="$(installer_binaire "$nom")"; then
      etape "Grype : binaire $nom" grype "file:/sortie/${chemin#"$SORTIE"/}" --quiet \
        -o "json=/sortie/sca/cible-$n.json" -o "sarif=/sortie/sarif-sca/cible-$n.sarif"
      fichiers+=("$SORTIE/sca/cible-$n.json")
    else
      etape "Installation vérifiée du binaire $nom" false
    fi
  done
  etape "Verdict des vulnérabilités (règle R3 et exceptions)" \
    python3 outils/securite/verdict_vulnerabilites.py --rapport "$SORTIE/sca/rapport.md" "${fichiers[@]}"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" && -f "$SORTIE/sca/rapport.md" ]]; then
    cat "$SORTIE/sca/rapport.md" >> "$GITHUB_STEP_SUMMARY"
  fi

  # Dépendances figées (y compris celles des outils, par exemple yamllint).
  verrous="$(fichiers_depot '*requirements*.txt' '*.lock.hcl' 'package-lock.json' 'poetry.lock' 'uv.lock')"
  if [[ -n "$verrous" ]]; then
    etape "OSV-Scanner (fichiers de verrouillage)" outil osv-scanner scan source -r .
  else
    saute "OSV-Scanner" "aucun fichier de verrouillage de dépendances"
  fi
}

# --- Point d'entrée ----------------------------------------------------------------------

controle="${1:-}"
case "$controle" in
  lint | iac | tests | secrets | sca) ;;
  *)
    echo "Usage : $0 <lint|iac|secrets|sca|tests>" >&2
    exit 2
    ;;
esac

resume ""
resume "### Contrôle « $controle »"
resume ""
resume "| Étape | Verdict |"
resume "|---|---|"
case "$controle" in
  lint) controle_lint ;;
  iac) controle_iac ;;
  tests) controle_tests ;;
  secrets) controle_secrets ;;
  sca) controle_sca ;;
esac
resume ""
if [[ $CODE -eq 0 ]]; then
  resume "Contrôle « $controle » : OK"
else
  resume "Contrôle « $controle » : ÉCHEC"
fi
exit "$CODE"
