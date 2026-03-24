############################################
# Core naming and tagging inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive DynamoDB table names."
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
# DynamoDB behavior inputs
############################################

variable "billing_mode" {
  description = "Billing mode for the DynamoDB tables."
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.billing_mode)
    error_message = "billing_mode must be either PAY_PER_REQUEST or PROVISIONED."
  }
}

variable "point_in_time_recovery_enabled" {
  description = "Enable point-in-time recovery for the DynamoDB tables."
  type        = bool
  default     = true
}

variable "table_class" {
  description = "Table class for the DynamoDB tables."
  type        = string
  default     = "STANDARD"

  validation {
    condition     = contains(["STANDARD", "STANDARD_INFREQUENT_ACCESS"], var.table_class)
    error_message = "table_class must be either STANDARD or STANDARD_INFREQUENT_ACCESS."
  }
}
