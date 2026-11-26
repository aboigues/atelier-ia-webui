# Contrat : filtre Open WebUI `filtre_ifc`

Fichier unique `openwebui/fonctions/filtre_ifc.py`, bibliothèque standard uniquement, chargé
dans Open WebUI comme fonction de type filtre et attaché aux modèles « Assistant bureau
d'études » et « Assistant secours ». Le cœur de conversion est une fonction pure testable hors
d'Open WebUI.

## Fonction pure

```text
espaces_ifc(texte_ifc: str) -> list[dict[str, str | bool | float]]
tableau_markdown(espaces: list[dict]) -> str
```

- Entrée : contenu d'un fichier STEP (`ISO-10303-21`), schéma IFC2X3 ou IFC4.
- Sortie : une entrée par `IFCSPACE` avec `code`, `nom` et chaque propriété simple qui lui est
  rattachée (voir `data-model.md`).
- Erreurs : `ErreurIFC("fichier IFC illisible : ...")`, `ErreurIFC("maquette trop volumineuse :
  N espaces (limite 2 000)")`.
- Référence de test : `exemples/bloc-operatoire/maquette-bloc.ifc` donne 4 salles d'opération
  SO1 à SO4 ; SO2 `PlafondSoufflant` = non ; SO4 `SurpressionPa` = 10.

## Comportement dans Open WebUI

`inlet(body, __user__, __event_emitter__)` :

1. Pour chaque fichier joint dont le nom se termine par `.ifc` (insensible à la casse) :
   lire le fichier brut dans le stockage d'Open WebUI ; refuser au-delà de 200 Mo.
2. Remplacer le contenu transmis au modèle par :
   `Tableau des espaces extrait de <nom>.ifc (N espaces) :` suivi du tableau Markdown.
3. Émettre le tableau comme source consultable (`citation`) pour que le participant puisse
   l'afficher (AS 2.1).
4. En cas d'erreur : émettre un statut lisible (« Conversion IFC impossible : ... ») et retirer
   le fichier de la demande plutôt que d'envoyer le STEP brut au modèle.

Pour chaque PDF joint dont le texte extrait fait moins de 200 caractères par page : ajouter au
message une note « Ce PDF semble être un plan vectoriel : exportez-le en PNG pour que le
modèle le lise » et émettre le même avertissement en statut.

Les autres fichiers ne sont pas modifiés. Le filtre n'effectue aucun appel réseau.

Vannes (`Valves`) : `taille_max_mo` (200), `espaces_max` (2000).
