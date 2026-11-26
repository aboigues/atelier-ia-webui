# Contrat : contrôles requis et workflows

## Contrôles requis par le ruleset de `main`

Les noms ci-dessous sont des noms de tâches stables ; les renommer impose de mettre à jour
`.github/rulesets/main.json` dans la même PR.

| Contrôle | Famille | Contenu | Bloque si |
|---|---|---|---|
| `lint` | lint | Ruff (lint et format, règles `S` comprises), ShellCheck, `tofu fmt -check` et `tofu validate`, TFLint, yamllint, actionlint, zizmor (niveau `medium` et plus), vérification de `securite/outils.lock` | une erreur |
| `sast-codeql` | SAST | CodeQL `python` et `actions`, suite `security-extended`, verdict par `verdict_codeql.py` sur le SARIF local | une alerte de gravité erreur ou avertissement de sécurité |
| `sca` | SCA | validation de `securite/exceptions.toml` ; Grype sur chaque image de `openwebui/compose.yaml` et de `securite/outils.lock` et sur chaque binaire d'outil de `securite/outils.lock` ; OSV-Scanner sur les fichiers de verrouillage présents ; verdict R3 | une vulnérabilité `bloquante`, un fichier d'exceptions invalide |
| `iac` | IaC | Trivy `config` (règles embarquées, gravité moyenne et plus) ; politiques maison (`outils/securite/politiques_iac.py`, testées par `tests/securite/test_politiques_iac.py`) | une mauvaise configuration Trivy, une politique maison en échec |
| `secrets` | secrets | TruffleHog `git` sur tout l'historique (`fetch-depth: 0`, `--no-verification`), exclusions `securite/trufflehog-exclusions.txt`, verdict par `verdict_secrets.py` avec les faux positifs de `securite/exceptions.toml` | une fuite |
| `tests` | tests | `python3 -m unittest discover -s tests` | un test en échec ou en erreur |

Sans code applicatif encore présent, chaque contrôle s'exécute et réussit (aucun contrôle
« en attente »).

Chaque contrôle requis est lié à l'application GitHub Actions (`integration_id` 15368) dans le
ruleset, et aucune tâche requise ne porte de condition `if:`.

## `.github/workflows/controles.yml`

- Déclencheurs : `pull_request` (branches `main`), `push` (branche `main`),
  `workflow_dispatch`. Jamais `pull_request_target`.
- `permissions: contents: read` au niveau du workflow ; `security-events: write` ajouté
  uniquement aux tâches `sast-codeql`, `sca` et `lint` (dépôt SARIF de zizmor), avec un
  commentaire de justification.
- `concurrency: group: controles-${{ github.ref }}`, `cancel-in-progress: true`.
- Chaque tâche : `runs-on: ubuntu-24.04`, `timeout-minutes: 15`,
  `actions/checkout@<sha> # v7.0.1` avec `persist-credentials: false`.
- Les outils tournent par `docker run --rm --network=<selon besoin> -v "$PWD:/src:ro"` sur
  l'image lue dans `securite/outils.lock` ; réseau coupé (`--network=none`) pour les outils
  qui n'en ont pas besoin (Ruff, ShellCheck, zizmor hors ligne). Les binaires officiels
  (actionlint, TFLint, OSV-Scanner, TruffleHog, Trivy, OpenTofu) sont téléchargés, vérifiés par
  leur somme figée dans `securite/outils.lock` puis exécutés sur le runner.
- Aucune variable `${{ github.event.* }}` interpolée directement dans un script `run:` (règle
  zizmor `template-injection`).
- Résumé lisible dans `GITHUB_STEP_SUMMARY` : outil, fichier, ligne, règle (FR-013).
- PR issue d'un fork : verdicts bloquants inchangés ; étapes de dépôt SARIF conditionnées
  (`head.repo.full_name == github.repository`) et non bloquantes ; CodeQL avec `upload: never`.

## `.github/workflows/analyse-hebdomadaire.yml`

- Déclencheurs : `schedule` (`0 6 * * 1`), `workflow_dispatch`.
- Tâches : `sca` et zizmor sur `main`, mêmes scripts que `controles.yml` ; dépôt SARIF.
- Échec du workflow : notification GitHub par courriel au propriétaire du dépôt.
