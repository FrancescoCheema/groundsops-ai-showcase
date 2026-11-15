# Optional DNS record for this environment in the domain's Route 53 hosted zone.
# Registering a domain in Route 53 creates the hosted zone automatically.
# Example: -var domain_name=groundsopsai.ca -var hostname=staging
#          creates staging.groundsopsai.ca -> this environment's static IP.

variable "domain_name" {
  type        = string
  description = "Domain with a public Route 53 hosted zone, e.g. groundsopsai.ca. Empty skips DNS."
  default     = ""
}

variable "hostname" {
  type        = string
  description = "Subdomain for this environment: staging, app (production) or demo."
  default     = ""

  validation {
    condition     = var.hostname == "" || can(regex("^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", var.hostname))
    error_message = "hostname must be a single DNS label such as staging, app or demo."
  }
}

locals {
  dns_enabled = var.domain_name != "" && var.hostname != ""
  fqdn        = local.dns_enabled ? "${var.hostname}.${var.domain_name}" : ""
}

data "aws_route53_zone" "domain" {
  count        = local.dns_enabled ? 1 : 0
  name         = var.domain_name
  private_zone = false
}

resource "aws_route53_record" "app" {
  count   = local.dns_enabled ? 1 : 0
  zone_id = data.aws_route53_zone.domain[0].zone_id
  name    = local.fqdn
  type    = "A"
  ttl     = 300
  records = [aws_lightsail_static_ip.staging.ip_address]
}

output "app_url" {
  description = "Public URL for this environment once DNS is configured."
  value       = local.dns_enabled ? "https://${local.fqdn}" : null
}
