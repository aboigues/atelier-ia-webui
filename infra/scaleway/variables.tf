# Variables d'une session (data-model.md Session). Aucune valeur secrète par défaut : les secrets
# sont générés et transmis par outils/atelier/session.py (TF_VAR_*), jamais écrits ici.

variable "session_id" {
  description = "Identifiant de la session (data-model.md Session.id), sous-domaine et étiquette."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]{3,30}$", var.session_id))
    error_message = "L'identifiant doit respecter [a-z0-9-]{3,30}."
  }
}

variable "projet_id" {
  description = "Projet Scaleway (profil telemach) : appels du modèle et politique IAM."
  type        = string
}

variable "type_instance" {
  description = "Type d'instance (data-model.md Session.type_instance)."
  type        = string
  default     = "DEV1-L"
}

variable "echeance_garde_fou" {
  description = "Échéance du garde-fou, RFC 3339 en UTC (data-model.md Session.echeance_garde_fou)."
  type        = string
  validation {
    condition     = can(formatdate("YYYY", var.echeance_garde_fou))
    error_message = "L'échéance doit être une date RFC 3339 (AAAA-MM-JJThh:mm:ssZ)."
  }
}

variable "webui_secret_key" {
  description = "Secret de signature des sessions d'Open WebUI."
  type        = string
  sensitive   = true
}

variable "formateur_courriel" {
  description = "Courriel du compte formateur (data-model.md Compte.courriel)."
  type        = string
}

variable "formateur_mot_de_passe" {
  description = "Mot de passe du compte formateur (data-model.md Compte.mot_de_passe)."
  type        = string
  sensitive   = true
}

variable "acces_jeton" {
  description = "Jeton du lien d'accès secret demandé par Caddy avant Open WebUI."
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{32,}$", var.acces_jeton))
    error_message = "Le jeton d'accès doit compter au moins 32 caractères [A-Za-z0-9_-]."
  }
}
