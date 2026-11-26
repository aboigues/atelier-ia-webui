---

description: "Liste des tâches de la fonctionnalité 001 : environnement de travaux pratiques pour une session"
---

# Tasks: Environnement de travaux pratiques pour une session de formation

**Input**: Design documents from `specs/001-environnement-tp-session/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: inclus. Le plan prévoit des tests `unittest` (`tests/test_*.py`) et `tests` est un
contrôle requis de `main` (fonctionnalité 002). Chaque fonction pure est écrite après son test,
vu d'abord en échec. Les parcours de bout en bout sont couverts par `atelier local controler`
et `atelier session controler` (FR-013).

**Organization**: tâches groupées par histoire (spec.md) : US1 P1, US2 P2, US3 P3, US4 P4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers différents, aucune dépendance sur une tâche non terminée)
- **[Story]**: histoire de rattachement (US1 à US4)

## Conventions

Structure de `plan.md` : commande `atelier` à la racine, code dans `outils/atelier/`,
configuration d'Open WebUI dans `openwebui/`, infrastructure dans `infra/`, tests dans `tests/`.
Règles transverses pour toutes les tâches :

- français accentué, zéro emoji, aucun nom de client (`CLAUDE.md`) ;
- Python 3.11+, bibliothèque standard uniquement (constitution, principe IV) ;
- toute commande `scw` porte `--profile telemach` ; aucun secret écrit dans un fichier versionné ;
- chaque commit passe les six contrôles requis (`outils/securite/controles-locaux.sh` avant
  chaque push) : Ruff (règles `S`), ShellCheck, OpenTofu et TFLint, Trivy, politiques IaC du
  projet (`outils/securite/politiques_iac.py`), TruffleHog, tests ;
- images Docker et versions figées par empreinte, revérifiées au moment de l'ajout (principe V).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: versions vérifiées, squelette, jeu de session fictif.

- [X] T001 Revérifier les dernières versions stables (pages de releases) d'Open WebUI, de Caddy et du fournisseur OpenTofu `scaleway/scaleway`, résoudre les empreintes des images `ghcr.io/open-webui/open-webui:<version>` et `caddy:<version>` (`docker buildx imagetools inspect`), et consigner versions et empreintes dans `specs/001-environnement-tp-session/research.md` (R1, R7) en remplaçant les valeurs du 2026-11-26 si elles ont changé
- [X] T002 Lire le code d'Open WebUI au tag retenu (téléchargement des fichiers `backend/open_webui/env.py`, `config.py`, `routers/{auths,functions,models,groups,prompts,openai,files}.py`, `functions.py` dans le scratchpad) et consigner dans `specs/001-environnement-tp-session/research.md` (nouvelle section R13) : signature exacte de `inlet` d'un filtre et accès aux fichiers joints, chemins et corps des routes utilisées par `contracts/configuration-openwebui.md`, validation des courriels (acceptation de `@<id>.atelier`), types de fichiers acceptés (`.ifc`) ; corriger le contrat si un nom de variable ou de route diffère
- [X] T003 Créer l'arborescence de `plan.md` : `outils/atelier/__init__.py`, `openwebui/fonctions/`, `openwebui/consignes/`, `infra/scaleway/`, `exemples/session/`
- [X] T004 [P] Écrire le point d'entrée exécutable `atelier` (racine du dépôt, `#!/usr/bin/env python3`) qui exécute `outils/atelier/__main__.py` via `runpy`, et le squelette de `outils/atelier/__main__.py` (`argparse`, groupes `local` et `session`, actions de `contracts/cli.md`, codes de sortie 0/1/2/3)
- [X] T005 [P] Écrire le jeu de session fictif `exemples/session/session.toml` (session `repetition`, client fictif, dates de décembre 2026) et `exemples/session/participants.csv` (10 participants fictifs, dont un doublon de prénom et nom et des accents) selon `contracts/fichiers-session.md`
- [X] T006 [P] Écrire `infra/tarifs.toml` selon `contracts/fichiers-session.md` (tarifs Mistral Medium 3.5 et Small 3.2 relevés sur la page officielle Scaleway, date `verifie_le`, hypothèses de research.md R10)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: lecture des fichiers de session, appels `scw`, client REST d'Open WebUI.

**CRITICAL**: aucune histoire ne commence avant la fin de cette phase.

