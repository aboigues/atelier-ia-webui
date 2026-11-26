output "site" {
  description = "Adresse HTTPS de la session."
  value       = "https://${local.site}"
}

output "ip" {
  description = "Adresse IP publique de l'instance."
  value       = scaleway_instance_ip.session.address
}

output "instance_id" {
  description = "Identifiant de l'instance (inventaire de purge)."
  value       = scaleway_instance_server.session.id
}

output "cle_api" {
  description = "Clé IAM de la session (lue par atelier pour configurer Open WebUI)."
  value       = scaleway_iam_api_key.session.secret_key
  sensitive   = true
}
