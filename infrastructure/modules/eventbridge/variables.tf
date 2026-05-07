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

variable "rules" {
  description = <<-EOT
    EventBridge rules and targets to create on the custom event bus.

    Each rule defines one event pattern and one or more targets. Target
    resource policies, such as SNS topic policies or SQS queue policies, are
    intentionally owned outside this module by the target resource owner or
    environment composition.
  EOT

  type = map(object({
    name          = optional(string)
    description   = optional(string)
    event_pattern = any
    targets = map(object({
      arn      = string
      role_arn = optional(string)
    }))
  }))

  default = {}

  validation {
    condition = alltrue([
      for rule_key in keys(var.rules) :
      length(trimspace(rule_key)) > 0 &&
      trimspace(rule_key) == rule_key
    ])
    error_message = "rules keys must be non-empty strings with no leading or trailing whitespace."
  }

  validation {
    condition = alltrue([
      for rule_key, rule in var.rules :
      try(rule.name, null) != null || (
        length(rule_key) <= 64 &&
        length(regexall("^[A-Za-z0-9_-]+$", rule_key)) > 0
      )
    ])
    error_message = "rules keys used as default rule names must be 64 characters or fewer and contain only letters, numbers, underscores, and hyphens."
  }

  validation {
    condition = alltrue([
      for rule in values(var.rules) :
      try(rule.name, null) == null || (
        length(trimspace(rule.name)) > 0 &&
        trimspace(rule.name) == rule.name &&
        length(rule.name) <= 64 &&
        length(regexall("^[A-Za-z0-9_-]+$", rule.name)) > 0
      )
    ])
    error_message = "Each rule name must be omitted or set to a 64-character-or-shorter value containing only letters, numbers, underscores, and hyphens."
  }

  validation {
    condition = alltrue([
      for rule in values(var.rules) :
      try(rule.description, null) == null ||
      length(trimspace(rule.description)) > 0
    ])
    error_message = "Each rule description must be omitted or set to a non-empty string."
  }

  validation {
    condition = alltrue([
      for rule in values(var.rules) :
      can(jsonencode(rule.event_pattern)) &&
      can(keys(rule.event_pattern)) &&
      length(keys(rule.event_pattern)) > 0
    ])
    error_message = "Each rule event_pattern must be a non-empty object that can be encoded as JSON."
  }

  validation {
    condition = alltrue([
      for rule in values(var.rules) :
      length(rule.targets) > 0
    ])
    error_message = "Each rule must define at least one target."
  }

  validation {
    condition = alltrue(flatten([
      for rule in values(var.rules) : [
        for target_key in keys(rule.targets) :
        length(trimspace(target_key)) > 0 &&
        trimspace(target_key) == target_key &&
        length(target_key) <= 64 &&
        length(regexall("^[A-Za-z0-9_-]+$", target_key)) > 0
      ]
    ]))
    error_message = "Each target key must be a 64-character-or-shorter value containing only letters, numbers, underscores, and hyphens."
  }

  validation {
    condition = alltrue(flatten([
      for rule in values(var.rules) : [
        for target in values(rule.targets) :
        length(trimspace(target.arn)) > 0
      ]
    ]))
    error_message = "Each target arn must be a non-empty string."
  }

  validation {
    condition = alltrue(flatten([
      for rule in values(var.rules) : [
        for target in values(rule.targets) :
        try(target.role_arn, null) == null ||
        length(trimspace(target.role_arn)) > 0
      ]
    ]))
    error_message = "Each target role_arn must be omitted or set to a non-empty string."
  }
}
