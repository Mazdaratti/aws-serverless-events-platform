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
    workload_key => merge(local.workload_defaults, workload)
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
    create_event = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = false
    }

    list_events = {
      dynamodb_table_arns = [var.events_table_arn]
      sqs_queue_arns      = []
      include_logs        = true
      include_xray        = false
      temporary_scan      = true
    }

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
