# Implementation Plan: Chaîne de contrôle de sécurité du dépôt

**Branch**: `002-chaine-controle-securite` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-chaine-controle-securite/spec.md`

## Summary

Mettre en œuvre le principe VII avant tout code de la fonctionnalité 001 : deux workflows
GitHub Actions (contrôles de PR et analyse hebdomadaire) qui exécutent six contrôles requis
(`lint`, `sast-codeql`, `sca`, `iac`, `secrets`, `tests`), un ruleset versionné qui protège
`main` sans contournement possible, la détection de secrets avec blocage à l'envoi, et une
gestion d'exceptions datées. Leçon de la compromission de `trivy-action` (mars 2026) : les
outils tournent dans leurs images officielles épinglées par empreinte, listées dans un fichier
unique partagé avec le contrôle local ; seules deux actions GitHub, épinglées par SHA, sont
utilisées.

## Technical Context

**Language/Version**: YAML GitHub Actions ; Python 3.11+ (stdlib) pour les scripts de verdict, d'exceptions, d'épinglage et de ruleset ; Bash (ShellCheck) pour le contrôle local et la démonstration

**Primary Dependencies**: `actions/checkout` v7.0.1 et `github/codeql-action` v4.39.5 (SHA) ; images épinglées : Ruff 0.17.6, ShellCheck v0.11.0, zizmor 1.33.1, Grype v0.122.1 ; binaires officiels à somme figée : actionlint 1.7.12, TFLint v0.66.0, OSV-Scanner v2.7.1, TruffleHog v3.100.1, Trivy v0.76.2, OpenTofu 1.13.10 (research.md R10) ; yamllint 1.38.0 (pip, empreintes) ; `gh` pour le ruleset

**Storage**: fichiers versionnés (`securite/`, `.github/`) ; résultats dans GitHub (résumés de tâches, onglet Sécurité)

**Testing**: `unittest` (verdict des vulnérabilités, exceptions, épinglage, politiques IaC) ; script de démonstration de bout en bout sur une PR jetable

**Target Platform**: GitHub (dépôt public), runners `ubuntu-24.04` ; poste du formateur (WSL2, Docker)

**Project Type**: chaîne d'intégration continue et outillage de sécurité du dépôt

**Performance Goals**: contrôles d'une PR < 10 min dans 90 % des cas ; chaque tâche < 15 min

**Constraints**: aucune action tierce hors GitHub ; contrôles requis liés à l'application GitHub Actions et sans condition `if:` ; dépôt SARIF non bloquant pour les PR de fork, verdict toujours bloquant ; tout outil figé par version et empreinte ; `contents: read` par défaut ; aucun secret pour les PR de fork ; aucun contournement de `main`, administrateur compris

**Scale/Scope**: un mainteneur, un dépôt, 6 contrôles requis, 2 workflows, ~6 scripts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principe | Vérification | Avant | Après conception |
|---|---|---|---|
| I. Confidentialité | Détection de secrets sur tout l'historique et blocage à l'envoi ; aucun document client analysé ni publié (les rapports ne citent que le dépôt) | OK | OK |
| II. Modèles ouverts | Non concerné (aucun appel de modèle) | OK | OK |
| III. Reproductible | Workflows, ruleset, exceptions, versions d'outils : tout en fichiers versionnés ; ruleset appliqué et vérifié par commande | OK | OK (R5) |
| IV. Au plus simple | Six contrôles, deux actions, un fichier d'outils partagé avec le local ; pas de `pre-commit` ni de fournisseur GitHub OpenTofu. Le surcroît d'outils est imposé par VII, qui prime en cas d'arbitrage | OK | OK |
| V. Versions et secrets | Versions relevées le 2026-11-26, figées par empreinte ; aucun secret requis par les workflows | OK | OK (R2) |
| VI. Langue et style | Scripts, messages et rapports en français sans emoji | OK | OK |
| VII. Sécurité et gates | Objet même de la fonctionnalité : protection de `main` sans contournement, contrôles bloquants des six familles, seuil clarifié (R3), exceptions datées (R4), actions SHA, permissions minimales, Dependabot hors périmètre | OK | OK |

Aucune violation.

## Project Structure

### Documentation (this feature)

```text
specs/002-chaine-controle-securite/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── controles.md      # contrôles requis et workflows
│   ├── commandes.md      # scripts
│   └── exceptions.md     # format du fichier d'exceptions
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
.github/
├── workflows/
│   ├── controles.yml               # 6 contrôles requis (PR et push sur main)
│   └── analyse-hebdomadaire.yml    # SCA et zizmor chaque lundi
├── rulesets/main.json              # protection de main
└── codeql/codeql-config.yml        # suites et chemins exclus
securite/
├── outils.lock                     # images épinglées (nom=image:version@sha256)
├── exceptions.toml                 # exceptions datées (classe elevee-sans-correctif)
├── trufflehog-exclusions.txt       # binaires du jeu fictif exclus de la recherche de secrets
└── requirements-yamllint.txt       # yamllint avec empreintes
outils/securite/
├── lib.sh                          # lancement d'un outil épinglé (outils.lock)
├── controle.sh                     # un sous-programme par contrôle (CI et local)
├── politiques_iac.py               # politiques IaC maison
├── controles-locaux.sh
├── regles_github.py
├── exceptions.py
├── verdict_vulnerabilites.py
├── verdict_secrets.py              # verdict TruffleHog, valeurs jamais affichées
├── verdict_codeql.py               # verdict CodeQL sur SARIF local (PR de fork comprises)
├── verifier_epinglage.py
└── demonstration.sh
pyproject.toml                      # configuration Ruff (règles, exclusions Spec-Kit)
.yamllint.yaml
.tflint.hcl
tests/securite/
├── test_verdict_vulnerabilites.py
├── test_exceptions.py
├── test_verifier_epinglage.py
├── test_regles_github.py
├── test_verdict_secrets.py
├── test_verdict_codeql.py
└── test_politiques_iac.py          # politiques maison, actives dès que infra/ et openwebui/ existent
```

**Structure Decision**: la configuration des outils vit sous `securite/` (données) et leur
orchestration sous `outils/securite/` (code), à côté de `outils/atelier/` prévu par la 001.
Les fichiers de configuration que les outils cherchent à la racine (`pyproject.toml`,
`.yamllint.yaml`, `.tflint.hcl`) y restent.

## Ordre de mise en service

1. Workflows, scripts et tests sur cette branche ; la PR doit passer ses propres contrôles.
2. Merge par Alexandre (dernier merge possible hors ruleset).
3. `regles_github.py appliquer`, puis `verifier`, puis `demonstration.sh`.
4. Reprise de la 001 (`/speckit-tasks`) sur une nouvelle branche, en reportant R9 (images
   Compose épinglées par empreinte).

## Complexity Tracking

Aucune violation de la constitution à justifier.
