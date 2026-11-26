# Constitution du projet atelier-ia-webui

Environnement de travaux pratiques des formations IA de Telemach Learning : une interface web
(Open WebUI) reliée à des modèles d'IA ouverts hébergés en France, que le formateur crée pour une
session et détruit après. Premier usage : l'atelier « IA et analyse de plans pour le bureau
d'études » d'un intégrateur de blocs opératoires (décembre 2026). Il sert aussi de préfiguration
à l'accompagnement qui suit la formation (déploiement d'une solution chez le client).

## Core Principles

### I. Confidentialité des documents clients (NON NÉGOCIABLE)

- Aucun document client (plan, CCTP, maquette IFC, liste d'équipements, liste de participants,
  résultat d'atelier) n'est jamais versionné dans ce dépôt, même anonymisé. Seuls les jeux de
  documents **fictifs** sont versionnés, dans `exemples/`.
- Les documents clients d'une session vivent hors du dépôt (dossier local ignoré par Git ou
  stockage Scaleway dédié à la session) et sont supprimés à la fin de la session.
- La fin de session détruit tout : comptes, conversations, fichiers déposés, volumes, instance.
  La purge est une commande unique dont le résultat est vérifiable (rapport de suppression).
- Aucune télémétrie, aucun service tiers hors hébergement Scaleway Paris ne reçoit de données.

Raison : c'est la promesse faite au client (« aucun document n'est conservé après la session »)
et le cœur du discours sur les plans d'établissements de santé.

### II. Modèles ouverts, hébergés en France

- Les modèles utilisés sont des modèles ouverts (Mistral, Llama ou équivalent), appelés via
  Scaleway Generative APIs (région `fr-par`) ou servis sur une instance Scaleway dédiée.
- Interdit : Copilot, OpenAI, et tout fournisseur d'IA hébergé hors de l'Union européenne.
- Aucun document ni message ne qualifie l'hébergement de « SecNumCloud ».
- Toute commande `scw` porte `--profile telemach` (le profil par défaut pointe sur un autre
  projet).

### III. Reproductible et éphémère

- Tout l'environnement est décrit en code : Docker Compose pour le poste local, OpenTofu (ou
  scripts `scw` versionnés) pour Scaleway. Aucune configuration manuelle dans une console.
- Une commande crée l'environnement d'une session, une commande le détruit ; le poste local
  (Docker) reproduit l'environnement de session avant tout déploiement.
- Le coût d'une session est connu avant sa création et borné (taille d'instance, durée).

### IV. Au service de l'atelier, au plus simple

- Chaque fonctionnalité se rattache à un module du programme de formation ou à
  l'accompagnement qui suit ; sinon, elle n'est pas développée.
- Les participants n'ont besoin que d'un navigateur : ni installation, ni abonnement, ni compte
  personnel chez un fournisseur d'IA.
