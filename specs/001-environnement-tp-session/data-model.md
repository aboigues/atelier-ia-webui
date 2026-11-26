# Modèle de données : environnement de travaux pratiques pour une session

Le projet ne gère pas de base de données propre : les comptes, discussions, fichiers et
consignes vivent dans Open WebUI (SQLite sur le disque de l'instance ou du volume Docker local).
Ce document décrit les entités manipulées par la commande `atelier` et leur correspondance dans
Open WebUI et chez Scaleway. Formats de fichiers : `contracts/fichiers-session.md`.

## Session

Occurrence de formation. Décrite par `sessions/<id>/session.toml` (ignoré par Git).

| Champ | Type | Règle |
|---|---|---|
| `id` | texte | `[a-z0-9-]{3,30}`, sert de sous-domaine et d'étiquette (`atelier-session=<id>`) |
| `client` | texte | libellé libre, jamais écrit dans un fichier versionné |
| `debut`, `fin` | date ISO | `fin >= debut` ; `fin` au plus 7 jours après `debut` |
| `type_instance` | texte | défaut `DEV1-L`, doit exister en `fr-par-1` |
| `modele_reference` | texte | défaut `mistral-medium-3.5-128b`, doit figurer dans `GET /v1/models` |
| `modele_secours` | texte | défaut `mistral-small-3.2-24b-instruct-2506` |
| `echeance_garde_fou` | date-heure | calculée : `fin` 18:00 Europe/Paris + 48 h |

États et transitions :

```text
preparee --creer--> creee --controler OK--> prete --(formation)--> terminee
terminee --exporter--> exportee --purger--> purgee
(tout état) --purger--> purgee          (purge toujours possible, reprise si interrompue)
creee/prete --échéance garde-fou--> neutralisee (données effacées, instance éteinte) --purger--> purgee
```

L'état est déduit, jamais stocké à la main : présence de l'état OpenTofu, réponse de
`/health`, présence de `exports/<id>/consignes.json`, rapport de purge.

## Compte

| Champ | Type | Règle |
|---|---|---|
| `prenom`, `nom` | texte | issus de `participants.csv` |
| `courriel` | texte | identifiant de connexion, généré : `prenom.nom@<id>.atelier` (normalisé, sans accent ; suffixe numérique si doublon) ; aucune adresse réelle |
| `mot_de_passe` | texte | 4 mots tirés au hasard (`secrets`), au moins 16 caractères ; jamais versionné |
| `role` | `formateur` / `participant` | formateur = `admin` Open WebUI ; participant = `user` membre du groupe `participants-<id>` |

Correspondance : utilisateur Open WebUI. Supprimé avec l'instance (session hébergée) ou avec le
volume Docker (`atelier local arreter --effacer`).

## Document déposé

Fichier joint à une discussion : PNG, JPEG, PDF, TXT, CSV, IFC. Appartient au compte qui l'a
déposé (stockage `uploads/` d'Open WebUI). Jamais copié sur le poste du formateur par la
commande `atelier`. Supprimé avec la session.

Traitement selon le type :

| Type | Envoyé au modèle sous forme de |
|---|---|
| PNG, JPEG | image (`image_url`), capacité `vision` du modèle |
| PDF | texte extrait ; si texte pauvre, avertissement « exporter le plan en PNG » |
| TXT, CSV | texte intégral |
| IFC | tableau des espaces produit par le filtre IFC (voir ci-dessous) |

## Tableau des espaces IFC (valeur dérivée)

Produit par `filtre_ifc.py` à partir d'un fichier IFC (schémas IFC2X3 et IFC4).

| Colonne | Source IFC |
|---|---|
| `code` | `IFCSPACE` attribut `Name` |
| `nom` | `IFCSPACE` attribut `LongName` (décodage `\X2\...\X0\`) |
| une colonne par propriété | `IFCPROPERTYSINGLEVALUE` reliées par `IFCRELDEFINESBYPROPERTIES` ; booléens `.T.`/`.F.` -> oui/non |

Règles : espaces triés par code ; propriétés absentes laissées vides ; au-delà de 2 000 espaces
ou 200 Mo, refus avec message explicite.

## Consigne

Prompt Open WebUI.

| Champ | Type | Règle |
|---|---|---|
| `commande` | texte | `/[a-z0-9-]+`, unique |
| `titre` | texte | |
| `contenu` | texte | Markdown ; ne contient aucun extrait de document client (consigne de rédaction donnée aux participants) |
| `auteur` | compte | formateur (consignes de départ, partagées en lecture au groupe) ou participant (privées, partageables au groupe) |

Consignes de départ versionnées dans `openwebui/consignes/*.md` (jeu fictif uniquement). Seule
donnée exportée en fin de session (`exports/<id>/consignes.json` et `.md`).

## Jeu fictif

Fichiers de `exemples/bloc-operatoire/` (versionnés), leur corrigé `CORRIGE.md` et les réponses
de référence `resultats-reference/scenario-<n>.md`. Chargé dans l'environnement par
`atelier ... charger-exemples` sous forme de consignes « scénario 1 » à « scénario 5 » ; les
documents eux-mêmes sont déposés par le formateur depuis son poste.

## Ressources Scaleway d'une session

Toutes étiquetées `atelier-session=<id>`, créées et détruites par OpenTofu.

| Ressource | Détail |
|---|---|
| `scaleway_instance_ip` | IPv4 publique |
| `scaleway_instance_security_group` | entrée 80, 443 uniquement |
| `scaleway_instance_server` | `DEV1-L`, Ubuntu 24.04, cloud-init, volume racine détruit avec le serveur |
| `scaleway_domain_record` | A `<id>` dans la zone `atelier.telemach-learning.fr` |
| `scaleway_iam_application` | `atelier-<id>` |
| `scaleway_iam_policy` | `GenerativeApisModelAccess` sur le projet |
| `scaleway_iam_api_key` | `expires_at` = échéance garde-fou |

Hors session (créée une fois, jamais purgée) : la zone DNS `atelier.telemach-learning.fr`.