- [X] T007 [P] Test `tests/test_config.py` : lecture de `session.toml` et validation de `data-model.md` Session.`id`, Session.`debut` et Session.`fin`, Session.`type_instance`, Session.`modele_reference`, Session.`modele_secours` (valeurs par défaut) et calcul de Session.`echeance_garde_fou` ; lecture de `participants.csv` (séparateur `;` ou `,`, en-tête `prenom;nom`, 1 à 15 lignes, UTF-8) ; refus de `infra/tarifs.toml` daté de plus de 30 jours ; code 2 sur fichier absent ou invalide
- [X] T008 Écrire `outils/atelier/config.py` conforme à T007 et `contracts/fichiers-session.md` : valide `data-model.md` Session.`id`, .`debut`, .`fin`, .`type_instance`, .`modele_reference`, .`modele_secours`, calcule .`echeance_garde_fou`, et ne recopie jamais Session.`client` dans un fichier versionné ni un journal ; lit Compte.`prenom` et Compte.`nom` depuis `participants.csv`
- [X] T009 [P] Écrire `outils/atelier/scw.py` : clé et projet lus par `scw --profile telemach config get secret-key|default-project-id` (jamais journalisés), liste des modèles `GET https://api.scaleway.ai/<projet>/v1/models`, prix horaire d'un type d'instance (`scw --profile telemach instance server-type list zone=fr-par-1 -o json`), inventaire des ressources par étiquette `atelier-session=<id>` (instances, volumes, IP, groupes de sécurité, applications et clés IAM, enregistrements DNS de la zone `atelier.telemach-learning.fr`) ; appels `subprocess` en liste d'arguments, sans shell (`# noqa: S603` justifié)
- [X] T010 [P] Test `tests/test_openwebui.py` : client REST contre un faux serveur `http.server` local (connexion administrateur, jeton porté par en-tête, erreurs HTTP traduites en exceptions lisibles, attente de `/health` avec délai maximal)
- [X] T011 Écrire `outils/atelier/openwebui.py` : client REST minimal (`urllib`, jeton administrateur, JSON), conforme à T010 et aux routes consignées en T002 ; fonctions idempotentes « créer ou mettre à jour » (connexion Scaleway, fonction, modèle, groupe, utilisateur, consigne) utilisées par toutes les histoires

**Checkpoint**: `python3 -m unittest discover -s tests -t .` vert ; `./atelier --help` liste les actions de `contracts/cli.md`.

---

## Phase 3: User Story 1 - Démonstration locale sur le jeu fictif (Priority: P1) MVP

**Goal**: `./atelier local demarrer` lance Open WebUI relié à Scaleway, configuré, jeu fictif chargé ; les scénarios 1 à 3 se rejouent dans le navigateur.

**Independent Test**: `./atelier local demarrer` (moins de 5 min), `./atelier local controler` tout OK, puis scénarios 1 à 3 de `quickstart.md` (scénario A) comparés à `exemples/bloc-operatoire/CORRIGE.md`.

### Tests for User Story 1

- [X] T012 [P] [US1] Test `tests/test_local.py` : construction de l'environnement passé à `docker compose` (clé Scaleway transmise par variable d'environnement du processus, jamais écrite sur disque ; `OPENAI_API_BASE_URL` avec l'identifiant de projet), génération idempotente des identifiants formateur locaux dans `sessions/local/identifiants.txt`, commande `docker compose` sans le profil `session`

### Implementation for User Story 1

