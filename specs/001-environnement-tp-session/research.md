# Recherche (phase 0) : environnement de travaux pratiques pour une session

Date : 2026-11-26. Versions vérifiées le jour même (API GitHub releases, catalogue Scaleway
interrogé avec `scw --profile telemach`), jamais tirées de mémoire.

## R1. Interface : Open WebUI v0.13.5

- **Décision** : image `ghcr.io/open-webui/open-webui:v0.13.5` (publiée le 2026-11-25), variante
  standard (non `cuda`, non `ollama`).
- **Raison** : dernière version stable ; dépôt de fichiers, images transmises aux modèles dotés
  de la capacité « vision », bibliothèque de consignes (« Prompts ») avec droits par groupe,
  fonctions de filtre en Python, API REST d'administration complète (`/api/v1/auths/add`,
  `/api/v1/groups`, `/api/v1/prompts`, `/api/v1/functions`, `/api/v1/models`).
- **Alternatives** : LibreChat (configuration YAML plus lourde, MongoDB obligatoire) ; interface
  maison (contraire au principe IV).

## R2. Aucune donnée vers un tiers (FR-012)

Vérifié dans `Dockerfile`, `backend/open_webui/env.py` et `config.py` au tag `v0.13.5` :

- **Décision** :
  - Télémétrie : déjà neutralisée par l'image (`SCARF_NO_ANALYTICS=true`, `DO_NOT_TRACK=true`,
    `ANONYMIZED_TELEMETRY=false`) ; on les répète explicitement. `ENABLE_OTEL=false` (défaut).
  - `OFFLINE_MODE=true` : force `HF_HUB_OFFLINE=1` et coupe `ENABLE_VERSION_UPDATE_CHECK`.
  - Documents : `BYPASS_EMBEDDING_AND_RETRIEVAL=true` (le texte extrait est envoyé en entier au
    modèle, pas de découpage ni de base vectorielle) et `RAG_EMBEDDING_ENGINE=openai` pointé sur
    Scaleway (`bge-multilingual-gemma2`) pour qu'aucun modèle `sentence-transformers` ne soit
    téléchargé depuis Hugging Face si une fonction en a besoin.
  - Fonctions désactivées : `ENABLE_OLLAMA_API=false`, `ENABLE_WEB_SEARCH=false`,
    `ENABLE_IMAGE_GENERATION=false`, `ENABLE_CODE_EXECUTION=false`,
    `ENABLE_CODE_INTERPRETER=false`, `ENABLE_COMMUNITY_SHARING=false`.
  - Un seul fournisseur : `OPENAI_API_BASE_URL=https://api.scaleway.ai/<projet>/v1`, liste
    blanche de modèles dans la configuration de connexion (`model_ids`).
- **Vérification** : la commande de contrôle (FR-013) inspecte les connexions sortantes du
  conteneur (`ss`/journal Caddy) pendant un scénario et échoue sur toute destination autre que
  `api.scaleway.ai` (et Let's Encrypt pour Caddy, qui ne reçoit aucune donnée de session).
- **Alternatives** : garder le RAG local avec `all-MiniLM-L6-v2` préchargé (inutile pour des
  documents de quelques pages, et mauvais en français).

## R3. Modèles Scaleway (fr-par)

- **Décision** : modèle de référence `mistral-medium-3.5-128b` (vision validée le 2026-11-24) ;
  secours `mistral-small-3.2-24b-instruct-2506` ; modèle de tâches (titres, suggestions)
  `mistral-small-3.2-24b-instruct-2506` via `TASK_MODEL_EXTERNAL` pour limiter le coût. Les
  deux sont présents dans `GET /v1/models` du projet `telemach` le 2026-11-26. Aucun autre
  modèle n'est exposé aux participants.
- **Tarifs** (page officielle Scaleway, à revérifier avant chaque session) : Mistral Medium 3.5
  1,50 EUR / M jetons en entrée, 7,50 EUR / M en sortie. Fenêtre limitée à 180 k jetons pendant
  la préversion : largement suffisant (plan en image + CCTP de quelques pages).
- **Alternatives** : Llama 3.3 70B (pas de vision) ; Qwen et GLM (hors ligne « Mistral, Llama »
  annoncée au programme).

## R4. Images et PDF de plans (FR-003, FR-004)

- **Décision** : le modèle personnalisé « Assistant bureau d'études » déclare la capacité
  `vision` ; Open WebUI transmet alors les PNG/JPEG en `image_url` base64, exactement comme
  `demo.py`. Les PDF sont lus en texte par `pypdf` (dépendance de l'image, `pypdf==6.21.2`) :
  adapté aux CCTP. Un PDF vectoriel de plan (AutoCAD) donne surtout des étiquettes sans
  géométrie : le filtre de session détecte un PDF dont le texte extrait est pauvre et ajoute
  une consigne « exporter le plan en PNG » (cas limite de la spec).
- **Alternatives** : rasteriser les PDF avec PyMuPDF (absent de l'image, ajout d'une
  dépendance, image Docker dérivée) ; OCR `lightonocr-3-0.8b` de Scaleway (étape de plus, gain
  incertain sur des plans). Reportées en v2 si le besoin apparaît chez le client.

## R5. Conversion IFC (FR-005, histoire 2)

- **Décision** : une fonction Open WebUI de type **filtre** (`filtre_ifc.py`, un seul fichier,
  bibliothèque standard uniquement), activée sur le modèle « Assistant bureau d'études ». À
  l'entrée (`inlet`), pour chaque fichier `.ifc` joint : lecture du fichier dans le stockage
  d'Open WebUI, extraction des `IFCSPACE` et de leurs `IFCPROPERTYSINGLEVALUE` (algorithme de
  `demo.py`, rendu robuste : lecture en flux, entités multilignes, types de valeurs variés),
  remplacement du contenu du fichier par un tableau Markdown des espaces, et émission de ce
  tableau comme source consultable dans la discussion (`__event_emitter__`, type `citation`).
  Limite : fichier de plus de 200 Mo ou plus de 2 000 espaces, message explicite (AS 2.3).
- **Raison** : déterministe (pas de dépendance à l'appel d'outils du modèle), aucun service
  supplémentaire, testable hors d'Open WebUI.
- **Alternatives** : outil (« Tool ») appelé par le modèle (aléatoire, demande un modèle fiable
  en appel de fonctions) ; service « Pipelines » séparé (un conteneur de plus) ; `ifcopenshell`
  (dépendance lourde, contraire au principe IV).
- **À vérifier à l'implémentation** : signature exacte de `inlet` en v0.13.5 (`body`,
  `__user__`, `__event_emitter__`, accès aux fichiers par `body["files"]` et
  `open_webui.models.files.Files`), et extension `.ifc` acceptée au dépôt (sinon l'ajouter
  dans les types autorisés).

