# Feature Specification: Chaîne de contrôle de sécurité du dépôt

**Feature Branch**: `002-chaine-controle-securite`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "Mettre en place le principe VII de la constitution (v1.1.0) : la sécurité doit rester à très haut niveau ; gates GitHub obligatoires sur chaque PR vers main (linters, SAST, SCA, analyse de l'infrastructure en code, détection de secrets, tests), protection de main, actions épinglées, permissions minimales ; Dependabot activé plus tard. À livrer avant que la fonctionnalité 001 n'ajoute du code."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Contrôles bloquants sur chaque PR (Priority: P1)

Alexandre, ou Claude pour lui, ouvre une PR vers `main`. Les contrôles automatiques se lancent
seuls : qualité du code, sécurité du code, vulnérabilités des composants tiers, sécurité de
l'infrastructure décrite en code, secrets, tests. Le résultat de chaque contrôle s'affiche dans
la PR ; si un seul échoue, le merge est impossible tant que la cause n'est pas corrigée.

**Why this priority**: c'est le cœur du principe VII ; sans contrôle bloquant, les autres
mesures restent déclaratives.

**Independent Test**: ouvrir une PR de démonstration qui introduit volontairement une faute de
style, un appel dangereux, un composant vulnérable, une ressource d'infrastructure ouverte à
tous et un test en échec : chaque contrôle concerné passe au rouge et le bouton de merge est
bloqué ; corriger, et tout passe au vert.

**Acceptance Scenarios**:

1. **Given** une PR vers `main`, **When** elle est ouverte ou mise à jour, **Then** tous les
   contrôles requis s'exécutent sans action manuelle et leur résultat apparaît dans la PR.
2. **Given** une PR dont un contrôle échoue, **When** Alexandre tente de la merger, **Then** le
   merge est refusé par la plateforme.
3. **Given** une PR qui ne modifie que de la documentation, **When** les contrôles
   s'exécutent, **Then** ils aboutissent tous (aucun contrôle requis ne reste « en attente »
   faute d'avoir été lancé).
4. **Given** un contrôle en échec, **When** Alexandre lit le résultat, **Then** il voit quel
   fichier, quelle ligne et quelle règle sont en cause, en moins de 2 minutes.

---

### User Story 2 - Branche principale protégée (Priority: P1)

Personne, administrateur compris, ne peut modifier `main` autrement que par une PR dont les
contrôles sont au vert ; l'historique reste linéaire et ne peut pas être réécrit.

**Why this priority**: sans protection, un push direct contourne tous les contrôles.

**Independent Test**: tenter un push direct sur `main`, un force-push et le merge d'une PR aux
contrôles rouges : les trois sont refusés.

**Acceptance Scenarios**:

1. **Given** la protection active, **When** quelqu'un pousse directement sur `main`, **Then**
   la plateforme refuse.
2. **Given** la protection active, **When** quelqu'un tente un force-push ou une suppression de
   `main`, **Then** la plateforme refuse.
3. **Given** une PR aux contrôles verts, **When** Alexandre la merge, **Then** seul un merge
   qui garde l'historique linéaire est proposé.
4. **Given** la configuration de protection, **When** on la compare à sa description versionnée
   dans le dépôt, **Then** elles concordent (la protection est reproductible, pas réglée à la
   main sans trace).

---

### User Story 3 - Aucun secret dans le dépôt (Priority: P2)