- [X] T013 [P] [US1] Écrire `openwebui/compose.yaml` selon `contracts/configuration-openwebui.md` (Services Docker) : service `openwebui` sur l'image figée par empreinte de T001, publié sur `127.0.0.1:3000` seulement, volume `donnees-openwebui`, `env_file: env.commun` et secrets par variables ; service `caddy` (image figée) dans le profil `session` seulement ; ni `privileged`, ni capacité ajoutée, `read_only` lorsque l'image le permet
- [X] T014 [P] [US1] Écrire `openwebui/env.commun` : toutes les variables non secrètes de `contracts/configuration-openwebui.md`, avec les noms confirmés en T002 (télémétrie coupée, `OFFLINE_MODE`, `BYPASS_EMBEDDING_AND_RETRIEVAL`, `ENABLE_SIGNUP=false`, `ENABLE_PERSISTENT_CONFIG=false`, etc.)
- [X] T015 [P] [US1] Écrire `openwebui/modele-assistant.toml` : modèles `assistant-bureau-etudes` (base Session.`modele_reference` de `data-model.md`) et `assistant-secours` (base Session.`modele_secours`), invite système reprise de `SYSTEME` dans `exemples/bloc-operatoire/demo.py`, `temperature` 0,1, capacités `vision` et `file_upload`
- [X] T016 [P] [US1] Écrire les consignes de départ `openwebui/consignes/scenario-1.md` à `scenario-5.md` (textes des scénarios de `exemples/bloc-operatoire/demo.py`) et `fiche-controle-plan.md`, chacune avec un en-tête `commande`, `titre` conforme à `data-model.md` Consigne.`commande` et Consigne.`titre` ; contenu sans aucun extrait de document client (Consigne.`contenu`)
- [X] T017 [US1] Implémenter dans `outils/atelier/openwebui.py` la fonction `configurer(environnement)` qui rejoue dans l'ordre les appels 1 à 4 et 7 de `contracts/configuration-openwebui.md` (connexion Scaleway avec `model_ids` limités, modèles personnalisés depuis `openwebui/modele-assistant.toml`, consignes depuis `openwebui/consignes/`), idempotente (FR-002, FR-014)
- [X] T018 [US1] Écrire `outils/atelier/local.py` (conforme à T012) et brancher `atelier local demarrer` et `atelier local arreter [--effacer]` dans `outils/atelier/__main__.py` : clé lue par `scw.py`, `docker compose -f openwebui/compose.yaml up -d`, attente de `/health`, `configurer`, affichage de l'adresse et des identifiants locaux (FR-001, AS 1.1)
- [X] T019 [US1] Écrire `outils/atelier/controle.py` (étapes 1 à 5, 7 et 8 de `contracts/cli.md`, « Contrôle de bout en bout ») et brancher `atelier local controler` : comptes de contrôle créés puis supprimés, dépôt de `exemples/bloc-operatoire/plan-salle3-indB.png`, vérification de la réponse du scénario 1 (indice B, au moins 8 repères E01 à E10, portes P1 à P4), isolement entre deux comptes, inscription libre refusée ; l'étape 8 (connexions sortantes) relève les destinations du conteneur pendant le scénario et échoue hors liste autorisée de research.md R2 (FR-012, FR-013)
- [X] T020 [US1] Exécuter le scénario A de `quickstart.md` en local, comparer les réponses des scénarios 1 à 3 à `exemples/bloc-operatoire/CORRIGE.md` et consigner les écarts éventuels dans `specs/001-environnement-tp-session/research.md` (section R13) ; ajuster `openwebui/modele-assistant.toml` si l'invite doit être corrigée

**Checkpoint**: US1 livrée, démontrable au client sans dépense d'hébergement.

---

## Phase 4: User Story 2 - Interroger une maquette IFC en langage courant (Priority: P2)

**Goal**: une maquette IFC déposée est réduite à un tableau des espaces, affiché comme source et envoyé au modèle ; un PDF de plan vectoriel déclenche un avertissement.

**Independent Test**: déposer `exemples/bloc-operatoire/maquette-bloc.ifc` et demander les salles sans plafond soufflant : la source « Tableau des espaces » s'affiche et la réponse cite SO2 et SO4 (scénario B de `quickstart.md`).

### Tests for User Story 2

