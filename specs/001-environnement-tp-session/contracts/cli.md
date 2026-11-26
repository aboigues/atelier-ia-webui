# Contrat : commande `atelier`

Point d'entrée unique, à la racine du dépôt : `./atelier <groupe> <action> [options]`.
Python 3.11 ou plus récent, bibliothèque standard uniquement. Sorties en français, sans emoji.
Toute commande `scw` lancée porte `--profile telemach`.

Codes de sortie communs : `0` succès ; `1` échec d'un contrôle ; `2` erreur d'usage ou de
configuration (fichier manquant, version non figée, tarif périmé) ; `3` ressource externe
indisponible (Docker, Scaleway, DNS).

## Poste local (histoires 1 et 2)

| Commande | Effet | Exigences |
|---|---|---|
| `atelier local demarrer` | Lit la clé Scaleway par `scw --profile telemach config get secret-key` (passée en variable d'environnement au processus `docker compose`, jamais écrite sur disque), lance `openwebui/compose.yaml` sans le service Caddy, attend `/health`, applique la configuration (`contracts/configuration-openwebui.md`), charge le jeu fictif, affiche `http://localhost:3000` et les identifiants formateur locaux. Idempotent. | FR-001, FR-002, FR-014, AS 1.1 (< 5 min) |
| `atelier local arreter [--effacer]` | Arrête les conteneurs. `--effacer` supprime aussi le volume de données (comptes, discussions, fichiers déposés). | FR-001 |
| `atelier local controler` | Contrôle de bout en bout (voir plus bas) sur `http://localhost:3000`. | FR-013 |

Identifiants formateur locaux : générés au premier démarrage dans `sessions/local/identifiants.txt`
(ignoré par Git).

## Session hébergée (histoires 3 et 4)

Toutes les actions prennent `--session <id>` et lisent `sessions/<id>/session.toml` et
`sessions/<id>/participants.csv` (`contracts/fichiers-session.md`).

| Commande | Effet | Exigences |
|---|---|---|
| `atelier session cout` | Affiche le coût estimé détaillé (instance, IP, modèle) et les hypothèses ; refuse si `infra/tarifs.toml` a plus de 30 jours. | FR-015 |
| `atelier session creer` | Affiche le coût et demande confirmation (`--oui` pour l'éviter) ; `tofu apply` ; attend le certificat HTTPS ; applique la configuration ; crée le groupe et les comptes ; charge les consignes de départ ; écrit `sessions/<id>/identifiants/<prenom-nom>.txt` (une fiche par participant) et `formateur.txt` ; lance `controler`. Durée cible < 30 min (SC-006). Relançable : ne recrée pas un compte existant. | FR-006, FR-007, FR-009, AS 3.1 |
| `atelier session controler [--charge N]` | Contrôle de bout en bout sur `https://<id>.atelier.telemach-learning.fr` ; `--charge N` lance N scénarios 1 en parallèle avec N comptes et échoue au-delà de 60 s par réponse. | FR-013, SC-003 |
| `atelier session statut` | Adresse, état (voir `data-model.md`), comptes créés, heures restantes avant l'échéance du garde-fou, rappel de purge. | cas limite 48 h |
| `atelier session exporter` | Écrit `exports/<id>/consignes.json` et `consignes.md` (toutes les consignes de la session, auteur réduit à « formateur » ou « participant »). Aucun fichier déposé, aucune discussion. | FR-010, AS 4.1 |
| `atelier session purger [--oui]` | `tofu destroy`, inventaire Scaleway par étiquette, suppression de `sessions/<id>/`, rapport `exports/<id>/rapport-purge.md`. Échoue (code 1) si une ressource subsiste ; relançable jusqu'au succès. | FR-011, AS 4.2, AS 4.3, SC-005 |
| `atelier session verifier-purge` | Inventaire seul, sans rien supprimer ; code 0 si zéro ressource étiquetée. | SC-005 |

## Contrôle de bout en bout (FR-013)

Étapes, chacune affichée `OK` ou `ÉCHEC` avec la durée :

1. `GET /health` répond ; certificat HTTPS valide (session hébergée).
2. Connexion d'un compte participant (`POST /api/v1/auths/signin`).
3. Inscription libre refusée (`POST /api/v1/auths/signup` -> erreur).
4. Appel du modèle de référence par l'API d'Open WebUI (`/api/chat/completions`), réponse non
   vide.
5. Dépôt de `exemples/bloc-operatoire/plan-salle3-indB.png` puis question du scénario 1 ; la
   réponse contient « B », au moins 8 des repères E01 à E10 et les portes P1 à P4.
6. Dépôt de `maquette-bloc.ifc` ; la réponse cite SO2 et SO4.
7. Isolement : un second compte ne voit pas le fichier déposé à l'étape 5.
8. Aucune connexion sortante hors liste autorisée (voir `research.md`, R2).

Les comptes de contrôle (`controle-1@<id>.atelier`, ...) sont supprimés à la fin du contrôle,
avec leurs discussions et fichiers.
