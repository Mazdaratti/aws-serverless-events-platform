############################################
# CloudWatch metric alarms
############################################

# The module builds one normalized alarm map in locals.tf and creates all
# metric alarms through this single resource. That keeps service-specific
# metric details close to the local definitions while keeping resource creation
# easy to review.
resource "aws_cloudwatch_metric_alarm" "metric" {
  for_each = local.metric_alarms

  alarm_name        = each.value.alarm_name
  alarm_description = each.value.alarm_description

  namespace   = each.value.namespace
  metric_name = each.value.metric_name
  dimensions  = each.value.dimensions
  statistic   = each.value.statistic
  period      = each.value.period

  comparison_operator = each.value.comparison_operator
  threshold           = each.value.threshold
  evaluation_periods  = each.value.evaluation_periods
  datapoints_to_alarm = each.value.datapoints_to_alarm
  treat_missing_data  = each.value.treat_missing_data

  actions_enabled = length(var.alarm_actions) > 0 || length(var.ok_actions) > 0
  alarm_actions   = var.alarm_actions
  ok_actions      = var.ok_actions

  tags = merge(var.tags, {
    Name = each.value.alarm_name
  })
}

############################################
# CloudWatch dashboard
############################################

# The dashboard is optional because some callers may want alarms only. When it
# is enabled, at least one dashboard-supported service input must be provided so
# Terraform does not create an empty dashboard.
resource "aws_cloudwatch_dashboard" "this" {
  count = var.dashboard_enabled ? 1 : 0

  dashboard_name = local.dashboard_name
  dashboard_body = jsonencode(local.dashboard_body)

  lifecycle {
    precondition {
      condition     = length(local.dashboard_widgets) > 0
      error_message = "dashboard_enabled requires at least one dashboard-supported metric input."
    }
  }
}
