############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive CloudWatch alarm names."
  type        = string

  validation {
    condition     = length(trimspace(var.name_prefix)) > 0
    error_message = "name_prefix must not be empty."
  }
}

variable "tags" {
  description = "Baseline tags passed from the environment root and applied to taggable observability resources."
  type        = map(string)

  validation {
    condition     = length(var.tags) > 0
    error_message = "tags must contain at least the baseline environment tags."
  }
}

############################################
# Alarm action configuration
############################################

variable "alarm_actions" {
  description = "List of action ARNs to invoke when alarms enter ALARM state. Keep empty to create alarms without alert delivery."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for action in var.alarm_actions :
      length(trimspace(action)) > 0
    ])
    error_message = "alarm_actions entries must be non-empty strings."
  }
}

variable "ok_actions" {
  description = "List of action ARNs to invoke when alarms return to OK state. Keep empty to create alarms without OK notifications."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for action in var.ok_actions :
      length(trimspace(action)) > 0
    ])
    error_message = "ok_actions entries must be non-empty strings."
  }
}

############################################
# Dashboard configuration
############################################

variable "dashboard_enabled" {
  description = "Whether to create the CloudWatch dashboard baseline."
  type        = bool
  default     = true
}

############################################
# Lambda alarm inputs
############################################

variable "lambda_functions" {
  description = "Map of logical Lambda function key to deployed Lambda function name."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for function_key in keys(var.lambda_functions) :
      can(regex("^[a-z0-9]+(?:[-_][a-z0-9]+)*$", function_key))
    ])
    error_message = "lambda_functions keys must be lowercase and separated with hyphens or underscores, for example create-event or notification_sender."
  }

  validation {
    condition = alltrue([
      for function_name in values(var.lambda_functions) :
      length(trimspace(function_name)) > 0
    ])
    error_message = "lambda_functions values must be non-empty Lambda function names."
  }
}

############################################
# API Gateway alarm inputs
############################################

variable "api_gateway_api_id" {
  description = "Optional API Gateway HTTP API ID used for API-level CloudWatch alarms."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = (
      var.api_gateway_api_id == null ||
      length(trimspace(var.api_gateway_api_id)) > 0
    )
    error_message = "api_gateway_api_id must be null or a non-empty string."
  }
}

variable "api_gateway_stage_name" {
  description = "Optional API Gateway HTTP API stage name used with api_gateway_api_id for stage-level CloudWatch alarms."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = (
      var.api_gateway_stage_name == null ||
      length(trimspace(var.api_gateway_stage_name)) > 0
    )
    error_message = "api_gateway_stage_name must be null or a non-empty string."
  }

  validation {
    condition = (
      (var.api_gateway_api_id == null && var.api_gateway_stage_name == null) ||
      (var.api_gateway_api_id != null && var.api_gateway_stage_name != null)
    )
    error_message = "api_gateway_api_id and api_gateway_stage_name must either both be set or both be null."
  }
}

############################################
# SQS alarm inputs
############################################

variable "sqs_queue_names" {
  description = "Map of logical source queue key to deployed SQS queue name."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for queue_key in keys(var.sqs_queue_names) :
      can(regex("^[a-z0-9]+(?:[-_][a-z0-9]+)*$", queue_key))
    ])
    error_message = "sqs_queue_names keys must be lowercase and separated with hyphens or underscores, for example notification-dispatch."
  }

  validation {
    condition = alltrue([
      for queue_name in values(var.sqs_queue_names) :
      length(trimspace(queue_name)) > 0
    ])
    error_message = "sqs_queue_names values must be non-empty SQS queue names."
  }
}

variable "sqs_dlq_names" {
  description = "Map of logical dead-letter queue key to deployed SQS DLQ name."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for queue_key in keys(var.sqs_dlq_names) :
      can(regex("^[a-z0-9]+(?:[-_][a-z0-9]+)*$", queue_key))
    ])
    error_message = "sqs_dlq_names keys must be lowercase and separated with hyphens or underscores, for example notification-dispatch."
  }

  validation {
    condition = alltrue([
      for queue_name in values(var.sqs_dlq_names) :
      length(trimspace(queue_name)) > 0
    ])
    error_message = "sqs_dlq_names values must be non-empty SQS queue names."
  }
}

