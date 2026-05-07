############################################
# Custom EventBridge event bus
############################################

# The event bus is the central post-commit routing surface for platform domain
# events. Rules and targets below attach to this bus, while target resource
# policies stay with the resources they protect.
resource "aws_cloudwatch_event_bus" "this" {
  name = local.event_bus_name

  tags = local.event_bus_tags
}

############################################
# EventBridge rules
############################################

# Rules match domain events on the custom bus. The caller supplies event
# patterns as structured Terraform values, and the module handles the JSON
# encoding expected by EventBridge.
resource "aws_cloudwatch_event_rule" "this" {
  for_each = local.normalized_rules

  name           = each.value.name
  description    = each.value.description
  event_bus_name = aws_cloudwatch_event_bus.this.name
  event_pattern  = jsonencode(each.value.event_pattern)

  tags = local.event_rule_tags[each.key]
}

############################################
# EventBridge targets
############################################

# Targets connect a matched rule to downstream AWS resources such as SNS topics
# or SQS queues. Permissions that allow EventBridge to use those targets are
# intentionally managed outside this module by the target owner/composition.
resource "aws_cloudwatch_event_target" "this" {
  for_each = local.event_targets

  event_bus_name = aws_cloudwatch_event_bus.this.name
  rule           = aws_cloudwatch_event_rule.this[each.value.rule_key].name
  target_id      = each.value.target_key
  arn            = each.value.arn
  role_arn       = each.value.role_arn
}
