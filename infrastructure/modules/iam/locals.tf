############################################
# Normalized workload configuration
############################################

locals {
  # These defaults keep the workload input small while still making the module
  # behavior explicit and easy to read.
  workload_defaults = {
    enable_logs = true
    enable_xray = false
  }

  # Normalize the caller input once so the rest of the module can work with a
  # fully-populated workload map.
  normalized_workloads = {
    for workload_key, workload in var.workloads :
    workload_key => {
      access_profile = workload.access_profile
      enable_logs    = coalesce(workload.enable_logs, local.workload_defaults.enable_logs)
      enable_xray    = coalesce(workload.enable_xray, local.workload_defaults.enable_xray)
    }
  }

  # Render stable IAM names from the shared prefix and logical workload key.
  rendered_role_names = {
    for workload_key in keys(local.normalized_workloads) :
    workload_key => "${var.name_prefix}-${workload_key}-role"
  }

  rendered_policy_names = {
    for workload_key in keys(local.normalized_workloads) :
    workload_key => "${var.name_prefix}-${workload_key}-policy"
  }

  # Each access profile expands to a fixed least-privilege intent. The concrete
  # IAM actions will be generated from this profile data in main.tf.
  access_profiles = {
    # Create-event performs one canonical event write and nothing broader.
    create_event = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = false
    }

    # Get-event is a single-record public read by primary key.
    get_event = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = false
    }

    # List-events needs read access for both direct item reads and the current
    # temporary broad-list scan path.
    list_events = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = true
    }

    # List-my-events uses the creator-events GSI for one authenticated
    # creator-scoped read path and does not need table scan access.
    list_my_events = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = false
    }

    # Update-event reads one canonical event, then performs a conditional
    # partial update on that same item.
    update_event = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = false
    }

    # Cancel-event reads one canonical event, then performs a conditional
    # lifecycle update on that same item.
    cancel_event = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = false
    }

    # RSVP is the first transactional cross-table write path, so it spans both
    # business tables and keeps helper counters consistent.
    rsvp_transaction = {
      dynamodb_table_arns = [
        var.events_table_arn,
        var.rsvps_table_arn
      ]
      sqs_queue_arns = []
      include_logs   = true
      include_xray   = false
      temporary_scan = false
    }

    # Get-event-rsvps reads the canonical event first for existence and
    # authorization, then queries one event-scoped RSVP page.
    get_event_rsvps = {
      dynamodb_table_arns = [
        var.events_table_arn,
        var.rsvps_table_arn
      ]
      sqs_queue_arns = []
      include_logs   = true
      include_xray   = false
      temporary_scan = false
    }

    # Notification-worker is intentionally isolated to asynchronous queue
    # consumption rather than synchronous business-table access.
    notification_consume = {
      dynamodb_table_arns = []
      sqs_queue_arns      = [var.notification_dispatch_queue_arn]
      include_logs        = true
      include_xray        = false
      temporary_scan      = false
    }
  }

  # Enrich each normalized workload with its derived IAM names and fixed access
  # profile definition so resource blocks can stay concise.
  resolved_workloads = {
    for workload_key, workload in local.normalized_workloads :
    workload_key => merge(workload, {
      role_name    = local.rendered_role_names[workload_key]
      policy_name  = local.rendered_policy_names[workload_key]
      access_rules = local.access_profiles[workload.access_profile]
    })
  }
}
