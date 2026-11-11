variable "project_name" {
  type    = string
  default = "groundsops"
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "allowed_origins" {
  type        = list(string)
  description = "HTTPS web origins permitted to fetch signed objects."
  default     = []
}

variable "force_destroy" {
  type        = bool
  description = "Keep false outside disposable development environments."
  default     = false
}
