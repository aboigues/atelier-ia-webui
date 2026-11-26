# Feature Specification: Environnement de travaux pratiques pour une session de formation

**Feature Branch**: `001-environnement-tp-session`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "Environnement web de travaux pratiques pour l'atelier « IA et analyse de plans pour le bureau d'études » (2 jours, jusqu'à 10 participants, décembre 2026) : les participants déposent des plans, des extraits de CCTP, des listes d'équipements et des maquettes IFC dans une interface de discussion reliée à un modèle d'IA ouvert hébergé à Paris ; le formateur prépare l'environnement, le démontre en local, le déploie pour la session et le détruit ensuite, documents compris."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Démonstration locale sur le jeu fictif (Priority: P1)

Le formateur démarre l'environnement sur son poste, se connecte depuis son navigateur, dépose
le plan fictif d'une salle d'opération (image) et demande d'en extraire le cartouche, la
nomenclature des équipements et la liste des portes. Il obtient un tableau exploitable, puis
rejoue les scénarios de cohérence (plan, extrait de CCTP, liste d'équipements) et de
comparaison de deux indices.

**Why this priority**: c'est la brique minimale qui remplace la démo en ligne de commande ; elle
sert à préparer les ateliers, à les montrer au client et à valider le modèle avant toute
dépense d'hébergement.

**Independent Test**: démarrer l'environnement en local, se connecter, rejouer les scénarios 1
à 3 du jeu fictif et comparer les réponses au corrigé (`exemples/bloc-operatoire/CORRIGE.md`).

**Acceptance Scenarios**:

1. **Given** un poste avec Docker et un accès au profil Scaleway `telemach`, **When** le
   formateur lance la commande de démarrage local, **Then** l'interface est accessible dans son
   navigateur en moins de 5 minutes, avec le modèle de référence sélectionné par défaut.
2. **Given** l'interface ouverte, **When** le formateur dépose `plan-salle3-indB.png` et demande
   le cartouche, la nomenclature et les portes, **Then** la réponse est un tableau qui contient
   l'indice B, les repères E01 à E10 présents sur le plan et les portes P1 à P4 avec leurs
   dimensions.
3. **Given** le plan indice B, l'extrait de CCTP et la liste d'équipements déposés ensemble,
   **When** le formateur demande les écarts, **Then** au moins 4 des 5 écarts volontaires du
   corrigé sont signalés.

---

### User Story 2 - Interroger une maquette IFC en langage courant (Priority: P2)

Un participant dépose une maquette IFC et demande « quelles salles n'ont pas de plafond
soufflant ? ». La maquette est d'abord réduite à un tableau des espaces et de leurs propriétés,
que le modèle interroge.

**Why this priority**: c'est le module 3 du programme ; un fichier IFC brut issu d'un logiciel
de BIM est trop volumineux pour être envoyé tel quel au modèle.

**Independent Test**: déposer `maquette-bloc.ifc` et vérifier que la réponse cite SO2 (sans
plafond soufflant) et SO4 (surpression de 10 Pa au lieu de 15 Pa).

**Acceptance Scenarios**:

1. **Given** l'interface ouverte, **When** un participant dépose une maquette IFC, **Then** il
   peut afficher le tableau des espaces et de leurs propriétés tiré de la maquette.
2. **Given** ce tableau, **When** il pose la question en langage courant, **Then** la réponse
   cite les espaces concernés et les valeurs qui diffèrent.
3. **Given** une maquette de plusieurs dizaines de mégaoctets, **When** elle est déposée,
   **Then** la conversion aboutit ou un message clair indique la limite atteinte.

---

### User Story 3 - Session hébergée pour les participants (Priority: P3)

La veille de la session, le formateur crée l'environnement hébergé à Paris avec un compte par
participant et un compte formateur. Les participants s'y connectent depuis leur ordinateur,
sans installation ni abonnement, travaillent chacun dans leur espace et retrouvent la
bibliothèque de consignes partagée par le formateur, qu'ils enrichissent pendant l'atelier.

**Why this priority**: indispensable pour la session, mais repose sur les histoires 1 et 2 déjà
validées en local.

**Independent Test**: créer l'environnement pour 10 comptes, se connecter simultanément avec 10
navigateurs, rejouer le scénario 1 sur chaque compte.

**Acceptance Scenarios**:

1. **Given** la liste des participants (prénom, nom), **When** le formateur lance la création
   de la session, **Then** l'environnement est accessible en HTTPS et une fiche d'identifiants
   est produite pour chaque participant, hors du dépôt.
2. **Given** deux participants connectés, **When** l'un dépose un document, **Then** l'autre ne
   le voit pas.
3. **Given** une consigne enregistrée dans la bibliothèque partagée par le formateur, **When**
   un participant ouvre la bibliothèque, **Then** il peut l'utiliser et en enregistrer une
   variante.
4. **Given** 10 participants qui interrogent le modèle en même temps, **When** chacun lance le
   scénario 1, **Then** chaque réponse arrive en moins de 60 secondes.

---

### User Story 4 - Fin de session et purge vérifiable (Priority: P4)

À la fin de la session, le formateur récupère ce qui doit être remis aux participants (consignes
et fiches de contrôle rédigées), puis lance la destruction. Tout est supprimé : comptes,
conversations, documents déposés, stockage, serveur. Un rapport de suppression est produit.

**Why this priority**: c'est l'engagement écrit au programme (« aucun document n'est conservé
après la session ») ; il conditionne la confiance du client.

**Independent Test**: créer une session, y déposer un document fictif, lancer la purge, puis
vérifier avec la console de commande Scaleway qu'aucune ressource de la session ne subsiste.

**Acceptance Scenarios**:

1. **Given** une session terminée, **When** le formateur lance l'export, **Then** il obtient la
   bibliothèque de consignes de la session dans un fichier, sans aucun document client.
2. **Given** une session terminée, **When** il lance la purge, **Then** toutes les ressources de
   la session sont supprimées et un rapport liste chaque ressource supprimée.
3. **Given** une purge interrompue, **When** il la relance, **Then** elle reprend et termine
   sans erreur.

---

### Edge Cases

- Le réseau du client bloque l'adresse de l'environnement : le formateur peut basculer sur un
  partage de connexion sans reconfiguration.
- Le service de modèles de Scaleway ne répond pas ou le quota est atteint : un message clair
  s'affiche et les résultats de référence du jeu fictif restent consultables.
- Un participant dépose un PDF vectoriel issu d'AutoCAD au lieu d'une image : le document est
  lisible, ou le message indique d'exporter le plan en image.
- Un participant tente de créer lui-même un compte : impossible, seuls les comptes créés par le
  formateur existent.
- Le formateur oublie de purger : un rappel ou une destruction programmée empêche
  l'environnement de survivre plus de 48 heures après la fin prévue.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le formateur MUST pouvoir démarrer et arrêter l'environnement sur son poste avec
  une commande chacune.
- **FR-002**: Le système MUST relier l'interface aux modèles ouverts de Scaleway (région Paris)
  et proposer le modèle de référence par défaut ; aucun autre fournisseur de modèles n'est
  configuré.
- **FR-003**: Les utilisateurs MUST pouvoir déposer des images (PNG, JPEG), des PDF, des fichiers
  texte et CSV, et des maquettes IFC dans une discussion.
- **FR-004**: Le système MUST transmettre les images de plans au modèle en tant qu'images, pour
  qu'il en lise le contenu visuel.
- **FR-005**: Le système MUST convertir une maquette IFC en tableau des espaces et de leurs
  propriétés avant de l'envoyer au modèle.
- **FR-006**: Le formateur MUST pouvoir créer une session hébergée à Paris, accessible en HTTPS,
  avec un compte par participant et un compte formateur, à partir d'une liste de participants.
- **FR-007**: L'inscription libre MUST être désactivée ; seuls les comptes créés par le
  formateur peuvent se connecter.
- **FR-008**: Chaque participant MUST ne voir que ses propres discussions et documents.
- **FR-009**: Le formateur MUST pouvoir partager une bibliothèque de consignes avec tous les
  participants, et les participants MUST pouvoir enregistrer leurs propres consignes.
- **FR-010**: Le formateur MUST pouvoir exporter la bibliothèque de consignes de la session.
- **FR-011**: Le formateur MUST pouvoir détruire la session et toutes ses données avec une
  commande, qui produit un rapport de suppression.
- **FR-012**: Le système MUST n'envoyer aucune donnée à un service tiers autre que Scaleway
  (télémétrie, polices, scripts ou images distants désactivés).
- **FR-013**: Une commande de contrôle MUST vérifier, avant la session, la connexion d'un
  compte, l'appel au modèle, le dépôt d'une image de plan et la conversion IFC.
- **FR-014**: Le jeu de documents fictifs MUST être chargeable dans l'environnement pour la
  démonstration et le corrigé des ateliers.
- **FR-015**: Le coût estimé d'une session (serveur et consommation du modèle) MUST être affiché
  avant sa création.

### Key Entities

- **Session** : une occurrence de formation (client, dates, environnement hébergé) ; créée la
  veille, détruite à la fin.
- **Compte** : participant ou formateur ; identifiants remis hors du dépôt, supprimés avec la
  session.
- **Document déposé** : plan, CCTP, liste, maquette ; appartient à un compte ; supprimé avec la
  session.
- **Consigne** : texte réutilisable (fiche de contrôle) ; partagée par le formateur ou rédigée
  par un participant ; seule donnée exportée en fin de session.
- **Jeu fictif** : documents de démonstration versionnés et leur corrigé.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Le formateur démarre l'environnement local et rejoue les 5 scénarios du jeu fictif
  en moins de 15 minutes, sans ligne de commande en dehors du démarrage.
- **SC-002**: Sur le jeu fictif, les réponses trouvent au moins 4 des 5 écarts du scénario de
  cohérence et les 2 modifications non déclarées du scénario des indices.
- **SC-003**: 10 participants travaillent simultanément avec un temps de réponse inférieur à
  60 secondes par demande.
- **SC-004**: Un participant se connecte et lance sa première demande en moins de 3 minutes
  après avoir reçu ses identifiants.
- **SC-005**: Après la purge, zéro ressource de la session subsiste chez Scaleway et zéro
  document client subsiste sur le poste du formateur ou dans le dépôt.
- **SC-006**: La création d'une session hébergée prend moins de 30 minutes, contrôle compris.

## Assumptions

- Le modèle de référence est `mistral-medium-3.5-128b` (Scaleway Generative APIs), validé sur
  les images de plans le 2026-11-24 ; un modèle plus léger peut servir de secours.
- L'environnement hébergé tourne sur une instance Scaleway à Paris ; l'adresse est un
  sous-domaine de `telemach-learning.fr` (DNS géré par Alexandre), avec un certificat
  automatique. À confirmer pendant `/speckit-plan`.
- Les identifiants sont générés par le formateur et remis sur papier ou par la messagerie du
  client ; pas d'authentification unique (SSO) en v1.
- Les participants disposent d'un ordinateur portable avec un navigateur récent et d'un accès à
  internet (prévu au programme).
- Le coût est à la charge de Telemach Learning ; il n'est pas refacturé.
- Hors périmètre v1 : déploiement chez le client (relève de l'accompagnement), outils ADV ou
  CRM, mesure de cotes sur plans.
- Dates cibles : environnement local opérationnel au plus tard le 2026-12-03 ; session hébergée
  testée au plus tard la veille de la formation (2026-12-09 ou 2026-12-20).
