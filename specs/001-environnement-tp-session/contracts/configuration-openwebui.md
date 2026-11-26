# Contrat : configuration d'Open WebUI

Identique en local et en session hébergée (principe III : le poste reproduit la session). Deux
couches : variables d'environnement (fichier versionné `openwebui/env.commun`, sans secret) et
appels à l'API REST, rejoués à chaque démarrage par `atelier` (idempotents).

`ENABLE_PERSISTENT_CONFIG=false` : les variables d'environnement font foi à chaque démarrage,
aucune valeur n'est figée en base par une modification dans l'interface.

## Variables d'environnement

| Variable | Valeur | Raison |
|---|---|---|
| `WEBUI_NAME` | `Atelier IA - Telemach Learning` | |
| `DEFAULT_LOCALE` | `fr-FR` | |
| `ENABLE_PERSISTENT_CONFIG` | `false` | configuration décrite en code |
| `ENABLE_SIGNUP` | `false` | FR-007 |
| `DEFAULT_USER_ROLE` | `pending` | défense en profondeur |
| `WEBUI_ADMIN_EMAIL`, `WEBUI_ADMIN_PASSWORD`, `WEBUI_ADMIN_NAME` | injectés au démarrage (secret) | compte formateur |
| `WEBUI_SECRET_KEY` | injecté (secret, 32 octets aléatoires par session) | |
| `ENABLE_OLLAMA_API` | `false` | FR-002 |
| `ENABLE_OPENAI_API` | `true` | |
| `OPENAI_API_BASE_URL` | `https://api.scaleway.ai/<projet>/v1` | FR-002 |
| `OPENAI_API_KEY` | injecté (local : clé du profil `telemach` ; session : clé IAM de session) | |
| `DEFAULT_MODELS` | `assistant-bureau-etudes` | AS 1.1 |
| `TASK_MODEL_EXTERNAL` | `mistral-small-3.2-24b-instruct-2506` | coût |
| `BYPASS_EMBEDDING_AND_RETRIEVAL` | `true` | documents envoyés en entier, pas de base vectorielle |
| `RAG_EMBEDDING_ENGINE` | `openai` (Scaleway, `bge-multilingual-gemma2`) | aucun modèle téléchargé |
| `OFFLINE_MODE` | `true` | FR-012 |
| `SCARF_NO_ANALYTICS`, `DO_NOT_TRACK` | `true` | FR-012 |
| `ANONYMIZED_TELEMETRY`, `ENABLE_OTEL` | `false` | FR-012 |
| `ENABLE_VERSION_UPDATE_CHECK`, `ENABLE_COMMUNITY_SHARING` | `false` | FR-012 |
| `ENABLE_WEB_SEARCH`, `ENABLE_IMAGE_GENERATION` | `false` | FR-012, périmètre |
| `ENABLE_CODE_EXECUTION`, `ENABLE_CODE_INTERPRETER` | `false` | périmètre |
| `ENABLE_ADMIN_CHAT_ACCESS` | `false` | FR-008 |
| `USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS` | `true` | FR-009 |
| `RAG_FILE_MAX_SIZE` | `200` (Mo) | AS 2.3 |

Chaque nom de variable est revérifié dans `backend/open_webui/env.py` et `config.py` du tag
figé lors de toute montée de version d'Open WebUI.

## Appels d'API (jeton administrateur)

| Ordre | Appel | Contenu |
|---|---|---|
| 1 | `POST /openai/config/update` | une seule connexion Scaleway ; `model_ids` = modèle de référence et modèle de secours |
| 2 | `POST /api/v1/functions/create` ou `/update` | fonction `filtre_ifc` (source `openwebui/fonctions/filtre_ifc.py`), activée |
| 3 | `POST /api/v1/models/create` ou `/update` | modèle `assistant-bureau-etudes` (« Assistant bureau d'études ») : base `mistral-medium-3.5-128b`, invite système de `openwebui/modele-assistant.toml` (reprise de `SYSTEME` de `demo.py`), `temperature` 0,1, capacités `vision` et `file_upload`, filtre `filtre_ifc` attaché, lisible par le groupe des participants |
| 4 | idem | modèle `assistant-secours` sur `mistral-small-3.2-24b-instruct-2506`, mêmes réglages |
| 5 | `POST /api/v1/groups/create` | `participants-<id>`, permissions : consignes oui, partage public non |
| 6 | `POST /api/v1/auths/add` puis ajout au groupe | un appel par participant absent (idempotent par courriel) |
| 7 | `POST /api/v1/prompts/create` | consignes de départ (`openwebui/consignes/*.md`), accès en lecture au groupe |

Chemins exacts et corps des requêtes à confirmer contre `backend/open_webui/routers/*.py` du
tag `v0.13.5` lors de l'implémentation ; un test d'intégration rejoue ces appels contre le
conteneur local.

## Services Docker (`openwebui/compose.yaml`)

| Service | Image | Local | Session |
|---|---|---|---|
| `openwebui` | `ghcr.io/open-webui/open-webui:v0.13.5` | port `127.0.0.1:3000` | réseau interne uniquement |
| `caddy` | `caddy:2.11.9` | absent (profil `session`) | ports 80 et 443, `reverse_proxy openwebui:8080` |

Volume `donnees-openwebui` monté sur `/app/backend/data`.
