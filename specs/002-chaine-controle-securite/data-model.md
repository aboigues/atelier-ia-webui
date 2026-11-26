# Modèle de données : chaîne de contrôle de sécurité

Aucune base de données : toutes les entités sont des fichiers versionnés du dépôt ou des
objets de la plateforme GitHub décrits par ces fichiers.

## Contrôle requis

| Champ | Règle |
|---|---|
| `nom` | nom de tâche stable du workflow, identique au nom exigé par le ruleset (`contracts/controles.md`) |
| `famille` | lint, sast, sca, iac, secrets, tests (FR-002) |
| `outils` | entrées de `securite/outils.lock` |
| `duree_max` | 15 min (FR-016) |
| `resultat` | succès, échec, annulé ; tout autre état que succès bloque le merge (FR-003) |
| `source` | application GitHub Actions (`integration_id` 15368) uniquement |
| `condition` | aucune condition `if:` au niveau de la tâche (un contrôle ignoré compterait comme réussi) |

## Outil figé (`securite/outils.lock`)

Une ligne par outil : `nom=registre/image:version@sha256:<64 hex>` pour une image, ou
`nom=https://...<version>...#sha256=<64 hex>` pour un binaire téléchargé (OpenTofu). Règles :
version explicite, jamais `latest` ; empreinte obligatoire ; un test vérifie que chaque `docker run`
des workflows et du script local passe par ce fichier et qu'aucune image n'y échappe.

## Règle de protection (`.github/rulesets/main.json`)

Représentation JSON du ruleset GitHub appliqué à `refs/heads/main` (cible `branch`,
`enforcement: active`, `bypass_actors: []`). L'état réel sur GitHub est comparé à ce fichier
par `regles_github.py verifier` ; tout écart est un échec.

## Exception de sécurité (`securite/exceptions.toml`)

| Champ | Type | Règle |
|---|---|---|
| `id` | texte | identifiant CVE/GHSA/GO, `<commit>:<fichier>:<ligne>` pour un faux positif de secret, ou `elevee-sans-correctif` (classe) |
| `type` | `vulnerabilite` / `secret-faux-positif` / `classe` | |
| `portee` | texte | dépôt d'image (`ghcr.io/...`), binaire d'outil (`binaire:<nom>`) ou fichier ; `*` interdit sauf pour `classe` |
| `raison` | texte | non vide, au moins 20 caractères |
| `acceptee_par` | texte | `Alexandre` uniquement |
| `acceptee_le` | date | pas dans le futur |
| `reexamen_le` | date | `acceptee_le < reexamen_le <= acceptee_le + 90 jours` |

États : `valide` (aujourd'hui <= `reexamen_le`) -> `echue` (après). Une exception échue est
ignorée par le verdict et signalée ; un fichier invalide fait échouer le contrôle `sca`.

## Vulnérabilité constatée (sortie de Grype, transitoire)

| Champ | Source |
|---|---|
| `id` | identifiant de la vulnérabilité |
| `gravite` | critique, élevée, moyenne, faible, inconnue |
| `correctif` | oui si une version corrigée est publiée |
| `composant`, `image` | paquet et image concernés |

Verdict (`research.md`, R3) : `bloquante`, `toleree` (par exception individuelle ou de
classe) ou `signalee`. Le rapport Markdown est joint au résumé de la tâche (`GITHUB_STEP_SUMMARY`)
et le SARIF déposé dans l'onglet Sécurité.

## Alerte

Résultat publié hors PR : alertes de code scanning (CodeQL, Grype, zizmor via SARIF),
alertes de secret scanning, échec de l'analyse hebdomadaire notifié par courriel.