############################################
# EventBridge alarm inputs
############################################

variable "eventbridge_rule_names" {
  description = "Map of logical EventBridge rule key to deployed EventBridge rule name."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for rule_key in keys(var.eventbridge_rule_names) :
      can(regex("^[a-z0-9]+(?:[-_][a-z0-9]+)*$", rule_key))
    ])
    error_message = "eventbridge_rule_names keys must be lowercase and separated with hyphens or underscores."
  }

  validation {
    condition = alltrue([
      for rule_name in values(var.eventbridge_rule_names) :
      length(trimspace(rule_name)) > 0
    ])
    error_message = "eventbridge_rule_names values must be non-empty EventBridge rule names."
  }
}

variable "eventbridge_bus_name" {
  description = "Optional custom EventBridge bus name used with eventbridge_rule_names for custom-bus rule alarms."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = (
      var.eventbridge_bus_name == null ||
      length(trimspace(var.eventbridge_bus_name)) > 0
    )
    error_message = "eventbridge_bus_name must be null or a non-empty string."
  }

  validation {
    condition = (
      length(var.eventbridge_rule_names) == 0 ||
      var.eventbridge_bus_name != null
    )
    error_message = "eventbridge_bus_name must be set when eventbridge_rule_names is not empty."
  }
}

############################################
# Baseline alarm thresholds
############################################

variable "lambda_error_threshold" {
  description = "Number of Lambda errors in one period that causes a Lambda error alarm to enter ALARM state."
  type        = number
  default     = 1

  validation {
    condition     = var.lambda_error_threshold >= 1
    error_message = "lambda_error_threshold must be greater than or equal to 1."
  }
}

variable "lambda_throttle_threshold" {
  description = "Number of Lambda throttles in one period that causes a Lambda throttle alarm to enter ALARM state."
  type        = number
  default     = 1

  validation {
    condition     = var.lambda_throttle_threshold >= 1
    error_message = "lambda_throttle_threshold must be greater than or equal to 1."
  }
}

variable "api_gateway_5xx_threshold" {
  description = "Number of API Gateway HTTP API 5xx responses in one period that causes the API alarm to enter ALARM state."
  type        = number
  default     = 1

  validation {
    condition     = var.api_gateway_5xx_threshold >= 1
    error_message = "api_gateway_5xx_threshold must be greater than or equal to 1."
  }
}

variable "sqs_visible_messages_threshold" {
  description = "Approximate number of visible source-queue messages that causes the SQS depth alarm to enter ALARM state."
  type        = number
  default     = 10

  validation {
    condition     = var.sqs_visible_messages_threshold >= 1
    error_message = "sqs_visible_messages_threshold must be greater than or equal to 1."
  }
}

variable "sqs_oldest_message_age_seconds_threshold" {
  description = "Approximate source-queue oldest message age in seconds that causes the SQS age alarm to enter ALARM state."
  type        = number
  default     = 300

  validation {
    condition     = var.sqs_oldest_message_age_seconds_threshold >= 60
    error_message = "sqs_oldest_message_age_seconds_threshold must be greater than or equal to 60."
  }
}

variable "sqs_dlq_visible_messages_threshold" {
  description = "Approximate number of visible DLQ messages that causes the SQS DLQ alarm to enter ALARM state."
  type        = number
  default     = 1

  validation {
    condition     = var.sqs_dlq_visible_messages_threshold >= 1
    error_message = "sqs_dlq_visible_messages_threshold must be greater than or equal to 1."
  }
}

variable "eventbridge_failed_invocations_threshold" {
  description = "Number of EventBridge failed invocations in one period that causes a rule alarm to enter ALARM state."
  type        = number
  default     = 1

  validation {
    condition     = var.eventbridge_failed_invocations_threshold >= 1
    error_message = "eventbridge_failed_invocations_threshold must be greater than or equal to 1."
  }
}