## R6. Comptes, isolement, bibliothèque de consignes (FR-006 à FR-010)

- **Décision** :
  - `ENABLE_SIGNUP=false`, `DEFAULT_USER_ROLE=pending`, compte formateur administrateur créé au
    premier démarrage par `WEBUI_ADMIN_EMAIL` / `WEBUI_ADMIN_PASSWORD` / `WEBUI_ADMIN_NAME`
    (présents dans `env.py` v0.13.5).
  - Participants créés par `POST /api/v1/auths/add` (rôle `user`), placés dans un groupe
    `participants-<session>`.
  - `ENABLE_ADMIN_CHAT_ACCESS=false` : même le formateur ne lit pas les discussions des
    participants. Les fichiers et discussions sont privés par défaut dans Open WebUI.
  - Consignes : créées par le formateur via `/api/v1/prompts`, accès en lecture accordé au
    groupe ; participants autorisés à créer leurs propres consignes
    (`USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS=true`), partage public interdit.
  - Export : `GET /api/v1/prompts` avec le jeton administrateur, écrit en Markdown et JSON dans
    `exports/<session>/` (ignoré par Git).
- **Alternatives** : SSO (hors périmètre v1) ; comptes génériques partagés (pas d'isolement).

## R7. Hébergement Scaleway et HTTPS (FR-006, FR-011)

- **Décision** :
  - OpenTofu `v1.13.10` (dernière stable, publiée le 2026-11-23, installée sur le poste
    le 2026-11-26) et fournisseur `scaleway/scaleway` `v2.93.0` (2026-11-20), figés dans
    `versions.tf` et `.terraform.lock.hcl`.
  - Instance `DEV1-L` (4 vCPU, 8 Go, 0,0428 EUR/h, disponible en `fr-par-1` le 2026-11-26) ;
    repli `PLAY2-MICRO` (0,0551 EUR/h). Open WebUI sans modèle local tient dans 2 Go ; 8 Go
    laisse une marge pour 10 sessions et la conversion IFC.
  - Image Ubuntu 24.04, Docker installé par cloud-init, `compose.yaml` partagé avec le local ;
    données Open WebUI (SQLite + fichiers) sur le disque de l'instance, détruit avec elle : pas
    de stockage objet, pas de base managée, donc moins de ressources à purger.
  - HTTPS : Caddy `2.11.9` (image `caddy:2.11.9`), certificat Let's Encrypt automatique.
  - Groupe de sécurité : entrée 80/443 seulement ; pas de SSH (toute la configuration passe par
    cloud-init et l'API d'Open WebUI en HTTPS).
  - Clé d'API de session : application IAM dédiée, politique limitée à
    `GenerativeApisModelAccess` sur le projet, clé avec `expires_at` = fin + 48 h ; créée et
    détruite par OpenTofu. La clé personnelle du formateur ne quitte jamais son poste.
  - Toutes les ressources portent l'étiquette `atelier-session=<id>`.
- **Alternatives** : scripts `scw` seuls (reprise d'une purge interrompue à coder à la main,
  alors que `tofu destroy` est idempotent) ; Kubernetes ou conteneurs serverless (disque
  éphémère ou trop de pièces pour 2 jours).

## R8. Nom de domaine (hypothèse de la spec, tranchée le 2026-11-26)

- **Décision** : délégation unique du sous-domaine `atelier.telemach-learning.fr` à Scaleway
  DNS (2 enregistrements NS chez le registrar de `telemach-learning.fr`, faits une fois par
  Alexandre, documentés dans `quickstart.md`). La zone `atelier.telemach-learning.fr` est créée
  une fois (hors session) ; chaque session crée puis détruit son enregistrement A
  `<id>.atelier.telemach-learning.fr` via OpenTofu.
- **Raison** : adresse lisible pour les participants, plus aucune manipulation DNS par session
  (principe III).
- **Alternatives** : nom fourni par Scaleway (`<id>.pub.instances.scw.cloud`, illisible) ;
  enregistrement A manuel à chaque session (contraire au principe III).

## R9. Purge et garde-fou de 48 heures (FR-011, cas limite)

- **Décision** :
  - `atelier session purger` : `tofu destroy` (reprend après interruption), puis inventaire
    `scw --profile telemach` par étiquette (instances, volumes, IP, groupes de sécurité,
    applications et clés IAM, enregistrements DNS) ; échec si une ressource subsiste. Ensuite
    suppression locale de `sessions/<id>/` (participants, identifiants, état OpenTofu qui
    contient la clé de session). Le rapport (ressources supprimées, horodatage, aucun nom de
    personne ni document) est écrit dans `exports/<id>/rapport-purge.md`.
  - Garde-fou : la clé de session expire à fin + 48 h (le modèle devient inaccessible) ; un
    minuteur systemd posé par cloud-init arrête les conteneurs, efface le répertoire de données
    et éteint l'instance à la même échéance ; `atelier session statut` rappelle la purge.
- **Alternatives** : destruction complète déclenchée par l'instance elle-même (il faudrait lui
  confier une clé capable de supprimer des ressources : refusé) ; tâche planifiée Serverless
  Jobs (une pièce de plus pour un cas de secours).

