# Scénario 4 : Interroger une maquette IFC en langage courant

Modèle : `mistral-medium-3.5-128b` (Scaleway, Paris) - durée : 3 s

### Salles d'opération sans plafond soufflant :
- SO2

### Autres valeurs qui détonnent entre les quatre salles d'opération :

| Propriété | SO1 | SO2 | SO3 | SO4 |
|-----------|-----|-----|-----|-----|
| **PlafondSoufflant** | oui | non | oui | oui |
| **SurpressionPa** | 15.0 | 15.0 | 15.0 | 10.0 |

La salle **SO4** a une surpression de **10.0 Pa** contre **15.0 Pa** pour les autres.
