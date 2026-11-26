# Contrat : fichiers de session

Tous sous `sessions/<id>/` ou `exports/<id>/`, ignorés par Git (`.gitignore`, principe I). Seuls
les modèles fictifs de `exemples/session/` sont versionnés.

## `sessions/<id>/session.toml` (écrit par le formateur)

```toml
id = "valmont-2026-12"                           # exemple fictif
client = "CH de Valmont (fictif)"
debut = 2026-12-10
fin = 2026-12-11
type_instance = "DEV1-L"                         # facultatif
modele_reference = "mistral-medium-3.5-128b"     # facultatif
modele_secours = "mistral-small-3.2-24b-instruct-2506"  # facultatif
```

## `sessions/<id>/participants.csv` (écrit par le formateur)

UTF-8, séparateur `;` ou `,` détecté, en-tête obligatoire `prenom;nom`. 1 à 15 lignes. Aucune
autre colonne lue (pas de courriel réel, pas de fonction).

## `sessions/<id>/identifiants/` (produit par `atelier session creer`)

Une fiche texte par compte, prête à imprimer :

```text
Atelier IA et analyse de plans - <client>
Adresse : https://<id>.atelier.telemach-learning.fr
Identifiant : <courriel généré>
Mot de passe : <mot de passe>
Les documents déposés sont supprimés à la fin de la session.
```

## `sessions/<id>/tofu/` (produit par `atelier`)

État OpenTofu local de la session (contient la clé IAM de session). Supprimé par la purge.

## `infra/tarifs.toml` (versionné)

```toml
verifie_le = 2026-11-26
source = "https://www.scaleway.com/fr/tarifs/model-as-a-service/"
[modeles."mistral-medium-3.5-128b"]
entree_eur_par_million = 1.50
sortie_eur_par_million = 7.50
[hypotheses]
demandes_par_participant = 150
jetons_entree_par_demande = 8000
jetons_sortie_par_demande = 1000
```

## `exports/<id>/consignes.json` et `consignes.md` (produits par `atelier session exporter`)

Liste de `{commande, titre, contenu, auteur: "formateur" | "participant"}` ; aucun nom de
personne, aucun fichier déposé, aucune discussion.

## `exports/<id>/rapport-purge.md` (produit par `atelier session purger`)

```text
Rapport de purge - session <id>
Début : <horodatage>   Fin : <horodatage>
Ressources Scaleway supprimées : <type> <identifiant> (une ligne chacune)
Inventaire après purge (étiquette atelier-session=<id>) : 0 ressource
Données locales supprimées : sessions/<id>/ (participants, identifiants, état OpenTofu)
Résultat : purge complète | purge incomplète (liste des restes)
```

Aucun nom de participant, aucun nom de document déposé.
