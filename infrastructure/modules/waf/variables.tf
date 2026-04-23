############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive the CloudFront-scoped Web ACL name."
  type        = string

  validation {
    condition     = length(trimspace(var.name_prefix)) > 0
    error_message = "name_prefix must not be empty."
  }
}

variable "tags" {
  description = "Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module."
  type        = map(string)

  validation {
    condition     = length(var.tags) > 0
    error_message = "tags must contain at least the baseline environment tags."
  }
}

############################################
# Web ACL behavior
############################################

variable "web_acl_name_suffix" {
  description = "Suffix appended to name_prefix when rendering the CloudFront-scoped Web ACL name."
  type        = string
  default     = "edge"

  validation {
    condition     = length(trimspace(var.web_acl_name_suffix)) > 0
    error_message = "web_acl_name_suffix must not be empty."
  }
}

variable "rate_limit_enabled" {
  description = "Whether the fixed IP-based rate-limit rule is enabled in the CloudFront-scoped Web ACL."
  type        = bool
  default     = true
}

variable "rate_limit" {
  description = "Request limit for the fixed IP-based rate-limit rule when rate limiting is enabled."
  type        = number
  default     = 2000

  validation {
    condition     = var.rate_limit >= 100
    error_message = "rate_limit must be at least 100."
  }
}
