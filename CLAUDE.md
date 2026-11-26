# atelier-ia-webui

Environnement de travaux pratiques (Open WebUI + modèles ouverts Scaleway Paris) pour les
formations IA de Telemach Learning. Principes non négociables : `.specify/memory/constitution.md`.

## Règles critiques (à ne jamais oublier)

- **Toujours répondre en français**, orthographe complète (accents, diacritiques) ; tutoyer
  Alexandre.
- **Zéro emoji** — partout, sans exception (code, docs, interface, commits).
- **Aucun document client dans le dépôt** — ni plan, ni CCTP, ni IFC, ni liste de participants,
  même anonymisé. Seul le jeu fictif `exemples/` est versionné. Avant chaque commit :
  `git status` et vérifier qu'aucun fichier de `sessions/`, `documents-clients/`, `exports/`
  ou `identifiants/` n'apparaît.
- **`--profile telemach`** sur toutes les commandes `scw` (le profil par défaut pointe sur un
  autre projet).
- **Versions** : toujours vérifier la dernière version stable (releases GitHub, registre) avant
  d'ajouter ou de mettre à jour une image, un outil ou une dépendance ; figer le tag, jamais
  `latest`.
- **Pas de Copilot, pas d'OpenAI, pas de « SecNumCloud »** : modèles ouverts (Mistral, Llama)
  chez Scaleway Paris uniquement.
- **PR : création autorisée, merge interdit** — commit + push + `gh pr create` possibles, jamais
  `gh pr merge` : Alexandre merge lui-même. Nouvelle branche après chaque merge ; PR toujours
  vers `main`.

## Méthode : Spec-Kit (v1.4.5)

Cycle par fonctionnalité : `/speckit-specify` -> `/speckit-clarify` (si besoin) ->
`/speckit-plan` -> `/speckit-tasks` -> `/speckit-analyze` -> `/speckit-implement`.
Fonctionnalité en cours : `specs/001-environnement-tp-session/` (spec rédigée, plan à faire).

## Contexte

- Premier client : un intégrateur de blocs opératoires. Atelier de formation de 2 jours en
  décembre 2026, jusqu'à 10 participants (nom du client, dates et suivi commercial :
  `CLAUDE.local.md`, non versionné). Le programme promet : « Modèle d'IA ouvert (Mistral) hébergé à Paris, mis à
  disposition par le formateur pour la durée de la formation ; aucun document n'est conservé
  après la session ».
- Suivi commercial et programme : dépôt `telemach-learning` (ne pas y copier de code de ce
  dépôt).
- Démo d'origine (ligne de commande) : `exemples/bloc-operatoire/demo.py` (appel de l'API
  Scaleway compatible OpenAI, plans envoyés en image base64, IFC converti en JSON sans
  bibliothèque) ; corrigé : `exemples/bloc-operatoire/CORRIGE.md` ; réponses de référence du
  2026-11-24 : `exemples/bloc-operatoire/resultats-reference/`.
- Clé Scaleway : lue à l'exécution (`scw --profile telemach config get secret-key`), jamais
  écrite dans un fichier versionné.
- Docker est disponible en local (WSL2).