- Préférer la configuration d'Open WebUI à du code ; préférer la bibliothèque standard Python
  aux dépendances (le convertisseur IFC de la démo n'en utilise aucune).

### V. Versions vérifiées, secrets hors du dépôt

- Toute version (image Docker, outil, fournisseur OpenTofu, dépendance) est la dernière version
  stable vérifiée au moment de l'ajout (registre, page de releases), jamais tirée de mémoire,
  et figée (tag explicite, jamais `latest`).
- Aucun secret (clé Scaleway, mot de passe administrateur, comptes participants) n'est
  versionné : fichiers `.env` ignorés par Git, clé lue à l'exécution depuis le profil
  `scw --profile telemach`.

### VI. Langue et style

- Documentation, interface personnalisée, messages de commit et commentaires en français, avec
  accents et diacritiques complets.
- Zéro emoji, partout : code, documentation, interface, commits, journaux.

### VII. Sécurité de très haut niveau, contrôlée par des gates GitHub (NON NÉGOCIABLE)

- La sécurité est tenue à très haut niveau sur tout le projet : code, infrastructure,
  chaîne d'approvisionnement et configuration d'Open WebUI. En cas d'arbitrage entre sécurité
  et simplicité (principe IV), la sécurité l'emporte.
- La branche `main` est protégée : passage par une PR obligatoire, contrôles requis au vert,
  historique linéaire, aucun push direct ni force-push, y compris pour l'administrateur.
- Chaque PR vers `main` passe des contrôles automatiques bloquants (GitHub Actions), au
  minimum :
  - linters : Python, shell, OpenTofu (`tofu fmt -check`, `tofu validate`), YAML, workflows
    GitHub Actions ;
  - SAST : analyse statique de sécurité du code ;
  - SCA : vulnérabilités connues des dépendances et des images Docker figées ;
  - analyse de sécurité de l'infrastructure en code (OpenTofu, cloud-init, Compose) ;
  - détection de secrets dans le code et dans tout l'historique ;
  - tests unitaires.
- Une vulnérabilité critique ou élevée bloque le merge, sauf exception acceptée par Alexandre
  et documentée dans le dépôt (vulnérabilité, raison, date de réexamen).
- Chaîne d'approvisionnement : chaque action GitHub est épinglée par son empreinte SHA complète
  (version lisible en commentaire) ; les jetons de workflow ont les permissions minimales
  (`contents: read` par défaut, élévation par tâche et justifiée) ; aucun secret n'apparaît
  dans les journaux.
- Dependabot (alertes et mises à jour de sécurité et de versions pour les actions GitHub, les
  images Docker et le fournisseur OpenTofu) sera activé ultérieurement ; d'ici là, la
  vérification des versions reste manuelle selon le principe V.
- Des contrôles tous au vert ne valent pas merge : le merge reste réservé à Alexandre.

Raison : le dépôt est public et l'environnement reçoit des plans d'établissements de santé ;
une faille dans le code, une action compromise ou un secret divulgué ruinerait la promesse
faite au client (principe I).

## Contraintes techniques

- Interface : Open WebUI (version figée, vérifiée à l'ajout ; v0.13.5 au 2026-11-26).
- Modèles : Scaleway Generative APIs, API compatible OpenAI ; modèle de référence de la démo :
  `mistral-medium-3.5-128b` (lecture d'images de plans validée le 2026-11-24).
- Plans : déposés en image (PNG) ou en PDF ; maquettes IFC converties en tableau de propriétés
  avant envoi au modèle (un IFC réel est trop volumineux pour être envoyé brut).
- Capacité cible : 10 comptes participants simultanés et un compte formateur, sur deux jours.
- Accès : HTTPS obligatoire dès que l'environnement est exposé hors du poste local.

## Flux de travail

- Cycle Spec-Kit pour chaque fonctionnalité : `/speckit-specify`, `/speckit-clarify` si
  ambiguïté, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`.
- Une branche par fonctionnalité ; commit, push et création de PR autorisés pour Claude ;
  **le merge est réservé à Alexandre**. Nouvelle branche après chaque merge.
- Gates avant merge (principe VII) : une PR n'est proposée au merge que lorsque tous les
  contrôles requis sont au vert ; un contrôle en échec se corrige dans la PR, il ne se
  désactive pas et ne se contourne pas. Toute modification des workflows, des règles de
  protection ou des seuils de sécurité passe par une PR dédiée, validée par Alexandre.
- Contrôle avant session (veille et jour J) : un test de bout en bout automatisé vérifie la
  connexion d'un compte, l'appel au modèle, le dépôt d'une image de plan et la conversion IFC.
- Contrôle après session : la purge est lancée et son rapport conservé (sans donnée client).

## Governance

- Cette constitution prime sur toute autre pratique du dépôt ; chaque spécification, plan et
  revue de PR vérifie sa conformité, en particulier aux principes I, II et VII.
- Modification : par PR dédiée, validée par Alexandre, avec incrément de version (MAJEUR :
  principe retiré ou redéfini ; MINEUR : principe ou section ajouté ; CORRECTIF : rédaction).
- Les consignes d'exécution courantes pour les agents sont dans `CLAUDE.md`.

**Version**: 1.1.0 | **Ratified**: 2026-11-26 | **Last Amended**: 2026-11-26
