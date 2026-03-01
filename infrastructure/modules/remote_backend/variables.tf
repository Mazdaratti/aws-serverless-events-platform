variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
}

variable "environment" {
  description = "Environment name (for example: dev, stage, prod)."
  type        = string
}

variable "common_tags" {
  description = "Additional tags to apply to all resources."
  type        = map(string)
  default     = {}
}

variable "state_bucket_name" {
  description = "Optional explicit state bucket name. If null, one is generated."
  type        = string
  default     = null
}

variable "lock_table_name" {
  description = "Optional explicit lock table name. If null, one is generated."
  type        = string
  default     = null
}
