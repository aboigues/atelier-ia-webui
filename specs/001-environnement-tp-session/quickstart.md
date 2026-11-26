# Guide de validation : environnement de travaux pratiques

Scénarios exécutables qui prouvent que la fonctionnalité marche de bout en bout. Les commandes
sont décrites dans `contracts/cli.md` ; les formats de fichiers dans
`contracts/fichiers-session.md`.

## Prérequis

- Docker et Docker Compose (WSL2), Python 3.11 ou plus récent, `scw` configuré avec le profil
  `telemach` (`scw --profile telemach config get secret-key` répond).
- OpenTofu `v1.13.10` (session hébergée).
- Une fois pour toutes, avant la première session hébergée :
  1. déclarer `telemach-learning.fr` comme domaine externe chez Scaleway
     (`scw --profile telemach domain external-domain register domain=telemach-learning.fr`),
     ajouter chez l'hébergeur DNS de `telemach-learning.fr` (bunny.net) l'enregistrement TXT `_scaleway-challenge` indiqué, attendre la
     validation ; puis créer la zone `atelier.telemach-learning.fr`
     (`scw --profile telemach dns zone create domain=telemach-learning.fr subdomain=atelier`)
     et lire ses serveurs de noms (`scw --profile telemach dns zone list`) ;
  2. chez bunny.net (hébergeur DNS de `telemach-learning.fr`), ajouter les enregistrements NS de `atelier`
     vers les serveurs de noms indiqués par Scaleway ;
  3. vérifier : `dig NS atelier.telemach-learning.fr +short` renvoie les serveurs Scaleway.
  4. vérifier les quotas Generative APIs du projet (requêtes et jetons par minute) pour
     10 utilisateurs simultanés ; demander une augmentation si besoin.

## Tests unitaires

```bash
python3 -m unittest discover -s tests
```

Attendu : tous verts, dont la conversion de `maquette-bloc.ifc` (SO2 sans plafond soufflant,
SO4 à 10 Pa) et la génération des comptes depuis un `participants.csv` fictif.

## Scénario A : démonstration locale (histoire 1, SC-001, SC-002)

```bash
./atelier local demarrer          # < 5 min, affiche http://localhost:3000
./atelier local controler         # toutes les étapes OK
```

Puis, dans le navigateur, avec le compte formateur local et le modèle « Assistant bureau
d'études » sélectionné par défaut, rejouer les scénarios 1 à 5 avec les consignes chargées et
les fichiers de `exemples/bloc-operatoire/`. Comparer à `CORRIGE.md` :

- scénario 1 : indice B, repères E01 à E10, portes P1 à P4 avec dimensions ;
- scénario 2 : au moins 4 des 5 écarts ;
- scénario 3 : les 2 modifications non déclarées (P3, plafond soufflant) ;
- scénario 4 : SO2 et SO4 ;
- scénario 5 : l'IA ne doit pas être prise pour un outil de mesure.

Durée totale cible : moins de 15 minutes.

## Scénario B : maquette IFC (histoire 2)

Déposer `maquette-bloc.ifc`, demander « quelles salles n'ont pas de plafond soufflant ? ».
Attendu : la source « Tableau des espaces » s'affiche, la réponse cite SO2 (et SO4 si l'on
demande les valeurs qui détonnent). Déposer un fichier `.ifc` tronqué : message « Conversion
IFC impossible », aucun contenu STEP brut envoyé au modèle.

## Scénario C : session hébergée de répétition (histoires 3 et 4)

Avec un `session.toml` et un `participants.csv` fictifs (copiés de `exemples/session/`) :

```bash
./atelier session cout --session repetition
./atelier session creer --session repetition          # < 30 min (SC-006)
./atelier session controler --session repetition --charge 10   # < 60 s par réponse (SC-003)
```

Vérifier à la main : connexion avec une fiche d'identifiants et première demande en moins de
3 minutes (SC-004) ; un participant ne voit pas le fichier d'un autre ; une consigne partagée
est visible et copiable ; l'inscription libre est absente de la page de connexion.

```bash
./atelier session exporter --session repetition       # exports/repetition/consignes.*
./atelier session purger --session repetition
./atelier session verifier-purge --session repetition # code 0
scw --profile telemach instance server list           # aucune instance de la session
```

Attendu : `exports/repetition/rapport-purge.md` indique « purge complète », `sessions/repetition/`
n'existe plus, `git status` ne montre aucun fichier de `sessions/`, `exports/` ou
`identifiants/`.

Reprise : interrompre `purger` (Ctrl+C pendant `tofu destroy`) puis le relancer : il termine
sans erreur (AS 4.3).

## Scénario D : cas limites

- Clé Scaleway invalide (variable vidée) : message d'erreur clair dans l'interface ; les
  réponses de référence restent lisibles dans `exemples/bloc-operatoire/resultats-reference/`.
- PDF de plan vectoriel : avertissement « exporter le plan en PNG ».
- Garde-fou : créer une session de répétition avec `fin` dans le passé proche, vérifier qu'à
  l'échéance la clé de session est refusée par l'API Scaleway et que l'instance s'éteint.
- Partage de connexion : l'adresse HTTPS répond depuis un téléphone en 4G.
