############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared name prefix used to derive SES participant notification template names."
  type        = string

  validation {
    condition     = length(trimspace(var.name_prefix)) > 0
    error_message = "name_prefix must not be empty."
  }
}

############################################
# Sender identity configuration
############################################

variable "sender_email" {
  description = "Dedicated project inbox email address to verify as the SES sender identity."
  type        = string

  validation {
    condition     = can(regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$", var.sender_email))
    error_message = "sender_email must be a valid email-like address."
  }
}
