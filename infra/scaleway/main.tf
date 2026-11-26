# Ressources d'une session (data-model.md « Ressources Scaleway d'une session »). Toutes portent
# l'étiquette atelier-session=<id> quand la ressource l'accepte (inventaire de purge).

locals {
  site = "${var.session_id}.atelier.telemach-learning.fr"
}

# --- Accès au modèle : application IAM dédiée, droits minimaux, clé expirante ---------------

resource "scaleway_iam_application" "session" {
  name        = "atelier-${var.session_id}"
  description = "Atelier IA : appels du modèle pour la session ${var.session_id}"
  tags        = ["atelier-session=${var.session_id}"]
}

resource "scaleway_iam_policy" "session" {
  name           = "atelier-${var.session_id}"
  description    = "Accès aux modèles Generative APIs seulement"
  application_id = scaleway_iam_application.session.id
  tags           = ["atelier-session=${var.session_id}"]

  rule {
    project_ids          = [var.projet_id]
    permission_set_names = ["GenerativeApisModelAccess"]
  }
}

resource "scaleway_iam_api_key" "session" {
  application_id     = scaleway_iam_application.session.id
  default_project_id = var.projet_id
  expires_at         = var.echeance_garde_fou
  description        = "Atelier IA : session ${var.session_id}, expire au garde-fou"
}

# --- Réseau ------------------------------------------------------------------------------

resource "scaleway_instance_ip" "session" {
  tags = ["atelier-session=${var.session_id}"]
}

resource "scaleway_instance_security_group" "session" {
  name                    = "atelier-${var.session_id}"
  description             = "HTTP et HTTPS seulement ; aucun SSH"
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"
  stateful                = true
  tags                    = ["atelier-session=${var.session_id}"]

  inbound_rule {
    action   = "accept"
    port     = 80
    protocol = "TCP"
  }

  inbound_rule {
    action   = "accept"
    port     = 443
    protocol = "TCP"
  }
}

# --- Instance ----------------------------------------------------------------------------

resource "scaleway_instance_server" "session" {
  name              = "atelier-${var.session_id}"
  type              = var.type_instance
  image             = "ubuntu_resolute"
  ip_id             = scaleway_instance_ip.session.id
  security_group_id = scaleway_instance_security_group.session.id
  tags              = ["atelier-session=${var.session_id}"]

  root_volume {
    size_in_gb            = 40
    delete_on_termination = true
  }

  user_data = {
    cloud-init = templatefile("${path.module}/cloud-init.yaml.tftpl", {
      site               = local.site
      compose_b64        = base64encode(file("${path.module}/../../openwebui/compose.yaml"))
      env_commun_b64     = base64encode(file("${path.module}/../../openwebui/env.commun"))
      caddyfile_b64      = base64encode(file("${path.module}/../../openwebui/Caddyfile"))
      url_api            = "https://api.scaleway.ai/${var.projet_id}/v1"
      cle_api            = scaleway_iam_api_key.session.secret_key
      webui_secret_key   = var.webui_secret_key
      formateur_courriel = var.formateur_courriel
      formateur_mdp      = var.formateur_mot_de_passe
      acces_jeton        = var.acces_jeton
      echeance           = var.echeance_garde_fou
    })
  }
}

# --- DNS (zone déléguée à Scaleway le 2026-11-26, research.md R8) ------------------------

resource "scaleway_domain_record" "session" {
  dns_zone = "atelier.telemach-learning.fr"
  name     = var.session_id
  type     = "A"
  data     = scaleway_instance_ip.session.address
  ttl      = 300
}
