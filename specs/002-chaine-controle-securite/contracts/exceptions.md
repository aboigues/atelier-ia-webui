# Contrat : fichier d'exceptions `securite/exceptions.toml`

Versionné. Toute modification passe par une PR (principe VII) ; le contrôle `sca` le valide.
Champs et règles : `data-model.md`, entité « Exception de sécurité ».

```toml
# Exception de classe exigée par FR-007 : vulnérabilités élevées sans correctif publié,
# listées dans le rapport sans bloquer. Réexaminée au plus tous les 90 jours.
[[exception]]
id = "elevee-sans-correctif"
type = "classe"
portee = "*"
raison = "Images tierces (Open WebUI, Caddy) : paquets système sans correctif publié ; suivi hebdomadaire."
acceptee_par = "Alexandre"
acceptee_le = 2026-11-26
reexamen_le = 2027-02-24

# Exemple de vulnérabilité individuelle (commentée, à titre de modèle)
# [[exception]]
# id = "CVE-AAAA-NNNNN"
# type = "vulnerabilite"
# portee = "ghcr.io/open-webui/open-webui"
# raison = "Composant non exposé : ..."
# acceptee_par = "Alexandre"
# acceptee_le = 2026-12-01
# reexamen_le = 2027-01-15

# Exemple de faux positif de secret (identifiant : commit:fichier:ligne, affiché par verdict_secrets.py)
# [[exception]]
# id = "<empreinte>"
# type = "secret-faux-positif"
# portee = "exemples/bloc-operatoire/..."
# raison = "Valeur fictive du jeu d'exemples, sans usage réel."
# acceptee_par = "Alexandre"
# acceptee_le = 2026-12-01
# reexamen_le = 2027-02-28
```

Comportement du verdict :

| Situation | Résultat |
|---|---|
| exception individuelle valide correspondant à `id` et `portee` | vulnérabilité `toleree`, listée |
| exception échue | ignorée, signalée « exception échue » ; la vulnérabilité est jugée sans elle |
| classe `elevee-sans-correctif` échue ou absente | les élevées sans correctif deviennent bloquantes |
| champ manquant, `acceptee_par` différent d'Alexandre, réexamen à plus de 90 jours | fichier invalide : `sca` échoue |
