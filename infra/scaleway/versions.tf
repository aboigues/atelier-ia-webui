# Versions figées (constitution, principe V ; research.md R7). L'état est local, rangé hors dépôt
# dans sessions/<id>/tofu/ : `tofu init -backend-config=path=...` (outils/atelier/session.py).
terraform {
  required_version = ">= 1.13.10"

  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "= 2.93.0"
    }
  }

  backend "local" {}
}

provider "scaleway" {
  # Clé, organisation et projet lus dans l'environnement (SCW_*) préparé depuis le profil
  # `scw --profile telemach` ; jamais écrits dans un fichier.
  region = "fr-par"
  zone   = "fr-par-1"
}
