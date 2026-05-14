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