Un secret (clé d'API, mot de passe, jeton) ne doit jamais atteindre le dépôt public : il est
bloqué dès l'envoi quand c'est possible, et sinon détecté par le contrôle de la PR, sur
l'ensemble de l'historique.

**Why this priority**: le dépôt est public ; un secret divulgué est compromis immédiatement,
même s'il est retiré ensuite.

**Independent Test**: tenter d'envoyer une branche contenant une fausse clé au format reconnu :
l'envoi est refusé ou la PR est bloquée ; une analyse complète de l'historique actuel ne
trouve aucun secret.

**Acceptance Scenarios**:

1. **Given** un commit contenant une clé au format d'un fournisseur connu, **When** il est
   envoyé, **Then** l'envoi est refusé par la plateforme ou la PR est bloquée par le contrôle
   de secrets.
2. **Given** l'historique complet du dépôt, **When** le contrôle de secrets s'exécute, **Then**
   il analyse tous les commits, pas seulement les fichiers modifiés.
3. **Given** un faux positif avéré (valeur fictive du jeu d'exemples), **When** Alexandre
   l'accepte, **Then** l'exception est documentée dans le dépôt avec sa raison.

---

### User Story 4 - Vulnérabilités suivies et exceptions documentées (Priority: P2)

Les composants tiers (images Docker figées, actions, fournisseur d'infrastructure, dépendances
éventuelles) sont analysés à chaque PR et chaque semaine sur `main`, car une vulnérabilité peut
être publiée sans que le dépôt change. Une vulnérabilité grave bloque ; une exception n'est
possible que si Alexandre l'accepte, avec une raison et une date de réexamen, après laquelle
elle bloque de nouveau.

**Why this priority**: Open WebUI et Caddy sont des composants tiers exposés sur internet ; ce
sont eux, plus que le code du dépôt, qui portent le risque.

**Independent Test**: référencer une version connue pour être vulnérable : le contrôle bloque ;
ajouter une exception datée : il passe ; dépasser la date de réexamen : il bloque de nouveau.

**Acceptance Scenarios**:

1. **Given** un composant tiers avec une vulnérabilité grave, **When** le contrôle s'exécute,
   **Then** il bloque si un correctif est publié, ou si elle est critique (voir FR-007).
2. **Given** une exception documentée et non échue, **When** le contrôle s'exécute, **Then**
   la vulnérabilité est signalée mais ne bloque pas.
3. **Given** une exception dont la date de réexamen est passée, **When** le contrôle
   s'exécute, **Then** il bloque de nouveau.
4. **Given** une nouvelle vulnérabilité publiée sur un composant de `main` inchangé, **When**
   l'analyse hebdomadaire s'exécute, **Then** Alexandre en est informé par la plateforme.

---

### User Story 5 - Mêmes contrôles sur le poste avant l'envoi (Priority: P3)

Avant de pousser, Alexandre ou Claude lance en une commande les mêmes contrôles que la PR, sur
le poste, pour corriger avant d'envoyer.

**Why this priority**: confort et rapidité ; la PR reste le seul contrôle qui fait foi.

**Independent Test**: lancer la commande locale sur une branche qui contient une faute de style
et un test en échec : elle signale les deux, comme la PR le ferait.

**Acceptance Scenarios**:

1. **Given** le poste du formateur (Docker disponible), **When** il lance la commande de
   contrôle local, **Then** il obtient le même verdict que la PR pour les linters, les tests et
   les secrets.
2. **Given** un contrôle local en échec, **When** il pousse quand même, **Then** la PR le
   bloque (le contrôle local ne remplace jamais celui de la PR).

---

### Edge Cases

- PR ouverte depuis une copie du dépôt (fork) par un tiers, le dépôt étant public : les
  contrôles s'exécutent sans accès à aucun secret ni droit d'écriture.
- PR qui modifie les contrôles eux-mêmes : elle est contrôlée par la version proposée et doit
  passer ; la suppression d'un contrôle requis est visible dans la PR et soumise à Alexandre.
- Service d'analyse indisponible ou réseau en panne : le contrôle échoue (on ne considère
  jamais une absence de résultat comme un succès) ; il peut être relancé.
- Vulnérabilité grave dans l'image officielle d'Open WebUI ou de Caddy sans correctif publié :
  élevée, elle est listée sans bloquer ; critique, elle bloque jusqu'à une exception
  individuelle ou une nouvelle version de l'image (FR-007).
- Une vulnérabilité élevée listée sans correctif reçoit un correctif : elle bloque dès
  l'analyse suivante, à la PR ou à l'analyse hebdomadaire.
- Dépôt encore sans code applicatif (fonctionnalité 001 non commencée) : les contrôles
  passent et seront actifs dès le premier fichier ajouté.
- Contrôle qui dépasse sa durée maximale : il échoue au lieu de rester en attente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Chaque PR vers `main` MUST déclencher automatiquement l'ensemble des contrôles
  requis, à l'ouverture et à chaque mise à jour.
- **FR-002**: Les contrôles requis MUST couvrir au minimum : linters (code Python, scripts
  shell, infrastructure en code avec vérification du format et de la validité, YAML,
  définitions des contrôles eux-mêmes), analyse statique de sécurité du code, analyse des
  vulnérabilités connues des composants tiers (images Docker figées, fournisseur
  d'infrastructure, actions, dépendances), analyse de sécurité de l'infrastructure en code
  (OpenTofu, cloud-init, Compose), détection de secrets sur tout l'historique, tests unitaires.
- **FR-003**: Un contrôle requis en échec, en attente ou non exécuté MUST empêcher le merge.
- **FR-004**: La branche `main` MUST refuser les push directs, les force-push et la
  suppression, y compris pour l'administrateur, et n'accepter que des merges qui gardent
  l'historique linéaire.
- **FR-005**: La configuration de protection de `main` MUST être décrite dans le dépôt et
  pouvoir être réappliquée et vérifiée par une commande.
- **FR-006**: Les secrets MUST être bloqués à l'envoi par la plateforme lorsqu'elle le permet,
  et détectés par le contrôle de la PR dans tous les cas.
- **FR-007**: Toute vulnérabilité critique ou élevée pour laquelle un correctif est publié
  MUST bloquer le merge. Une vulnérabilité critique sans correctif MUST bloquer sauf
  exception individuelle (FR-008). Les vulnérabilités élevées sans correctif MUST être
  listées dans un rapport joint à la PR et à l'analyse hebdomadaire, sans bloquer ; cette
  tolérance est elle-même une exception de classe inscrite dans le fichier d'exceptions
  (FR-008), avec sa date de réexamen, pour rester conforme au principe VII.
- **FR-008**: Une exception (vulnérabilité ou faux positif de secret) MUST être enregistrée
  dans un fichier versionné du dépôt avec l'identifiant, la raison, la personne qui l'accepte
  et une date de réexamen d'au plus 90 jours ; échue, elle MUST cesser de s'appliquer.
- **FR-009**: L'analyse des vulnérabilités MUST aussi s'exécuter chaque semaine sur `main`, et
  ses alertes MUST être visibles par Alexandre sur la plateforme.
- **FR-010**: Chaque action tierce utilisée par les contrôles MUST être épinglée par son
  empreinte complète, avec la version lisible en commentaire ; un contrôle MUST échouer si une
  action n'est pas épinglée.
- **FR-011**: Les contrôles MUST s'exécuter avec des droits en lecture seule par défaut ; tout
  droit supplémentaire MUST être limité à la tâche qui en a besoin et justifié en commentaire.
- **FR-012**: Les contrôles MUST n'exposer aucun secret dans leurs journaux et ne disposer
  d'aucun secret lorsqu'ils s'exécutent pour une PR issue d'une copie du dépôt.
- **FR-013**: Chaque contrôle en échec MUST indiquer le fichier, la ligne (si applicable) et la
  règle en cause dans la PR.
- **FR-014**: Une commande locale MUST exécuter les linters, les tests et la détection de
  secrets avec les mêmes règles et versions que la PR.
- **FR-015**: Les outils de contrôle MUST être figés à une version vérifiée au moment de
  l'ajout (constitution, principe V).
- **FR-016**: Les contrôles MUST s'achever en moins de 15 minutes, échec compris ; au-delà ils
  échouent.

### Key Entities

- **Contrôle requis** : vérification automatique nommée, exécutée sur chaque PR, dont le
  résultat (succès ou échec) conditionne le merge.
- **Règle de protection** : description versionnée des contraintes appliquées à `main`.
- **Exception de sécurité** : vulnérabilité ou faux positif accepté par Alexandre ; porte un
  identifiant, une raison, une date d'acceptation et une date de réexamen.
- **Alerte** : vulnérabilité ou secret signalé par la plateforme hors PR (analyse
  hebdomadaire, blocage à l'envoi).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % des PR mergées dans `main` après la mise en service ont tous leurs contrôles
  requis au vert.
- **SC-002**: Sur une PR de démonstration contenant 6 défauts volontaires (un par famille de
  contrôle), les 6 sont détectés et le merge est bloqué.
- **SC-003**: 3 tentatives de contournement (push direct, force-push, merge d'une PR rouge)
  sont refusées sur 3.
- **SC-004**: Une analyse complète de l'historique du dépôt trouve 0 secret.
- **SC-005**: L'ensemble des contrôles d'une PR s'achève en moins de 10 minutes dans 90 % des
  cas.
- **SC-006**: Le diagnostic d'un contrôle en échec (quel fichier, quelle règle) prend moins de
  2 minutes à Alexandre.
- **SC-007**: 0 action tierce non épinglée et 0 contrôle disposant de droits d'écriture non
  justifiés.

## Clarifications

### Session 2026-11-26

- Q: Quel seuil appliquer aux vulnérabilités sans correctif publié dans les images tierces ? -> A: bloquer toute critique ou élevée qui a un correctif ; critique sans correctif bloquante sauf exception individuelle ; élevée sans correctif listée sans bloquer, au titre d'une exception de classe documentée et réexaminée.

## Assumptions

- Le dépôt est public sur GitHub (`aboigues/atelier-ia-webui`) : analyse de sécurité du code,
  détection de secrets avec blocage à l'envoi et règles de protection de branche sont
  disponibles sans abonnement payant.
- Alexandre est le seul mainteneur : aucune approbation de revue n'est exigée (il ne peut pas
  approuver sa propre PR) ; le merge reste son geste, contrôles au vert.
- Dependabot (alertes et mises à jour automatiques) est hors périmètre ; il sera activé par une
  fonctionnalité ultérieure. D'ici là, les versions sont vérifiées à la main (principe V).
- Le contrôle local s'appuie sur Docker, déjà présent sur le poste ; les analyses qui ne
  tournent que sur la plateforme (analyse statique de sécurité du code, blocage à l'envoi) ne
  sont pas reproduites en local.
- Les commits signés ne sont pas exigés en v1.
- Livraison avant le début de l'implémentation de la fonctionnalité 001.
