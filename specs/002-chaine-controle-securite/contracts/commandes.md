# Contrat : commandes de la chaîne de contrôle

Scripts en Python (bibliothèque standard) ou Bash (passant ShellCheck), sorties en français,
sans emoji. Codes de sortie : `0` succès, `1` contrôle en échec, `2` erreur d'usage ou de
configuration, `3` outil ou service indisponible (traité comme un échec par les workflows).

| Commande | Effet | Exigences |
|---|---|---|
| `outils/securite/controles-locaux.sh [--rapide]` | Exécute en local `lint` (hors CodeQL), `iac`, `secrets`, `tests` et, sauf `--rapide`, `sca`, avec les images de `securite/outils.lock`. Affiche un tableau final contrôle / verdict. | FR-014, US5 |
| `outils/securite/controle.sh <controle>` | Exécute un contrôle (`lint`, `iac`, `secrets`, `sca`, `tests`) avec les images de `securite/outils.lock` ; appelé par les workflows et par `controles-locaux.sh` ; résumé dans `GITHUB_STEP_SUMMARY` ou sur la sortie standard. | FR-002, FR-013, FR-014 |
| `outils/securite/regles_github.py appliquer` | Crée ou met à jour le ruleset de `main` depuis `.github/rulesets/main.json` ; active secret scanning et push protection ; désactive le « default setup » CodeQL. Nécessite `gh` connecté avec les droits d'administration du dépôt. Idempotent. | FR-004, FR-005, FR-006 |
| `outils/securite/regles_github.py verifier` | Compare l'état GitHub au fichier versionné et aux réglages attendus (dont `integration_id` 15368 sur chaque contrôle requis) ; code 1 et liste des écarts en cas de différence. | FR-005 |
| `outils/securite/exceptions.py verifier` | Valide `securite/exceptions.toml` (champs, 90 jours, dates) ; liste les exceptions échues ou proches de l'échéance (14 jours). | FR-008 |
| `outils/securite/verdict_secrets.py <resultats.jsonl>` | Lit les résultats de TruffleHog, ignore les faux positifs valides (`<commit>:<fichier>:<ligne>`), n'affiche jamais la valeur d'un secret ; code 1 en cas de fuite. | FR-006, FR-008, FR-012 |
| `outils/securite/verdict_codeql.py <dossier SARIF>` | Bloque toute alerte de sécurité CodeQL de niveau `error` ou `warning` ; code 3 si aucun SARIF. | FR-002, FR-012 |
| `outils/securite/verdict_vulnerabilites.py <grype.json>...` | Applique la règle R3 et les exceptions ; écrit un rapport Markdown ; code 1 s'il existe une vulnérabilité bloquante. | FR-007 |
| `outils/securite/verifier_epinglage.py` | Vérifie que chaque `uses:` est épinglé par SHA de 40 caractères suivi d'un commentaire de version, que chaque image utilisée vient de `securite/outils.lock` avec une empreinte, et qu'aucune tâche requise ne porte de condition `if:`. | FR-010, FR-015 |
| `outils/securite/demonstration.sh` | Branche et PR brouillon jetables avec un défaut par famille ; vérifie les blocages et les refus de push direct et de force-push ; nettoie. Ne touche jamais `main`. | SC-002, SC-003 |
