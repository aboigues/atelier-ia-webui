# atelier-ia-webui

Environnement de travaux pratiques des formations IA de Telemach Learning : une interface web
(Open WebUI) reliée à des modèles d'IA ouverts hébergés par Scaleway à Paris, créée pour une
session de formation et détruite ensuite, documents compris.

- Principes du projet : `.specify/memory/constitution.md`
- Spécifications : `specs/001-environnement-tp-session/` (environnement de TP),
  `specs/002-chaine-controle-securite/` (contrôles de sécurité du dépôt)
- Jeu de documents fictifs et corrigé : `exemples/bloc-operatoire/`

Le projet suit la méthode Spec-Kit (`/speckit-plan`, `/speckit-tasks`, `/speckit-implement`).

## Contrôles de sécurité

Chaque PR vers `main` doit passer six contrôles bloquants (constitution, principe VII) :
`lint`, `sast-codeql`, `sca`, `iac`, `secrets`, `tests`. `main` est protégée par un ruleset
versionné (`.github/rulesets/main.json`) : ni push direct ni force-push, merge en « squash » ou
« rebase » uniquement, sans contournement possible.

- Avant chaque envoi : `outils/securite/controles-locaux.sh` (ou `--rapide` pour sauter
  l'analyse des vulnérabilités) donne le même verdict que la PR, hors CodeQL.
- Outils : figés par version et empreinte dans `securite/outils.lock` (images épinglées ou
  binaires officiels à somme vérifiée) ; aucune action GitHub tierce hors `actions/checkout` et
  `github/codeql-action`, épinglées par SHA.
- Exceptions : `securite/exceptions.toml`, acceptées par Alexandre, datées, réexaminées au plus
  tous les 90 jours ; une exception échue redevient bloquante.
- Protection de `main` : `outils/securite/regles_github.py appliquer|verifier`.
- Analyse hebdomadaire des vulnérabilités : `.github/workflows/analyse-hebdomadaire.yml`.
