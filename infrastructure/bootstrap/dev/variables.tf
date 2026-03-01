variable "aws_region" {
  description = "AWS region where backend resources are created."
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used in resource naming and tags."
  type        = string
  default     = "aws-serverless-events-platform"
}

variable "environment" {
  description = "Environment name used in naming and tags."
  type        = string
  default     = "dev"
}

variable "common_tags" {
  description = "Additional tags to apply to resources."
  type        = map(string)
  default     = {
    ManagedBy = "Terraform"
  }
}

variable "state_bucket_name" {
  description = "Optional explicit name for the Terraform state bucket."
  type        = string
  default     = null
}

variable "lock_table_name" {
  description = "Optional explicit name for the Terraform lock table."
  type        = string
  default     = null
}

