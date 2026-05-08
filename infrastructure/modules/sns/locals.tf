############################################
# Normalized SNS configuration
############################################

locals {
  # Render the SNS topic name from the shared prefix unless the caller provides
  # an explicit topic name. This keeps naming consistent between resources,
  # tags, and outputs.
  topic_name = coalesce(
    var.topic_name,
    "${var.name_prefix}-admin-notifications"
  )

  # Keep the topic Name tag close to the rendered name so the resource block can
  # stay focused on SNS behavior.
  topic_tags = merge(var.tags, {
    Name = local.topic_name
  })
}
