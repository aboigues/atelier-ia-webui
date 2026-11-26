# Implementation Plan: Environnement de travaux pratiques pour une session de formation

**Branch**: `001-environnement-tp-session` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-environnement-tp-session/spec.md`

## Summary

Remplacer la démo en ligne de commande (`exemples/bloc-operatoire/demo.py`) par un
environnement web : Open WebUI v0.13.5 relié aux modèles Mistral de Scaleway Generative APIs
(Paris), configuré entièrement en code, sans télémétrie ni autre fournisseur. Un modèle
personnalisé « Assistant bureau d'études » (Mistral Medium 3.5, vision, invite système de la
démo) lit les plans en image ; un filtre Open WebUI en Python standard convertit les maquettes
IFC en tableau des espaces. Le même `compose.yaml` tourne sur le poste du formateur et, pour une
session, sur une instance Scaleway `DEV1-L` créée par OpenTofu, derrière Caddy (HTTPS
automatique) à l'adresse `<id>.atelier.telemach-learning.fr`. Une commande unique `atelier`
(Python, bibliothèque standard) démarre, configure, contrôle, chiffre, exporte et purge ; la
purge détruit toutes les ressources étiquetées de la session et produit un rapport vérifiable.

## Technical Context

**Language/Version**: Python 3.11+ (stdlib seule, `tomllib`) pour `atelier` et le filtre IFC ; HCL OpenTofu v1.13.10 ; YAML cloud-init et Docker Compose

**Primary Dependencies**: Open WebUI `v0.13.5` (image `ghcr.io/open-webui/open-webui:v0.13.5`) ; Caddy `2.11.9` ; fournisseur OpenTofu `scaleway/scaleway` `v2.93.0` ; CLI `scw` (profil `telemach`) ; Docker Compose

**Storage**: SQLite et répertoire `uploads/` d'Open WebUI dans un volume Docker (local) ou sur le disque racine de l'instance (session), détruits avec l'environnement ; fichiers de session locaux sous `sessions/<id>/` et `exports/<id>/` (ignorés par Git)

**Testing**: `python3 -m unittest` (conversion IFC, génération des comptes, calcul de coût, rapport de purge) ; contrôle de bout en bout `atelier local controler` / `atelier session controler [--charge 10]` (FR-013)

**Target Platform**: poste formateur Linux (WSL2) avec Docker ; instance Scaleway `fr-par-1` Ubuntu 24.04 ; navigateurs récents des participants

**Project Type**: outil en ligne de commande d'exploitation + configuration d'application web tierce + infrastructure en code

**Performance Goals**: démarrage local < 5 min ; création de session < 30 min contrôle compris ; réponse < 60 s par demande avec 10 participants simultanés

**Constraints**: aucune donnée vers un tiers hors Scaleway (FR-012) ; aucun secret ni document client versionné ; versions figées ; durée de vie bornée (garde-fou fin + 48 h) ; coût affiché avant création (~35 EUR par session, `research.md` R10)

**Scale/Scope**: 1 formateur + 10 participants (15 au plus), 2 jours, une session à la fois ; maquettes IFC jusqu'à 200 Mo / 2 000 espaces

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principe | Vérification | Avant | Après conception |
|---|---|---|---|
| I. Confidentialité | Documents clients uniquement dans Open WebUI (instance détruite) ; `sessions/`, `exports/`, `identifiants/` ignorés ; exemples de fichiers de session fictifs ; purge unique avec rapport sans nom ni document ; télémétrie coupée et vérifiée par le contrôle | OK | OK (R2, R9, `contracts/fichiers-session.md`) |
| II. Modèles ouverts en France | Seule connexion : Scaleway Generative APIs `fr-par`, liste blanche Mistral Medium 3.5 / Small 3.2 ; aucune mention « SecNumCloud » ; `--profile telemach` partout | OK | OK (R3, `contracts/configuration-openwebui.md`) |
| III. Reproductible et éphémère | Docker Compose partagé local/session, OpenTofu pour Scaleway, configuration Open WebUI par variables + API rejouées, `ENABLE_PERSISTENT_CONFIG=false` ; une commande crée, une détruit ; coût affiché et borné. Exception unique : délégation DNS de `atelier.telemach-learning.fr`, faite une fois chez le registrar (hors Scaleway, non scriptable), documentée | OK | OK (R7, R8, R10) |
| IV. Au plus simple | Configuration d'Open WebUI plutôt que code ; un seul fichier de filtre en Python standard ; pas de stockage objet, base managée, SSH ni Pipelines ; chaque élément se rattache aux modules 1 à 3 de l'atelier | OK | OK |
| V. Versions et secrets | Versions vérifiées le 2026-11-26 et figées (Open WebUI, Caddy, OpenTofu, fournisseur) ; clé personnelle lue à l'exécution et jamais écrite ; clé IAM dédiée à la session, expirante, détruite ; état OpenTofu (qui la contient) supprimé à la purge | OK | OK |
| VI. Langue et style | Code, interface, messages, documentation en français accentué, sans emoji | OK | OK |

Aucune violation : la section Complexity Tracking reste vide.

## Project Structure

### Documentation (this feature)

```text
specs/001-environnement-tp-session/
├── plan.md              # ce fichier
├── research.md          # phase 0 : décisions et versions vérifiées
├── data-model.md        # phase 1 : entités, états, ressources Scaleway
├── quickstart.md        # phase 1 : scénarios de validation
├── contracts/
│   ├── cli.md                       # commande atelier
│   ├── configuration-openwebui.md   # variables, appels d'API, services Docker
│   ├── filtre-ifc.md                # filtre de conversion IFC
│   └── fichiers-session.md          # session.toml, participants.csv, exports, rapport
└── tasks.md             # phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
atelier                          # point d'entrée exécutable (python3), délègue à outils/atelier
outils/atelier/
├── __main__.py                  # analyse des arguments, groupes local / session
├── config.py                    # lecture session.toml, participants.csv, tarifs.toml
├── scw.py                       # appels scw --profile telemach (clé, projet, prix, inventaire)
├── openwebui.py                 # client REST minimal (urllib) et configuration idempotente
├── comptes.py                   # courriels et mots de passe générés, fiches d'identifiants
├── local.py                     # docker compose demarrer / arreter
├── session.py                   # tofu apply / destroy, statut, export
├── controle.py                  # contrôle de bout en bout et charge
├── cout.py                      # estimation du coût
└── purge.py                     # inventaire par étiquette et rapport
openwebui/
├── compose.yaml                 # openwebui + caddy (profil session)
├── Caddyfile
├── env.commun                   # variables non secrètes
├── modele-assistant.toml        # invite système et réglages des modèles personnalisés
├── fonctions/filtre_ifc.py      # filtre IFC / avertissement PDF
└── consignes/*.md               # consignes de départ (scénarios 1 à 5, fiches de contrôle)
infra/
├── tarifs.toml                  # tarifs datés du modèle et hypothèses de coût
└── scaleway/
    ├── versions.tf              # OpenTofu et fournisseur figés
    ├── variables.tf
    ├── main.tf                  # IP, groupe de sécurité, instance, DNS, IAM
    ├── outputs.tf
    └── cloud-init.yaml.tftpl    # Docker, compose, minuteur garde-fou
exemples/
├── bloc-operatoire/             # existant, inchangé
└── session/                     # session.toml et participants.csv fictifs
tests/
├── test_filtre_ifc.py
├── test_comptes.py
├── test_cout.py
└── test_purge.py
```

**Structure Decision**: un dépôt unique sans application maison : la commande `atelier`
(`outils/atelier/`) pilote une application tierce configurée (`openwebui/`) et une
infrastructure en code (`infra/scaleway/`). Le filtre IFC est un fichier autonome parce qu'Open
WebUI charge chaque fonction comme un module unique ; les tests l'importent directement.
`demo.py` reste tel quel comme démo de secours en ligne de commande.

## Phases suivantes et points à confirmer à l'implémentation

- Confirmer contre le code du tag `v0.13.5` : signature `inlet` des filtres et accès aux
  fichiers, chemins et corps exacts des routes `functions`, `models`, `groups`, `prompts`,
  `openai/config/update`, acceptation des courriels en `@<id>.atelier` et de l'extension `.ifc`.
- Fait le 2026-11-26 : délégation DNS de `atelier.telemach-learning.fr`, OpenTofu `v1.13.10`
  sur le poste, mesure des quotas (R11). En attente : validation d'identité de l'organisation
  Scaleway (hausse des quotas) ; relire les en-têtes `x-ratelimit-*` une fois validée.
- Contrôles de sécurité (fonctionnalité 002, research.md R9 et R10) : images de
  `openwebui/compose.yaml` et de cloud-init épinglées par empreinte (`image:tag@sha256:...`),
  code conforme aux six contrôles requis dès le premier commit (Ruff règles `S`, ShellCheck,
  OpenTofu et TFLint, Trivy, politiques IaC maison, TruffleHog, tests). Les exceptions
  OpenTofu 1.13.10 sont à réexaminer avant le 2026-12-26.
- Jalons de la spec : local opérationnel le 2026-12-03 ; session de répétition complète
  (scénario C du quickstart) avant le 2026-12-09.

## Complexity Tracking

Aucune violation de la constitution à justifier.
