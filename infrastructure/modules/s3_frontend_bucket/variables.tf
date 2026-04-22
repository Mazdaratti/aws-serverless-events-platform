############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive the frontend origin bucket name."
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
# Frontend origin bucket behavior
############################################

variable "bucket_name_suffix" {
  description = "Suffix appended to name_prefix when rendering the private frontend origin bucket name."
  type        = string
  default     = "frontend"

  validation {
    condition     = length(trimspace(var.bucket_name_suffix)) > 0
    error_message = "bucket_name_suffix must not be empty."
  }
}

variable "versioning_enabled" {
  description = "Whether S3 bucket versioning is enabled for the private frontend origin bucket."
  type        = bool
  default     = false
}

variable "force_destroy" {
  description = "Whether Terraform may destroy the frontend origin bucket even when it still contains objects."
  type        = bool
  default     = false
}
