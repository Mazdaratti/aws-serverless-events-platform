############################################
# Primary queues with DLQs
############################################

# These queues are split from the non-DLQ case so the redrive configuration
# stays easy to read for beginners. Each queue in this block gets a dedicated
# dead-letter queue and a redrive policy.
resource "aws_sqs_queue" "primary_with_dlq" {
  for_each = local.queues_with_dlq

  name                       = local.rendered_queue_names[each.key]
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  receive_wait_time_seconds  = each.value.receive_wait_time_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = each.value.max_receive_count
  })

  tags = merge(var.tags, {
    Name = local.rendered_queue_names[each.key]
  })

  lifecycle {
    precondition {
      condition = (
        each.value.max_receive_count != null &&
        floor(each.value.max_receive_count) == each.value.max_receive_count &&
        each.value.max_receive_count >= 1
      )
      error_message = "max_receive_count must be a whole number greater than or equal to 1 when create_dlq is true."
    }
  }
}

############################################
# Primary queues without DLQs
############################################

# These queues use the same core queue settings, but intentionally omit the
# redrive policy because no DLQ is attached.
resource "aws_sqs_queue" "primary_without_dlq" {
  for_each = local.queues_without_dlq

  name                       = local.rendered_queue_names[each.key]
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  receive_wait_time_seconds  = each.value.receive_wait_time_seconds

  tags = merge(var.tags, {
    Name = local.rendered_queue_names[each.key]
  })
}

############################################
# Dedicated dead-letter queues
############################################

# In v1, a queue-level DLQ reuses the same timing settings as its source queue.
# That keeps the module interface small while still making the DLQ behavior
# explicit and production-like.
resource "aws_sqs_queue" "dlq" {
  for_each = local.queues_with_dlq

  name                       = local.rendered_dlq_names[each.key]
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  receive_wait_time_seconds  = each.value.receive_wait_time_seconds

  tags = merge(var.tags, {
    Name = local.rendered_dlq_names[each.key]
  })
}

############################################
# DLQ allow policies
############################################

# This policy makes the source-to-DLQ relationship explicit instead of relying
# on a looser default.
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  for_each = local.queues_with_dlq

  queue_url = aws_sqs_queue.dlq[each.key].id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.primary_with_dlq[each.key].arn]
  })
}
