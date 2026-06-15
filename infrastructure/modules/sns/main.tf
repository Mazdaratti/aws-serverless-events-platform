############################################
# SNS admin notification topic
############################################

# This topic carries platform and administrative broadcast notifications.
# Publisher permissions remain caller-owned because they depend on concrete
# source identities such as EventBridge rule ARNs.
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