- [X] T021 [P] [US2] Test `tests/test_filtre_ifc.py` selon `contracts/filtre-ifc.md` : `espaces_ifc` sur `exemples/bloc-operatoire/maquette-bloc.ifc` (4 salles SO1 à SO4, SO2 `PlafondSoufflant` = non, SO4 `SurpressionPa` = 10), colonnes de `data-model.md` Tableau des espaces IFC.`code` et .`nom` (décodage `\X2\...\X0\`), entités sur plusieurs lignes, schémas IFC2X3 et IFC4, tri par code, propriétés absentes laissées vides, `ErreurIFC` sur fichier tronqué et au-delà de 2 000 espaces ; `tableau_markdown` ; détection d'un PDF au texte pauvre (moins de 200 caractères par page)

### Implementation for User Story 2

- [X] T022 [US2] Écrire `openwebui/fonctions/filtre_ifc.py` (un seul fichier, bibliothèque standard, aucun appel réseau) conforme à T021 et `contracts/filtre-ifc.md`, colonnes `data-model.md` Tableau des espaces IFC.`code` et .`nom` puis une colonne par propriété : fonctions pures, classe `Filter` avec `Valves` (`taille_max_mo`, `espaces_max`) et `inlet` selon la signature confirmée en T002 (remplacement du contenu du fichier IFC, source émise par `__event_emitter__`, retrait du fichier en cas d'erreur, avertissement PDF)
- [X] T023 [US2] Étendre `configurer` dans `outils/atelier/openwebui.py` : création ou mise à jour de la fonction `filtre_ifc` (appel 2 de `contracts/configuration-openwebui.md`), activation et rattachement aux deux modèles personnalisés ; autoriser l'extension `.ifc` au dépôt si T002 l'a montré nécessaire
- [X] T024 [US2] Ajouter l'étape 6 (dépôt de `maquette-bloc.ifc`, réponse citant SO2 et SO4) à `outils/atelier/controle.py`, puis exécuter le scénario B de `quickstart.md` en local (maquette valide, puis fichier tronqué)

**Checkpoint**: US1 et US2 fonctionnent en local.

---

## Phase 5: User Story 3 - Session hébergée pour les participants (Priority: P3)

**Goal**: `./atelier session creer` crée l'environnement à Paris en HTTPS, avec un compte par participant et la bibliothèque de consignes partagée, en moins de 30 minutes contrôle compris.

**Independent Test**: scénario C de `quickstart.md` jusqu'à `session controler --charge 10` inclus, sur la session fictive `repetition`.

### Tests for User Story 3

- [X] T025 [P] [US3] Test `tests/test_comptes.py` : génération de `data-model.md` Compte.`courriel` (normalisation sans accent, suffixe numérique en cas de doublon, domaine `@<id>.atelier`), Compte.`mot_de_passe` (4 mots tirés par `secrets`, au moins 16 caractères), Compte.`role` ; fiches d'identifiants au format de `contracts/fichiers-session.md` écrites sous `sessions/<id>/identifiants/` ; aucun accès réseau
- [X] T026 [P] [US3] Test `tests/test_cout.py` : estimation de research.md R10 à partir d'un prix horaire et de tarifs injectés (instance, IP, modèle, total arrondi), refus des tarifs datés de plus de 30 jours

### Implementation for User Story 3

- [X] T027 [P] [US3] Écrire `outils/atelier/comptes.py` conforme à T025 : produit `data-model.md` Compte.`courriel`, Compte.`mot_de_passe` et Compte.`role` à partir de Compte.`prenom` et Compte.`nom`
- [X] T028 [P] [US3] Écrire `outils/atelier/cout.py` conforme à T026 et brancher `atelier session cout` (FR-015)
- [X] T029 [P] [US3] Écrire `infra/scaleway/versions.tf` (OpenTofu `>= 1.13.10`, fournisseur `scaleway/scaleway` à la version de T001, backend local dont le chemin est passé à `tofu init`) et `infra/scaleway/variables.tf` (identifiant de session validé comme `data-model.md` Session.`id`, type d'instance Session.`type_instance`, échéance Session.`echeance_garde_fou`, empreintes des images, sans valeur secrète par défaut)
- [X] T030 [US3] Écrire `infra/scaleway/main.tf` selon `data-model.md` « Ressources Scaleway d'une session » : IP, groupe de sécurité (politique d'entrée `drop`, entrée 80 et 443 seulement), instance `fr-par-1` Ubuntu 24.04 avec volume racine détruit avec elle, enregistrement A `<id>` dans la zone `atelier.telemach-learning.fr`, application, politique (`GenerativeApisModelAccess` seulement) et clé IAM (`expires_at` = échéance) ; étiquette `atelier-session=<id>` sur toute ressource qui l'accepte ; `infra/scaleway/outputs.tf` (adresse, IP, clé IAM marquée `sensitive`) ; verrouiller le fournisseur (`tofu providers lock -platform=linux_amd64`) et versionner `infra/scaleway/.terraform.lock.hcl`
- [X] T031 [US3] Écrire `infra/scaleway/cloud-init.yaml.tftpl` : installation de Docker depuis le dépôt officiel, dépôt de `compose.yaml`, `env.commun` et `Caddyfile`, variables secrètes dans un fichier `0600` hors image, images tirées par empreinte, démarrage, minuteur systemd du garde-fou (arrêt des conteneurs, effacement du volume de données, extinction à Session.`echeance_garde_fou` de `data-model.md`) ; aucun accès SSH
- [X] T032 [P] [US3] Écrire `openwebui/Caddyfile` (`<id>.atelier.telemach-learning.fr`, certificat automatique, `reverse_proxy openwebui:8080`, en-têtes de sécurité HSTS, `X-Content-Type-Options`, `Referrer-Policy`, journal sans corps de requête)
- [X] T033 [US3] Étendre `configurer` dans `outils/atelier/openwebui.py` pour la session : groupe `participants-<id>` (appel 5), comptes (appel 6, idempotent par courriel, `data-model.md` Compte.`role`), consignes partagées en lecture au groupe (appel 7, `data-model.md` Consigne.`auteur`) (FR-006 à FR-009)
- [X] T034 [US3] Écrire `outils/atelier/session.py` et brancher `atelier session creer` : coût affiché et confirmation (`--oui`), `tofu init` et `apply` avec l'état dans `sessions/<id>/tofu/`, attente du DNS et du certificat, `configurer`, fiches d'identifiants via `comptes.py`, puis `session controler` ; relançable sans recréer un compte existant (AS 3.1, SC-006)
- [X] T035 [US3] Brancher `atelier session controler [--charge N]` dans `outils/atelier/controle.py` (même contrôle qu'en local sur l'adresse HTTPS, certificat vérifié ; `--charge N` : N scénarios 1 en parallèle, échec au-delà de 60 s ou sur réponse 429) et `atelier session statut` (état déduit de `data-model.md` Session, heures avant l'échéance, rappel de purge)
- [X] T036 [US3] Mesurer la durée du contrôle `sca` avec les images d'Open WebUI et de Caddy (point P1 de l'analyse de la 002) ; si elle dépasse 10 minutes, proposer à Alexandre une mise en cache, sans réduire le périmètre analysé ; traiter les vulnérabilités bloquantes de ces images selon `securite/exceptions.toml` (exception soumise à Alexandre, jamais ajoutée sans son accord)
- [ ] T037 [US3] (En partie fait le 2026-11-26 : création, contrôle et charge à 10 OK, research.md R13 ; restent SC-004 à la main et l'interface sous CSP.) Exécuter le scénario C de `quickstart.md` jusqu'à `session controler --charge 10` sur la session fictive `repetition`, puis vérifier à la main SC-004 (connexion et première demande en moins de 3 minutes) et l'isolement entre participants (AS 3.2, AS 3.3)

**Checkpoint**: une session de répétition existe chez Scaleway ; ne pas la laisser en place (enchaîner US4).

---

## Phase 6: User Story 4 - Fin de session et purge vérifiable (Priority: P4)

**Goal**: export des consignes sans document client, purge complète et reprenable, rapport sans nom ni document.

**Independent Test**: fin du scénario C de `quickstart.md` : `session exporter`, `session purger`, `session verifier-purge` à 0, inventaire `scw` vide, `sessions/repetition/` absent.

### Tests for User Story 4

- [X] T038 [P] [US4] Test `tests/test_purge.py` : rapport de purge au format de `contracts/fichiers-session.md` à partir d'un inventaire injecté (purge complète, purge incomplète avec restes listés), absence de tout nom de participant et de document dans le rapport, suppression de `sessions/<id>/` seulement après un inventaire vide
- [X] T039 [P] [US4] Test `tests/test_export.py` : export des consignes en JSON et Markdown avec Consigne.`commande`, Consigne.`titre`, Consigne.`contenu` et Consigne.`auteur` réduit à « formateur » ou « participant » (`data-model.md`), sans nom de personne

### Implementation for User Story 4

- [X] T040 [US4] Écrire `outils/atelier/purge.py` (conforme à T038) et brancher `atelier session purger [--oui]` et `atelier session verifier-purge` : `tofu destroy` (relançable), inventaire par étiquette via `scw.py`, suppression de `sessions/<id>/`, rapport `exports/<id>/rapport-purge.md` ; code 1 si une ressource subsiste (FR-011, AS 4.2, AS 4.3, SC-005)
- [X] T041 [US4] Implémenter `atelier session exporter` dans `outils/atelier/session.py` (conforme à T039) : `exports/<id>/consignes.json` et `consignes.md` (FR-010, AS 4.1)
- [ ] T042 [US4] (En partie fait le 2026-11-26 : export et purge complète vérifiée par scw, research.md R13 ; reste la reprise après interruption.) Terminer le scénario C de `quickstart.md` sur la session `repetition` (export, purge, interruption de la purge puis reprise, vérification `scw --profile telemach` et `git status`) et consigner le résultat dans `specs/001-environnement-tp-session/research.md` (R13)

**Checkpoint**: cycle complet d'une session démontré, rien ne subsiste chez Scaleway ni dans `sessions/`.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T043 Exécuter le scénario D de `quickstart.md` (clé invalide, PDF vectoriel, garde-fou sur une session de répétition à échéance courte, accès par partage de connexion) et consigner les résultats dans `specs/001-environnement-tp-session/research.md` (R13)
- [X] T044 [P] Mettre à jour `README.md` (démarrage local, cycle d'une session, renvoi vers `specs/001-environnement-tp-session/quickstart.md`) et `CLAUDE.md` (état de la fonctionnalité 001)
- [ ] T045 Réexaminer avant le 2026-12-26 les exceptions OpenTofu de `securite/exceptions.toml` (nouvelle version corrigée ou prolongation acceptée par Alexandre) ; relire les en-têtes `x-ratelimit-*` de Scaleway si la validation d'identité est passée et mettre à jour research.md R11
- [X] T046 Avant commit : `outils/securite/controles-locaux.sh` complet au vert ; `git status` sans fichier de `sessions/`, `exports/`, `identifiants/`, `documents-clients/` ; aucun emoji ni nom de client ; puis commit, push et PR vers `main` (sans merge)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (T001-T006) -> Foundational (T007-T011) -> histoires. T001 et T002 conditionnent toutes les tâches qui citent des versions, des empreintes, des variables ou des routes d'Open WebUI.
- US1 (T012-T020) : socle local, prérequis de toutes les autres histoires.
- US2 (T021-T024) : après US1 (même `configurer` et même contrôle) ; indépendante de US3 et US4.
- US3 (T025-T037) : après US1 ; US2 recommandée avant (le contrôle de session inclut l'IFC), sinon l'étape 6 du contrôle est ajoutée ensuite.
- US4 (T038-T042) : après US3 (une session doit exister pour être purgée) ; à enchaîner sans délai après T037 pour ne pas laisser de ressource facturée.
- Polish : T043 après US4 ; T044 à tout moment après US1 ; T045 à date fixe ; T046 en dernier.

### Within Each User Story

- Tests écrits et vus en échec avant le code qu'ils couvrent.
- Configuration (`openwebui/`, `infra/`) avant les commandes qui l'utilisent ; commandes avant les scénarios de validation.

### Parallel Opportunities

- Phase 1 : T004, T005, T006 en parallèle après T003.
- Phase 2 : T007, T009, T010 en parallèle.
- US1 : T012 à T016 en parallèle.
- US3 : T025, T026, T029, T032 en parallèle ; puis T027 et T028.
- US4 : T038 et T039 en parallèle.

## Parallel Example: User Story 1

```text
T012 [US1] tests/test_local.py
T013 [US1] openwebui/compose.yaml
T014 [US1] openwebui/env.commun
T015 [US1] openwebui/modele-assistant.toml
T016 [US1] openwebui/consignes/*.md
```

## Implementation Strategy

### MVP (User Story 1)

1. Phases 1 et 2.
2. US1 : démonstration locale complète.
3. Valider sur le scénario A de `quickstart.md` : jalon de la spec, au plus tard le 2026-12-03.

### Livraison incrémentale

1. US1 puis US2 : démonstration locale complète (plans et maquette), une PR chacune.
2. US3 puis US4 enchaînées dans la même PR : une session créée doit toujours pouvoir être purgée.
3. Session de répétition complète (scénario C) avant le 2026-12-09.

## Notes

- [P] = fichiers différents, aucune dépendance.
- Toute ressource Scaleway créée pendant les tests (T037, T042, T043) est purgée le jour même.
- Toute exception de sécurité nouvelle (T036) est soumise à Alexandre avant d'être écrite.
