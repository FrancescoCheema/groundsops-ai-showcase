variable "aws_region" {
  description = "AWS region for GroundsOps authentication."
  type        = string
  default     = "ca-central-1"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "portfolio"
}
