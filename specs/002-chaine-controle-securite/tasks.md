---

description: "Liste des tâches de la fonctionnalité 002 : chaîne de contrôle de sécurité du dépôt"
---

# Tasks: Chaîne de contrôle de sécurité du dépôt

**Input**: Design documents from `specs/002-chaine-controle-securite/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: inclus. Le plan prévoit des tests `unittest` pour chaque script (`tests/securite/`) et
`tests` est lui-même un contrôle requis (FR-002) ; chaque script est écrit après son test, qui
doit d'abord échouer.

**Organization**: tâches groupées par histoire (spec.md) ; US1 et US2 sont P1, US3 et US4 P2,
US5 P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers différents, aucune dépendance sur une tâche non terminée)
- **[Story]**: histoire de rattachement (US1 à US5)

## Conventions de chemins

Structure de `plan.md` : configuration des outils sous `securite/`, scripts sous
`outils/securite/`, tests sous `tests/securite/`, workflows et ruleset sous `.github/`.
Règles transverses pour toutes les tâches : français accentué, zéro emoji, aucun nom de client,
versions et empreintes exactement celles de `research.md` (R1, R2).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: arborescence et configuration des outils, sans logique.

- [X] T001 Créer l'arborescence `securite/`, `outils/securite/`, `tests/securite/` (avec `tests/__init__.py` et `tests/securite/__init__.py` vides pour `unittest discover`), `.github/workflows/`, `.github/rulesets/`, `.github/codeql/`
- [X] T002 [P] Écrire `securite/outils.lock` avec une ligne `nom=image:version@sha256:...` par outil de `research.md` R2 (ruff, shellcheck, tflint, actionlint, zizmor, grype, osv-scanner, checkov, gitleaks), en respectant `data-model.md` Outil figé (version explicite, empreinte obligatoire) ; ajouter la ligne `opentofu=https://github.com/opentofu/opentofu/releases/download/v1.13.10/tofu_1.13.10_linux_amd64.zip#sha256=c1f0d6b34d8328f963d3b1ad10896fae30a6c6890596190ffef477dab991090f` (somme tirée du `SHA256SUMS` dont la signature GPG a été vérifiée le 2026-11-26, `research.md` R2)
- [X] T003 [P] Écrire `securite/requirements-yamllint.txt` : `yamllint==1.38.0` et ses dépendances avec empreintes `--hash=sha256:` obtenues par `pip download` puis `pip hash` (installation avec `--require-hashes`)
- [X] T004 [P] Écrire `pyproject.toml` (section `[tool.ruff]` seulement) : `target-version = "py311"`, `line-length = 100`, règles `E`, `F`, `W`, `I`, `B`, `UP`, `S` (sécurité), `exclude` = `.specify/scripts/`, `.claude/skills/` (fichiers tiers Spec-Kit, `research.md` R6) ; règle `S101` autorisée sous `tests/`
- [X] T005 [P] Écrire `.yamllint.yaml` (base `default`, `line-length: max: 120`, `truthy` acceptant `on`, fichiers tiers Spec-Kit ignorés)
- [X] T006 [P] Écrire `.tflint.hcl` (plugin `terraform` en préréglage `recommended`, `call_module_type = "none"`) ; sans fichier `.tf` dans le dépôt, TFLint doit sortir en succès
- [X] T007 [P] (Remplacé le 2026-11-26 : TruffleHog et `securite/trufflehog-exclusions.txt`, research.md R10.) Écrire `securite/gitleaks.toml` : `[extend] useDefault = true`, liste d'exclusion limitée aux binaires du jeu fictif (`exemples/**/*.png`, `exemples/**/*.pdf`), aucune exclusion de dossier de code
- [X] T008 [P] (Remplacé le 2026-11-26 : Trivy `config`, sans fichier de configuration, research.md R10.) Écrire `securite/checkov.yaml` : `framework: [terraform, github_actions]`, `skip-framework: [secrets]` (couvert par Gitleaks), `compact: true`, sortie `cli` et `sarif`, `soft-fail: false`
- [X] T009 [P] Écrire `.github/codeql/codeql-config.yml` : suite `security-extended`, `paths-ignore` sur `.specify/scripts/` et `.claude/skills/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: briques communes à tous les contrôles : lancement d'un outil épinglé, vérification de l'épinglage, fichier d'exceptions.

**CRITICAL**: aucune histoire ne commence avant la fin de cette phase.

- [X] T010 Écrire `outils/securite/lib.sh` (ShellCheck propre) : fonction `image_outil <nom>` qui lit `securite/outils.lock` et échoue (code 2) si l'outil est absent ou sans empreinte ; fonction `lancer_outil <nom> [--reseau] -- <args>` qui exécute `docker run --rm -v "$PWD:/src:ro" -w /src` avec `--network=none` par défaut ; code de sortie de l'outil propagé, erreur Docker traduite en code 3 (`contracts/commandes.md`)
- [X] T011 [P] Test `tests/securite/test_verifier_epinglage.py` : cas d'un `uses:` épinglé par SHA de 40 caractères avec commentaire de version (accepté), par tag (refusé), sans commentaire (refusé), action locale `./` (acceptée) ; image `docker run` absente de `securite/outils.lock` ou sans empreinte (refusée) ; ligne mal formée de `outils.lock` au regard de `data-model.md` Outil figé (refusée) ; tâche d'un contrôle requis (`data-model.md` Contrôle requis.`nom`) portant une condition `if:` au niveau de la tâche (refusée, car GitHub compte un contrôle ignoré comme réussi) ; condition `if:` sur une étape (acceptée)
- [X] T012 Écrire `outils/securite/verifier_epinglage.py` (stdlib) : analyse `.github/workflows/*.yml`, `outils/securite/*.sh` et `securite/outils.lock` selon T011, y compris l'interdiction des `if:` sur les tâches requises lues dans `.github/rulesets/main.json` ; messages `fichier:ligne: règle` ; codes `contracts/commandes.md` (FR-010, FR-015)
- [X] T013 [P] Test `tests/securite/test_exceptions.py` : validation de chaque champ de `data-model.md` Exception de sécurité (`id`, `type` parmi trois valeurs, `portee` avec `*` réservé au type `classe`, `raison` de 20 caractères au moins, `acceptee_par` = `Alexandre`, `acceptee_le` pas dans le futur, `reexamen_le` au plus 90 jours après `acceptee_le`) ; états `valide` et `echue` ; alerte à 14 jours de l'échéance ; sortie `gitleaksignore` limitée aux faux positifs valides ; dates injectables pour des tests déterministes
- [X] T014 Écrire `outils/securite/exceptions.py` (stdlib, `tomllib`) avec les sous-commandes `verifier` et `gitleaksignore` et une API `charger(date_du_jour)` réutilisable par le verdict, conforme à T013 et `contracts/exceptions.md` ; valide chaque champ selon `data-model.md` Exception de sécurité.`id`, .`type`, .`portee`, .`raison`, .`acceptee_par`, .`acceptee_le` et .`reexamen_le`, et calcule l'état `valide`/`echue`
- [X] T015 Écrire `securite/exceptions.toml` avec la seule exception de classe `elevee-sans-correctif` (`acceptee_le = 2026-11-26`, `reexamen_le = 2027-02-24`) et les modèles commentés de `contracts/exceptions.md` ; `outils/securite/exceptions.py verifier` doit rendre 0

**Checkpoint**: `python3 -m unittest discover -s tests` vert ; `verifier_epinglage.py` et `exceptions.py verifier` rendent 0.

---

## Phase 3: User Story 1 - Contrôles bloquants sur chaque PR (Priority: P1) MVP

**Goal**: les six contrôles s'exécutent seuls sur chaque PR et bloquent en cas d'échec ; résultat lisible dans la PR.

**Independent Test**: ouvrir la PR de cette fonctionnalité : `lint`, `sast-codeql`, `iac`, `tests` (et `secrets`, `sca` une fois US3 et US4 livrées) apparaissent et passent ; une faute de style poussée sur la branche fait échouer `lint` avec fichier, ligne et règle.

### Tests for User Story 1

- [X] T016 [P] [US1] Test `tests/securite/test_politiques_iac.py` : politiques maison de `research.md` R2 (groupe de sécurité limité à 80 et 443 sans 22, étiquette `atelier-session` sur toute ressource Scaleway, `scaleway_iam_api_key` avec `expires_at`, politique IAM limitée à `GenerativeApisModelAccess`, Compose sans `privileged` ni port publié hors `127.0.0.1` pour le service `openwebui`, images Compose et cloud-init épinglées par empreinte) ; chaque politique est testée sur des fragments HCL et YAML fictifs écrits dans le test, et le test sur les fichiers réels est ignoré (`skipUnless`) tant que `infra/` et `openwebui/` n'existent pas (spec, cas limite « dépôt sans code »)

### Implementation for User Story 1

- [X] T017 [US1] Écrire `outils/securite/politiques_iac.py` (stdlib, analyse textuelle des `.tf` et YAML, sans dépendance) appelé par T016 et par le contrôle `iac`
- [X] T018 [P] [US1] Mettre `exemples/bloc-operatoire/demo.py` et `exemples/bloc-operatoire/generer_documents.py` en conformité Ruff (lint et format) sans changer leur comportement ; justifier en commentaire chaque `# noqa: S...` restant (par exemple l'appel `subprocess` à `scw`, liste d'arguments sans shell)
- [X] T019 [US1] Écrire `outils/securite/controle.sh <controle>` (ShellCheck propre, utilise `lib.sh`) : un sous-programme par contrôle non-CodeQL de `contracts/controles.md` (`lint`, `iac`, `tests` ; `secrets` et `sca` ajoutés par US3 et US4), avec résumé Markdown `outil | fichier | ligne | règle` écrit dans `$GITHUB_STEP_SUMMARY` si la variable existe, sinon sur la sortie standard (FR-013) ; installation d'OpenTofu 1.13.10 depuis l'URL de `securite/outils.lock` avec vérification de la somme SHA-256 figée dans ce même fichier (échec si elle diffère), pour `tofu fmt -check` et `tofu validate` (sautés proprement sans fichier `.tf`) ; yamllint installé dans un venv temporaire avec `--require-hashes`
- [X] T020 [US1] Écrire `.github/workflows/controles.yml` selon `contracts/controles.md` : déclencheurs `pull_request` vers `main`, `push` sur `main`, `workflow_dispatch` ; `permissions: contents: read` au niveau du workflow ; `concurrency` ; tâches `lint`, `iac`, `tests` appelant `outils/securite/controle.sh`, chacune `runs-on: ubuntu-24.04`, `timeout-minutes: 15` (`data-model.md` Contrôle requis `duree_max`), `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` avec `persist-credentials: false` ; la tâche `lint` dépose le SARIF de zizmor (`security-events: write` justifié en commentaire) ; le verdict de chaque outil reste bloquant, mais l'étape de dépôt SARIF porte `if: github.event.pull_request.head.repo.full_name == github.repository || github.event_name != 'pull_request'` et `continue-on-error: true`, car GitHub retire le droit d'écriture aux PR issues de forks (condition sur l'étape, jamais sur la tâche, voir T011) ; aucune expression `${{ github.event.* }}` dans un `run:`
- [X] T021 [US1] (Verdict par `outils/securite/verdict_codeql.py`, testé par `tests/securite/test_verdict_codeql.py`.) Ajouter la tâche `sast-codeql` à `.github/workflows/controles.yml` : `github/codeql-action/init` et `analyze` épinglés `@915412ff23e8b7659517e607487dbeae018f2934 # v4.39.5`, langages `python` et `actions`, `config-file: .github/codeql/codeql-config.yml`, `security-events: write` justifié, `timeout-minutes: 15` ; pour une PR issue d'un fork, `analyze` avec `upload: never` (même condition d'étape que T020) et échec de la tâche si une alerte de sécurité est trouvée dans le SARIF local
- [X] T022 [US1] Exécuter localement `outils/securite/controle.sh lint`, `iac` et `tests`, puis `verifier_epinglage.py`, et corriger jusqu'à obtenir 0 erreur sur la branche (y compris sur les workflows eux-mêmes : actionlint et zizmor)

**Checkpoint**: US1 livrée : la PR montre `lint`, `sast-codeql`, `iac`, `tests` au vert.

---

## Phase 4: User Story 3 - Aucun secret dans le dépôt (Priority: P2)

**Goal**: contrôle `secrets` sur tout l'historique et faux positifs gérés par exception. (Phase placée avant US2 car le ruleset exige le nom de ce contrôle.)

**Independent Test**: `outils/securite/controle.sh secrets` sur la branche : 0 fuite sur tout l'historique ; un fichier temporaire contenant un jeton au format reconnu fait échouer le contrôle.

- [X] T023 [US3] (Réalisé avec TruffleHog et `verdict_secrets.py`, research.md R10.) Ajouter le sous-programme `secrets` à `outils/securite/controle.sh` : `exceptions.py gitleaksignore` vers un `.gitleaksignore` temporaire hors dépôt, puis Gitleaks `git` sur tout l'historique avec `securite/gitleaks.toml`, réseau coupé, rapport SARIF et résumé (FR-006, FR-013)
- [X] T024 [US3] Ajouter la tâche `secrets` à `.github/workflows/controles.yml` (`fetch-depth: 0` sur `checkout`, `timeout-minutes: 15`, permissions par défaut)
- [X] T025 [US3] Exécuter `outils/securite/controle.sh secrets` sur tout l'historique actuel ; toute détection est soit une vraie fuite (arrêt et signalement à Alexandre, jamais de correction silencieuse), soit un faux positif ajouté à `securite/exceptions.toml` avec raison (SC-004)

**Checkpoint**: `secrets` au vert sur la PR.

---

## Phase 5: User Story 4 - Vulnérabilités suivies et exceptions documentées (Priority: P2)

**Goal**: contrôle `sca` avec le verdict R3, exceptions datées, analyse hebdomadaire.

**Independent Test**: `controle.sh sca` passe sur la branche ; un JSON Grype fictif contenant une élevée avec correctif rend le verdict bloquant ; la même vulnérabilité avec une exception valide est tolérée, avec une exception échue de nouveau bloquante.

### Tests for User Story 4

- [X] T026 [P] [US4] Test `tests/securite/test_verdict_vulnerabilites.py` sur des JSON Grype fictifs : les quatre règles de `research.md` R3 et le tableau de `contracts/exceptions.md` ; gravités de `data-model.md` Vulnérabilité constatée `gravite` (dont `inconnue`, traitée comme moyenne) et `correctif` ; exception individuelle appliquée seulement si `id` et `portee` correspondent ; classe `elevee-sans-correctif` absente ou échue rendant bloquantes les élevées sans correctif ; rapport Markdown listant bloquantes, tolérées et signalées ; JSON illisible ou vide traité comme une erreur (code 3), jamais comme un succès

### Implementation for User Story 4

- [X] T027 [US4] Écrire `outils/securite/verdict_vulnerabilites.py` (stdlib, réutilise `exceptions.charger`) conforme à T026 et `contracts/commandes.md` ; lit `data-model.md` Vulnérabilité constatée.`gravite` (`inconnue` traitée comme moyenne, précision propre à cette tâche) et .`correctif`, et rend le verdict `bloquante`/`toleree`/`signalee`
- [X] T028 [US4] Ajouter le sous-programme `sca` à `outils/securite/controle.sh` : `exceptions.py verifier` ; liste des images = lignes `image:` de `openwebui/compose.yaml` s'il existe + images de `securite/outils.lock` ; Grype `-o json` par image (réseau autorisé pour la base de vulnérabilités) puis verdict ; OSV-Scanner `scan source -r .` seulement si un fichier de verrouillage est présent ; SARIF de Grype pour l'onglet Sécurité
- [X] T029 [US4] Ajouter la tâche `sca` à `.github/workflows/controles.yml` (`security-events: write` justifié, `timeout-minutes: 15`, dépôt SARIF conditionné comme en T020)
- [X] T030 [US4] Écrire `.github/workflows/analyse-hebdomadaire.yml` selon `contracts/controles.md` : `schedule: '0 6 * * 1'` et `workflow_dispatch`, tâches `sca` et zizmor via `controle.sh`, mêmes épinglages et permissions minimales (FR-009)
- [X] T031 [US4] Exécuter `outils/securite/controle.sh sca` ; pour chaque vulnérabilité bloquante d'un outil de `outils.lock`, monter de version (en relevant version et empreinte, principe V) plutôt qu'ajouter une exception ; n'ajouter d'exception que si aucune version corrigée n'existe, et le signaler à Alexandre

**Checkpoint**: les six contrôles existent ; la PR doit être entièrement verte.

---

## Phase 6: User Story 2 - Branche principale protégée (Priority: P1)

**Goal**: ruleset versionné, appliqué et vérifié par commande, sans contournement.

**Independent Test**: après application, `regles_github.py verifier` rend 0 ; push direct, force-push et merge d'une PR rouge sont refusés (T040).

### Tests for User Story 2

- [X] T032 [P] [US2] Test `tests/securite/test_regles_github.py` : comparaison entre `.github/rulesets/main.json` et une réponse d'API fictive (identique, règle manquante, contrôle requis manquant, contrôle requis sans `integration_id` 15368, acteur de contournement présent, méthode de merge `merge` autorisée, secret scanning ou push protection désactivés) ; aucun appel réseau dans les tests (appel à `gh` injectable)

### Implementation for User Story 2

- [X] T033 [P] [US2] Écrire `.github/rulesets/main.json` selon `research.md` R5 : cible `refs/heads/main`, `enforcement: active`, `bypass_actors: []`, règles `deletion`, `non_fast_forward`, `required_linear_history`, `pull_request` (0 approbation, méthodes `squash` et `rebase`), `required_status_checks` strict avec exactement les noms de `contracts/controles.md` et `data-model.md` Contrôle requis.`nom` (`lint`, `sast-codeql`, `sca`, `iac`, `secrets`, `tests`), chacun lié à l'application GitHub Actions (`integration_id: 15368`) pour qu'aucune autre source ne puisse publier un faux succès ; `data-model.md` Contrôle requis.`resultat` (tout état autre que succès bloque) et Règle de protection.`enforcement` = `active`, .`bypass_actors` = `[]`
- [X] T034 [US2] Écrire `outils/securite/regles_github.py` (stdlib + `gh api`) avec `appliquer` (création ou mise à jour idempotente du ruleset, activation de `secret_scanning` et `secret_scanning_push_protection`, désactivation du default setup CodeQL) et `verifier` (écarts listés, code 1), conforme à T032 et `contracts/commandes.md` (FR-004, FR-005, FR-006)
- [X] T035 [US2] Ajouter un test dans `tests/securite/test_regles_github.py` qui vérifie que les noms de `required_status_checks` du ruleset sont exactement les noms de tâches de `.github/workflows/controles.yml` (un renommage sans mise à jour du ruleset échoue) et qu'aucune de ces tâches ne porte de condition `if:` (D1, en complément de T012)

**Checkpoint**: ruleset prêt ; son application se fait après le merge (T039).

---

## Phase 7: User Story 5 - Mêmes contrôles sur le poste avant l'envoi (Priority: P3)

**Goal**: une commande locale qui donne le même verdict que la PR (hors CodeQL et push protection).

**Independent Test**: sur une branche avec une faute de style et un test en échec, `controles-locaux.sh --rapide` signale les deux.

- [X] T036 [US5] Écrire `outils/securite/controles-locaux.sh [--rapide]` (ShellCheck propre) : enchaîne `verifier_epinglage.py` puis `controle.sh lint`, `iac`, `secrets`, `tests` et, sauf `--rapide`, `sca` ; tableau final contrôle / verdict ; code 1 si un contrôle échoue (FR-014)
- [X] T037 [US5] Exécuter `outils/securite/controles-locaux.sh` complet sur la branche et vérifier l'identité de verdict avec la PR

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T038 [P] Écrire `outils/securite/demonstration.sh` selon `research.md` R8 et `contracts/commandes.md` : branche et PR brouillon jetables avec un défaut par famille, attente des contrôles (`gh pr checks --watch`), vérification des 6 échecs et du refus de merge, tentatives de push direct et de force-push sur `main` (refus attendus), nettoyage systématique (`trap`) ; ne modifie jamais `main`
- [X] T039 (Fait le 2026-11-26 après le merge de la PR 3 : ruleset `protection-main` actif, 0 contournement, 6 contrôles liés à GitHub Actions, secret scanning et push protection activés, default setup CodeQL désactivé ; `regles_github.py verifier` = 0.) Mise en service, après merge de cette fonctionnalité par Alexandre uniquement : `regles_github.py appliquer`, puis `verifier` (code 0) ; consigner le résultat dans la PR suivante
- [ ] T040 Exécuter `outils/securite/demonstration.sh` et les scénarios C à F de `quickstart.md` ; consigner les résultats (SC-002, SC-003, SC-005, SC-007)
- [X] T041 [P] Mettre à jour `README.md` (section « Contrôles de sécurité » : contrôles requis, commande locale, exceptions) et `CLAUDE.md` (commande locale à lancer avant chaque push ; merge en squash ou rebase uniquement)
- [X] T042 [P] Reporter dans `specs/001-environnement-tp-session/plan.md` (section « Phases suivantes ») l'obligation `research.md` R9 : images de `openwebui/compose.yaml` et de cloud-init épinglées par empreinte, code conforme aux six contrôles dès le premier commit
- [X] T043 Vérifier avant commit : `git status` sans fichier de `sessions/`, `exports/`, `identifiants/`, `documents-clients/` ; aucun emoji ni nom de client dans les fichiers ajoutés ; puis commit, push et PR vers `main` (sans merge)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (T001-T009) -> Foundational (T010-T015) -> histoires.
- US1 (T016-T022) d'abord : elle crée `controle.sh` et `controles.yml`, que US3, US4 et US5 étendent.
- US3 (T023-T025) et US4 (T026-T031) après US1, indépendantes entre elles sauf qu'elles modifient les mêmes fichiers `controle.sh` et `controles.yml` (à faire l'une après l'autre).
- US2 (T032-T035) après US3 et US4 : le ruleset exige les six noms de contrôle ; T032 et T033 peuvent être écrits plus tôt.
- US5 (T036-T037) après US1, US3 et US4 (enchaîne tous les sous-programmes).
- Polish : T038 après US2 ; T039 et T040 après le merge de la PR ; T041, T042 à tout moment après US1.

### Within Each User Story

- Le test (`tests/securite/test_*.py`) est écrit et vu en échec avant le script correspondant.
- Scripts avant workflows ; workflows avant exécution de vérification.

### Parallel Opportunities

- Phase 1 : T002 à T009 en parallèle après T001.
- Phase 2 : T011 et T013 en parallèle ; T012 et T014 en parallèle une fois leurs tests écrits.
- T016, T018, T026, T032, T033 : fichiers distincts, parallélisables dès la fin de la phase 2.
- T038, T041, T042 en parallèle.

## Parallel Example: après la phase 2

```text
T016 [US1] tests/securite/test_politiques_iac.py
T018 [US1] mise en conformité Ruff de exemples/bloc-operatoire/*.py
T026 [US4] tests/securite/test_verdict_vulnerabilites.py
T032 [US2] tests/securite/test_regles_github.py
T033 [US2] .github/rulesets/main.json
```

## Implementation Strategy

### MVP (User Story 1)

1. Phases 1 et 2.
2. US1 : `lint`, `sast-codeql`, `iac`, `tests` sur chaque PR.
3. Valider sur la PR : déjà bloquant si les contrôles sont rendus requis.

### Livraison complète (une seule PR, principe VII)

US3 puis US4 complètent les six contrôles ; US2 prépare la protection ; US5 le confort local ;
merge par Alexandre ; T039 et T040 mettent la protection en service et la démontrent. La
fonctionnalité 001 reprend ensuite (`/speckit-tasks`) sur une nouvelle branche.

## Notes

- [P] = fichiers différents, aucune dépendance.
- Toute version d'outil modifiée en cours de route est relevée à nouveau (registre, releases) et
  reportée dans `research.md` et `securite/outils.lock` (principe V).
- Un contrôle en échec se corrige, il ne se désactive pas (constitution, Flux de travail).
