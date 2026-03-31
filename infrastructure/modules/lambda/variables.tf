############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive Lambda function and log group names."
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
# Lambda function definitions
############################################

variable "functions" {
  description = <<-EOT
    Map of Lambda function definitions keyed by logical workload name.

    The module stays infrastructure-focused in v1:
    - package_path points to a ready ZIP artifact
    - IAM roles are consumed through role_arn
    - environment variables are passed through as simple key/value pairs
  EOT

  type = map(object({
    description           = string
    role_arn              = string
    runtime               = string
    handler               = string
    package_path          = string
    memory_size           = optional(number)
    timeout               = optional(number)
    environment_variables = optional(map(string))
    log_retention_in_days = optional(number)
  }))

  validation {
    condition     = length(var.functions) > 0
    error_message = "functions must not be empty."
  }

  validation {
    condition = alltrue([
      for function_key in keys(var.functions) :
      can(regex("^[a-z0-9-]+$", function_key))
    ])
    error_message = "Function keys must be lowercase, hyphenated logical workload names."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      length(trimspace(function.description)) > 0
    ])
    error_message = "Each function description must not be empty."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      length(trimspace(function.role_arn)) > 0
    ])
    error_message = "Each function role_arn must not be empty."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      length(trimspace(function.runtime)) > 0
    ])
    error_message = "Each function runtime must not be empty."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      length(trimspace(function.handler)) > 0
    ])
    error_message = "Each function handler must not be empty."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      length(trimspace(function.package_path)) > 0
    ])
    error_message = "Each function package_path must not be empty."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      try(function.memory_size, 128) >= 128 &&
      try(function.memory_size, 128) <= 10240
    ])
    error_message = "Each function memory_size must be between 128 and 10240 MB."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      try(function.timeout, 3) >= 1 &&
      try(function.timeout, 3) <= 900
    ])
    error_message = "Each function timeout must be between 1 and 900 seconds."
  }

  validation {
    condition = alltrue([
      for function in values(var.functions) :
      contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], try(function.log_retention_in_days, 14))
    ])
    error_message = "Each function log_retention_in_days must use a supported CloudWatch Logs retention value."
  }
}
