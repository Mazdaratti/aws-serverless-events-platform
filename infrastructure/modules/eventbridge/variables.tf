############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive EventBridge resource names."
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
# Event bus configuration
############################################

variable "event_bus_name" {
  description = "Optional explicit custom EventBridge event bus name. When null, the module derives the name from name_prefix."
  type        = string
  default     = null

  validation {
    condition = (
      var.event_bus_name == null ||
      length(trimspace(var.event_bus_name)) > 0
    )
    error_message = "event_bus_name must be null or a non-empty string."
  }
}
