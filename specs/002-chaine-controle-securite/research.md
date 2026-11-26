# Recherche (phase 0) : chaîne de contrôle de sécurité du dépôt

Date : 2026-11-26. Versions relevées le jour même sur les pages de releases GitHub, empreintes
des images résolues avec `docker buildx imagetools inspect`, empreintes des actions lues sur les
tags (API GitHub). Rien n'est tiré de mémoire (principe V).

## R1. Leçon de l'incident Trivy de mars 2026 : le moins d'actions tierces possible

- **Constat** : le 2026-03-19, 76 des 77 tags de `aquasecurity/trivy-action` et tous ceux de
  `aquasecurity/setup-trivy` ont été redirigés vers du code volant les secrets des pipelines
  (CVE-2026-33634, GHSA-69fq-xp46-6x23) ; le 2026-03-22, des images Docker Hub de Trivy
  malveillantes ont été publiées. Les pipelines épinglés par empreinte SHA n'ont pas été
  touchés.
- **Décision** : les outils d'analyse ne sont **pas** appelés par des actions tierces mais
  exécutés dans leurs images officielles **épinglées par empreinte** (`image@sha256:...`),
  listées dans un fichier unique `securite/outils.lock`, lu à la fois par les workflows et par
  le contrôle local (FR-014). Seules trois actions sont utilisées, toutes de GitHub, épinglées
  par SHA :

  | Action | Version | Empreinte |
  |---|---|---|
  | `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
  | `github/codeql-action` (`init`, `analyze`, `upload-sarif`) | v4.39.5 | `915412ff23e8b7659517e607487dbeae018f2934` |

- **Alternatives** : actions de marché (`trivy-action`, `gitleaks-action`, `checkov-action`) :
  pratiques mais chacune élargit la surface d'attaque et exige un suivi de version de plus.

## R2. Outils retenus et versions figées

Tableau mis à jour pendant l'implémentation (voir R10 : images d'outils vulnérables remplacées
par des binaires officiels vérifiés, Gitleaks par TruffleHog, Checkov par Trivy).

| Famille (FR-002) | Outil | Version | Image épinglée |
|---|---|---|---|
| Lint Python (+ règles de sécurité `S`) | Ruff | 0.17.6 | `ghcr.io/astral-sh/ruff@sha256:2671e9bf3e50c24a88e731f209f9bf01c0360da6857ae36bca680b222efc3528` |
| Lint shell | ShellCheck | v0.11.0 | `koalaman/shellcheck@sha256:61862eba1fcf09a484ebcc6feea46f1782532571a34ed51fedf90dd25f925a8d` |
| Lint OpenTofu | `tofu fmt -check`, `tofu validate` | 1.13.10 | `tofu_1.13.10_linux_amd64.zip`, SHA-256 `c1f0d6b34d8328f963d3b1ad10896fae30a6c6890596190ffef477dab991090f` figée dans `outils.lock`, tirée du `SHA256SUMS` dont la signature GPG (clé OpenTofu `E3E6 E43D 84CB 852E ADB0 051D 0C0A F313 E5FD 9F80`) a été vérifiée le 2026-11-26 |
| Lint OpenTofu (règles) | TFLint | v0.66.0 | binaire officiel `tflint_linux_amd64.zip`, somme figée (R10) |
| Lint YAML | yamllint | 1.38.0 | pas d'image officielle : `pip install --require-hashes` |
| Lint des workflows | actionlint | 1.7.12 | binaire officiel, somme figée (R10) |
| Sécurité des workflows (épinglage, permissions, injections, actions vulnérables) | zizmor | 1.33.1 | `ghcr.io/zizmorcore/zizmor@sha256:ecd3ffe6158de1322e05a044ed43749bee12b1dccb7e1a7859bc6ac4b2a1c516` |
| SAST | CodeQL (langages `python`, `actions`) | action v4.39.5 | action GitHub (R1) |
| SCA images Docker | Grype | v0.122.1 | `anchore/grype@sha256:661583704a253c0448ed63998b5ea2cd9d5a76ee71eedc4aed439b8ce3e93a1c` |
| SCA dépendances (fichiers de verrouillage) | OSV-Scanner | v2.7.1 | binaire officiel, somme figée (R10) |
| IaC | Trivy (mode `config`), remplace Checkov (R10) | v0.76.2 | binaire officiel, release immuable, somme figée ; jamais l'action ni l'image |
| IaC (règles du projet) | politiques maison (`unittest`) | - | Python du poste ou du runner |
| Secrets (historique complet) | TruffleHog, remplace Gitleaks (R10) | v3.100.1 | binaire officiel, somme figée ; `--no-verification` |
| Secrets (blocage à l'envoi) | secret scanning et push protection GitHub | - | réglage du dépôt |
| Tests | `python3 -m unittest` | Python du runner `ubuntu-24.04` (3.12) | - |

- **Raison des choix** :
  - Ruff remplace flake8, isort et Bandit (règles `S`) en un seul outil ;
  - zizmor vérifie l'épinglage par SHA (FR-010), les permissions (FR-011), les injections de
    contexte et les actions connues comme vulnérables : il couvre aussi la SCA des actions ;
  - Grype plutôt que Trivy pour les images : sortie JSON exploitable, option des correctifs
    disponibles, et pas d'historique de compromission récent ; ce n'est pas un rejet définitif
    de Trivy (corrigé depuis), mais un choix de prudence ;
  - CodeQL : gratuit pour un dépôt public, résultats dans l'onglet Sécurité et dans la PR ;
  - Checkov : couverture générique OpenTofu (Scaleway peu couvert par tous les outils du
    marché), d'où des **politiques maison** testées : groupe de sécurité limité à 80/443 et
    sans 22, étiquette `atelier-session` sur toute ressource, clé IAM avec `expires_at`,
    politique IAM limitée à `GenerativeApisModelAccess`, Compose sans `privileged` ni port
    exposé hors `127.0.0.1` en local, images Compose épinglées par empreinte.
- **Alternatives** : Semgrep (redondant avec CodeQL + Ruff `S`) ; Bandit seul (couvert par
  Ruff) ; Trivy config (pas de Compose, couverture Scaleway nulle).

## R3. Règle de seuil des vulnérabilités (FR-007, clarifiée)

- **Décision** : Grype produit un JSON unique par image ; un script maison
  `outils/securite/verdict_vulnerabilites.py` (stdlib, testé) rend le verdict :
  1. critique ou élevée **avec** correctif publié -> bloquante, sauf exception individuelle ;
  2. critique **sans** correctif -> bloquante, sauf exception individuelle ;
  3. élevée **sans** correctif -> listée dans le rapport, non bloquante **tant que**
     l'exception de classe `elevee-sans-correctif` est valide ; échue, elle redevient
     bloquante ;
  4. moyenne ou faible -> listée seulement.
- **Raison** : une seule source de vérité (le fichier d'exceptions), une logique testable, et
  aucune dépendance à des options d'outil qui changent de nom entre versions.
- **Images analysées** : celles de la fonctionnalité 001 (`open-webui`, `caddy`) dès qu'elles
  sont référencées dans `openwebui/compose.yaml`, ainsi que les images des outils de
  `securite/outils.lock` (un outil vulnérable est aussi une menace).

## R4. Exceptions (FR-008)

- **Décision** : fichier versionné `securite/exceptions.toml` (format :
  `contracts/exceptions.md`). Le script `outils/securite/exceptions.py` valide les champs,
  refuse une date de réexamen à plus de 90 jours de l'acceptation, ignore une exception échue
  et produit les fichiers d'ignorance propres aux outils au moment du contrôle (jamais
  versionnés à part) : `.gitleaksignore` (empreintes de faux positifs) et la liste passée au
  verdict des vulnérabilités. Le fichier d'exceptions lui-même est contrôlé à chaque PR.
- **Alternatives** : `.trivyignore.yaml` (gère une expiration, mais propre à Trivy) ;
  `.grype.yaml` (pas d'expiration).

## R5. Protection de `main` (FR-004, FR-005)

- **Décision** : un **ruleset** GitHub décrit dans `.github/rulesets/main.json`, appliqué et
  comparé par `outils/securite/regles_github.py appliquer|verifier` (API REST via `gh api`) :
  - règles `deletion`, `non_fast_forward`, `required_linear_history` ;
  - `pull_request` avec 0 approbation requise (seul mainteneur), méthodes de merge
    autorisées : `squash` et `rebase` ;
  - `required_status_checks` strict (branche à jour) sur les contrôles de
    `contracts/controles.md`, chacun lié à l'application GitHub Actions (`integration_id`
    15368, vérifié par `gh api /apps/github-actions`) : sans cela, toute application ou tout
    jeton autorisé à écrire des statuts pourrait publier un faux succès sous le même nom ;
  - **aucun** acteur de contournement (`bypass_actors` vide), administrateur compris.
  Le même script active le secret scanning et la push protection
  (`security_and_analysis`) et désactive le « default setup » de CodeQL au profit du workflow.
- **Raison** : les rulesets sont versionnables en JSON, s'appliquent aux administrateurs et
  sont gratuits sur un dépôt public ; l'ancienne « branch protection » est moins expressive.
- **Alternatives** : réglage manuel dans l'interface (non reproductible, contraire au
  principe III) ; OpenTofu avec le fournisseur GitHub (un fournisseur et un état de plus).

## R6. Workflows (FR-001, FR-003, FR-011, FR-012, FR-016)

- **Décision** :
  - `.github/workflows/controles.yml` sur `pull_request` vers `main` et `push` sur `main` :
    tâches `lint`, `sast-codeql`, `sca`, `iac`, `secrets`, `tests`, chacune
    `timeout-minutes: 15`, `runs-on: ubuntu-24.04`, `permissions: contents: read` au niveau du
    workflow ; `security-events: write` uniquement pour les tâches qui déposent un SARIF, avec
    commentaire de justification ; `concurrency` qui annule les exécutions dépassées.
  - **Pas de filtre de chemins** : tous les contrôles tournent sur toute PR, documentation
    comprise, pour qu'aucun contrôle requis ne reste « en attente » (spec, AS 1.3).
  - Événement `pull_request` (jamais `pull_request_target`) : une PR issue d'un fork n'a ni
    secret ni droit d'écriture (FR-012) ; `persist-credentials: false` sur `checkout`.
  - `.github/workflows/analyse-hebdomadaire.yml` : `schedule` le lundi 06:00 UTC +
    `workflow_dispatch`, sur `main` : `sca` (Grype, OSV-Scanner) et zizmor ; résultats en
    SARIF dans l'onglet Sécurité, échec du workflow notifié par courriel à Alexandre (FR-009).
  - Chaque outil échoue en cas d'erreur d'exécution (code de sortie non nul) : une analyse
    impossible n'est jamais un succès.
  - **Aucune condition `if:` sur une tâche requise** : GitHub compte un contrôle requis
    « ignoré » comme réussi ; une condition ajoutée plus tard contournerait silencieusement le
    contrôle. `verifier_epinglage.py` et un test le refusent.
  - **PR issues de forks** : GitHub y force `security-events: read` ; le dépôt SARIF y est donc
    impossible. Le verdict de chaque outil reste bloquant ; seule l'étape de dépôt SARIF est
    conditionnée (condition d'étape) et non bloquante, et CodeQL y tourne avec `upload: never`.
- **Périmètre analysé** : tout le dépôt pour les secrets ; pour les linters, tout sauf les
  fichiers tiers de Spec-Kit (`.specify/scripts/`, `.claude/skills/`), copiés d'un projet
  externe et non modifiés par nous ; ils restent couverts par la détection de secrets et par
  CodeQL.

## R7. Contrôle local (FR-014)

- **Décision** : `outils/securite/controles-locaux.sh` lit `securite/outils.lock` et lance les
  mêmes images, mêmes options et mêmes fichiers de configuration que la PR : linters, tests,
  Gitleaks, Checkov, politiques maison, Grype (option `--rapide` pour sauter Grype, qui
  télécharge sa base). Non reproduits en local : CodeQL et la push protection.
- **Alternatives** : `pre-commit` (dépendance Python de plus, versions d'outils dupliquées) ;
  `make` (absent par défaut sous certaines installations, sans gain ici).

## R8. Démonstration des blocages (SC-002, SC-003)

- **Décision** : `outils/securite/demonstration.sh` crée une branche jetable, y introduit un
  défaut par famille (style Python, appel `subprocess` avec `shell=True`, image vulnérable
  connue, groupe de sécurité ouvert sur 22, test en échec, faux secret au format reconnu mais
  marqué comme jeton de test de Gitleaks), ouvre une PR brouillon, attend les contrôles,
  vérifie que les 6 familles sont rouges et que le merge est refusé, puis ferme la PR et
  supprime la branche. La tentative de push direct et de force-push sur `main` est faite par le
  même script, qui vérifie le refus.
- **Point d'attention** : la push protection peut refuser l'envoi du faux secret avant même la
  PR ; c'est le comportement attendu (US3, AS 3.1) ; le script le constate et teste alors le
  contrôle Gitleaks localement.

## R9. Effets sur la fonctionnalité 001

- Les images de `openwebui/compose.yaml` et `cloud-init` devront être épinglées par empreinte
  (`image:tag@sha256:...`) : politique maison et Grype l'exigent. À reporter dans les tâches de
  la 001.
- Le code de la 001 devra passer Ruff (règles `S` comprises), ShellCheck, TFLint, Trivy et
  les politiques maison dès son premier commit.

## R10. Révision pendant l'implémentation (2026-11-26, décisions d'Alexandre)

- **Constat** : la première analyse Grype des images d'outils a trouvé 300 vulnérabilités
  bloquantes dans 5 images officielles pourtant à jour (actionlint 124, Gitleaks 118, Checkov
  25, OSV-Scanner 24, TFLint 9), presque toutes dans des paquets système jamais reconstruits.
  Ruff, ShellCheck, zizmor et Grype n'en avaient aucune.
- **Décision (binaires vérifiés)** : les outils à image vulnérable sont pris sous forme de
  binaires officiels des releases, somme SHA-256 figée dans `securite/outils.lock` (lue dans le
  fichier de sommes de la release, identique à l'empreinte calculée par GitHub), et ces binaires
  sont eux-mêmes analysés par Grype à chaque contrôle `sca`. Résultat : actionlint, TFLint et
  OSV-Scanner n'ont plus aucune vulnérabilité critique ou élevée.
- **Gitleaks remplacé par TruffleHog** v3.100.1 : le binaire de Gitleaks v8.30.1 (aucune
  version depuis mars 2026) gardait 24 vulnérabilités corrigées en amont. TruffleHog tourne avec
  `--no-verification` (aucun secret envoyé à un tiers) ; ses résultats, qui contiennent la valeur
  des secrets, sont écrits hors du dépôt et lus par `verdict_secrets.py`, qui n'affiche que le
  détecteur, le fichier, la ligne et le commit (FR-012). Identifiant d'un faux positif :
  `<commit>:<fichier>:<ligne>`.
- **Checkov remplacé par Trivy** v0.76.2 en mode `config` (règles embarquées,
  `--skip-check-update`, blocage à partir de la gravité moyenne) : binaire seulement, jamais
  l'action ni l'image (R1). Son unique vulnérabilité élevée (GO-2026-6865, plantage zstd) fait
  l'objet d'une exception acceptée pour 90 jours.
- **OpenTofu 1.13.10** (dernière version stable) : 8 vulnérabilités bloquantes dans ses
  dépendances Go (dont GO-2026-6612, critique, côté serveur HTTP/2, qu'OpenTofu n'expose pas) ;
  exceptions individuelles acceptées pour 30 jours (réexamen le 2026-12-26, avant la session).
- **Verdict CodeQL** : `verdict_codeql.py` lit le SARIF produit localement par CodeQL et bloque
  toute alerte de sécurité de niveau `error` ou `warning`, y compris pour une PR de fork qui ne
  peut pas déposer ses résultats (point D3 de l'analyse).
- **Durées mesurées en local** : contrôle complet 2 min 12 s base Grype en cache ; `sca` seul
  3 min 40 s au premier téléchargement de la base.
