############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive SNS resource names."
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
# Topic configuration
############################################

variable "topic_name" {
  description = "Optional explicit SNS topic name. When null, the module derives the name from name_prefix."
  type        = string
  default     = null

  validation {
    condition = (
      var.topic_name == null ||
      length(trimspace(var.topic_name)) > 0
    )
    error_message = "topic_name must be null or a non-empty string."
  }
}

variable "email_subscriptions" {
  description = "Email endpoints to subscribe to the SNS topic. Email subscriptions require confirmation before receiving messages."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for email in var.email_subscriptions :
      length(trimspace(email)) > 0
    ])
    error_message = "email_subscriptions must contain only non-empty strings."
  }
}
