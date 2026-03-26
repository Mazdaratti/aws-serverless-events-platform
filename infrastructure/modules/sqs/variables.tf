############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive SQS queue and DLQ names."
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
# Queue definitions
############################################

variable "queues" {
  description = <<-EOT
    Map of queue definitions keyed by logical queue name.

    Logical queue keys should be stable, lowercase, and hyphenated because they
    are used to derive rendered queue names and output map keys.
  EOT

  type = map(object({
    create_dlq                 = optional(bool)
    visibility_timeout_seconds = optional(number)
    message_retention_seconds  = optional(number)
    receive_wait_time_seconds  = optional(number)
    max_receive_count          = optional(number)
  }))

  validation {
    condition     = length(var.queues) > 0
    error_message = "queues must not be empty."
  }

  validation {
    condition = alltrue([
      for queue_key in keys(var.queues) :
      can(regex("^[a-z0-9]+(?:-[a-z0-9]+)*$", queue_key))
    ])
    error_message = "Queue keys must be lowercase and hyphenated, for example async-side-effects or repair-jobs."
  }
}
