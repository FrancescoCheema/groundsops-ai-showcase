variable "aws_region" {
  type    = string
  default = "ca-central-1"
}

variable "availability_zone" {
  type    = string
  default = "ca-central-1a"
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "bundle_id" {
  type        = string
  description = "Lightsail bundle. small_3_0 is the 2 GB public-IPv4 plan."
  default     = "small_3_0"
}

variable "ssh_allowed_cidrs" {
  type        = list(string)
  description = "Public CIDRs permitted to SSH. Use your public IP with /32."
}

variable "billing_email" {
  type        = string
  description = "Address that receives the AWS monthly budget alerts."
}

variable "monthly_budget_usd" {
  type    = number
  default = 35
}
