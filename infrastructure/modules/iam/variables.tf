############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive IAM role and policy names."
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
# Resource ARNs used for least-privilege policies
############################################

variable "events_table_arn" {
  description = "ARN of the DynamoDB events table used by workload-specific IAM policies."
  type        = string

  validation {
    condition     = length(trimspace(var.events_table_arn)) > 0
    error_message = "events_table_arn must not be empty."
  }
}

variable "rsvps_table_arn" {
  description = "ARN of the DynamoDB RSVP table used by workload-specific IAM policies."
  type        = string

  validation {
    condition     = length(trimspace(var.rsvps_table_arn)) > 0
    error_message = "rsvps_table_arn must not be empty."
  }
}

variable "notification_dispatch_queue_arn" {
  description = "ARN of the notification-dispatch SQS queue used by the notification worker IAM policy."
  type        = string

  validation {
    condition     = length(trimspace(var.notification_dispatch_queue_arn)) > 0
    error_message = "notification_dispatch_queue_arn must not be empty."
  }
}

############################################
# Workload role definitions
############################################

variable "workloads" {
  description = <<-EOT
    Map of Lambda workload role definitions keyed by logical workload name.

    Supported workload keys in v1:
    - create-event
    - get-event
    - list-events
    - update-event
    - cancel-event
    - rsvp
    - get-event-rsvps
    - notification-worker
  EOT

  type = map(object({
    access_profile = string
    enable_logs    = optional(bool)
    enable_xray    = optional(bool)
  }))

  validation {
    condition     = length(var.workloads) > 0
    error_message = "workloads must not be empty."
  }

  validation {
    condition = alltrue([
      for workload_key in keys(var.workloads) :
      contains([
        "create-event",
        "get-event",
        "list-events",
        "update-event",
        "cancel-event",
        "rsvp",
        "get-event-rsvps",
        "notification-worker"
      ], workload_key)
    ])
    error_message = "workloads may only contain the supported keys: create-event, get-event, list-events, update-event, cancel-event, rsvp, get-event-rsvps, notification-worker."
  }

  validation {
    condition = alltrue([
      for workload in values(var.workloads) :
      contains([
        "create_event",
        "get_event",
        "list_events",
        "update_event",
        "cancel_event",
        "rsvp_transaction",
        "get_event_rsvps",
        "notification_consume"
      ], workload.access_profile)
    ])
    error_message = "Each workload must use one of the supported access profiles: create_event, get_event, list_events, update_event, cancel_event, rsvp_transaction, get_event_rsvps, notification_consume."
  }

  validation {
    condition = alltrue([
      for workload_key, workload in var.workloads :
      (
        workload_key == "create-event" &&
        workload.access_profile == "create_event"
        ) || (
        workload_key == "get-event" &&
        workload.access_profile == "get_event"
        ) || (
        workload_key == "list-events" &&
        workload.access_profile == "list_events"
        ) || (
        workload_key == "update-event" &&
        workload.access_profile == "update_event"
        ) || (
        workload_key == "cancel-event" &&
        workload.access_profile == "cancel_event"
        ) || (
        workload_key == "rsvp" &&
        workload.access_profile == "rsvp_transaction"
        ) || (
        # Keep each workload/profile pairing explicit so module callers get a
        # clear validation error instead of a less obvious policy mismatch.
        workload_key == "get-event-rsvps" &&
        workload.access_profile == "get_event_rsvps"
        ) || (
        workload_key == "notification-worker" &&
        workload.access_profile == "notification_consume"
      )
    ])
    error_message = "Each workload key must use its matching access profile: create-event/create_event, get-event/get_event, list-events/list_events, update-event/update_event, cancel-event/cancel_event, rsvp/rsvp_transaction, get-event-rsvps/get_event_rsvps, notification-worker/notification_consume."
  }
}
