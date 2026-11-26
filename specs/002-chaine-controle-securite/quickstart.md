# Guide de validation : chaîne de contrôle de sécurité

Commandes : `contracts/commandes.md`. Contrôles : `contracts/controles.md`.

## Prérequis

- Docker (WSL2), Python 3.11+, `gh` connecté au compte propriétaire du dépôt
  (`gh auth status`, portée `repo` et `workflow`).
- Dépôt public `aboigues/atelier-ia-webui`.

## Scénario A : contrôle local (US5)

```bash
outils/securite/controles-locaux.sh            # tout, Grype compris
outils/securite/controles-locaux.sh --rapide   # sans Grype
```

Attendu : tableau final avec `lint`, `iac`, `secrets`, `tests`, `sca` à « OK » sur `main`.
Ajouter une faute de style dans un fichier Python : `lint` passe à « ÉCHEC » avec fichier,
ligne et règle.

## Scénario B : contrôles sur une PR (US1)

Ouvrir la PR de cette fonctionnalité. Attendu : les 6 contrôles requis apparaissent et passent ;
la PR de documentation seule n'en laisse aucun « en attente » ; durée totale < 10 min.

## Scénario C : protection de `main` (US2)

Après le merge de cette fonctionnalité (dernier merge possible sans protection) :

```bash
outils/securite/regles_github.py appliquer
outils/securite/regles_github.py verifier      # code 0
```

Puis :

```bash
outils/securite/demonstration.sh
```

Attendu (SC-002, SC-003) : 6 familles de défauts détectées sur la PR brouillon, merge refusé ;
push direct et force-push sur `main` refusés ; branche et PR jetables supprimées. Dans
l'interface GitHub, seuls « Squash and merge » et « Rebase and merge » sont proposés.

## Scénario D : secrets (US3)

- `gh api repos/aboigues/atelier-ia-webui --jq .security_and_analysis` : secret scanning et
  push protection à `enabled`.
- Le contrôle `secrets` sur `main` analyse tout l'historique et trouve 0 fuite (SC-004).

## Scénario E : vulnérabilités et exceptions (US4)

```bash
outils/securite/exceptions.py verifier         # fichier valide, aucune exception échue
```

- Sur une branche de test, référencer une image connue vulnérable avec correctif publié :
  `sca` bloque. Ajouter une exception individuelle datée : `sca` passe et la liste. Mettre
  `reexamen_le` dans le passé (et `acceptee_le` en conséquence) : `sca` bloque de nouveau.
- Lancer `analyse-hebdomadaire.yml` par `gh workflow run analyse-hebdomadaire.yml` : résultats
  visibles dans l'onglet Sécurité.

## Scénario E bis : PR issue d'un fork (FR-012)

Depuis un second compte GitHub, forker le dépôt et ouvrir une PR contenant une faute de style.
Attendu : les contrôles s'exécutent sans secret ; `lint` échoue sur la faute (verdict
bloquant) et non sur le dépôt SARIF ; une PR de fork sans défaut passe au vert.

## Scénario F : chaîne d'approvisionnement (SC-007)

```bash
outils/securite/verifier_epinglage.py          # code 0
```

Remplacer une empreinte SHA par un tag (`@v7`) dans une branche de test : `lint` échoue
(vérificateur maison et zizmor).