## R10. Coût d'une session (FR-015)

- **Décision** : `atelier session cout` lit le prix horaire de l'instance en direct
  (`scw instance server-type list`) et les tarifs du modèle dans `infra/tarifs.toml` (date de
  vérification obligatoire, refus si plus de 30 jours). Hypothèse par défaut : 10 participants,
  150 demandes chacun sur 2 jours, 8 000 jetons en entrée et 1 000 en sortie par demande ;
  environ 72 h d'instance.
- **Ordre de grandeur** : instance 72 h x 0,0428 = 3,1 EUR ; modèle 12 M jetons entrée x 1,50
  + 1,5 M sortie x 7,50 = 29,3 EUR ; IP et DNS négligeables. Environ 35 EUR par session.

## R11. Charge (SC-003) et quotas

- **Quotas mesurés le 2026-11-26** (en-têtes `x-ratelimit-*` de l'API, projet `telemach`) :
  300 requêtes et 200 000 jetons (entrée + sortie) par minute, pour chaque modèle
  (`mistral-medium-3.5-128b` comme `mistral-small-3.2-24b-instruct-2506`). Le modèle de
  tâches (Small) consomme donc un quota distinct de celui de l'assistant (Medium).
- **Consommation mesurée** (jetons d'entrée, premier tour) : scénario 1 = 2 378 ; scénario 2 =
  3 133 ; scénario 3 = 4 558 ; scénario 4 = 929 ; sortie jusqu'à environ 1 500.
- **Analyse** : 10 participants lançant ensemble le scénario 3 font environ 60 000 jetons dans
  la minute, soit 30 % du quota. Le risque vient des discussions longues (historique et images
  renvoyés à chaque tour, 15 000 à 30 000 jetons par demande) et des CCTP réels de plusieurs
  dizaines de pages déposés en même temps : au-delà de 200 000 jetons par minute, l'API répond
  429 et Open WebUI affiche une erreur.
- **Décision** : quotas suffisants pour le jeu fictif ; demande d'augmentation (x2 à x5, ticket
  au support Scaleway, ou validation d'identité de l'organisation) recommandée avant la
  session réelle, par marge. Consignes d'atelier : une nouvelle discussion par exercice. Le
  contrôle `atelier session controler --charge 10` mesure les temps de réponse (échec au-delà
  de 60 s) et signale les réponses 429.

## R12. Langage et tests

- **Décision** : Python 3.11 ou plus récent (`tomllib`), bibliothèque standard uniquement, pour
  la commande `atelier` et le filtre IFC ; tests `unittest` (`python3 -m unittest`) ; contrôle
  de bout en bout = `atelier local controler` et `atelier session controler` (FR-013).
- **Alternatives** : Bash pour la commande (logique d'API REST et de rapports trop fragile) ;
  `pytest` et `requests` (dépendances inutiles).
