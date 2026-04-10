############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive Cognito resource names."
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
# Cognito identity baseline inputs
############################################

variable "user_pool_name_override" {
  description = "Optional explicit Cognito User Pool name. When omitted, the module derives the name from name_prefix."
  type        = string
  default     = null
}

variable "user_pool_client_name_override" {
  description = "Optional explicit Cognito User Pool Client name. When omitted, the module derives the name from name_prefix."
  type        = string
  default     = null
}

variable "admin_group_name" {
  description = "Name of the Cognito group that represents future admin membership for platform authorization context."
  type        = string
  default     = "admin"

  validation {
    condition     = length(trimspace(var.admin_group_name)) > 0
    error_message = "admin_group_name must not be empty."
  }
}

variable "password_minimum_length" {
  description = "Minimum password length for the Cognito password policy."
  type        = number
  default     = 8

  validation {
    condition     = var.password_minimum_length >= 8
    error_message = "password_minimum_length must be at least 8."
  }
}

variable "allow_self_signup" {
  description = "Whether Cognito allows end users to sign themselves up instead of requiring admin-created users only."
  type        = bool
  default     = true
}

variable "username_case_sensitive" {
  description = "Whether Cognito usernames are case-sensitive. The platform default keeps usernames case-insensitive."
  type        = bool
  default     = false
}

variable "require_email" {
  description = "Whether the baseline identity model requires email as a standard user attribute."
  type        = bool
  default     = true
}

variable "deletion_protection_enabled" {
  description = "Whether Cognito deletion protection is enabled for the User Pool. Environment roots can set this explicitly per environment."
  type        = bool
  default     = false
}
