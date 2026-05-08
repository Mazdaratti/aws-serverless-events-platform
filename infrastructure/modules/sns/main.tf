############################################
# SNS admin notification topic
############################################

# This topic is the reusable baseline for platform/admin broadcast
# notifications. EventBridge publish permissions are intentionally added later
# in the concrete environment wiring where the source rule ARN is known.
resource "aws_sns_topic" "this" {
  name = local.topic_name

  tags = local.topic_tags
}

############################################
# Optional email subscriptions
############################################

# Email subscriptions require the recipient to confirm the subscription before
# messages are delivered. The module creates only the subscription resources;
# confirmation remains an out-of-band recipient action.
resource "aws_sns_topic_subscription" "email" {
  for_each = var.email_subscriptions

  topic_arn = aws_sns_topic.this.arn
  protocol  = "email"
  endpoint  = each.value
}
