############################################
# Shared AWS context
############################################

data "aws_partition" "current" {}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

############################################
# Lambda trust relationship
############################################

# v1 keeps the trust model intentionally simple: this module creates Lambda
# execution roles only, so every workload role trusts the Lambda service
# principal and nothing broader.
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    sid    = "LambdaAssumeRole"
    effect = "Allow"

    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

############################################
# Workload permission policies
############################################

# Generate one least-privilege customer-managed policy per workload. The
# statements are driven by the fixed workload profiles from locals.tf so the
# environment does not need to describe IAM internals later.
data "aws_iam_policy_document" "workload" {
  for_each = local.resolved_workloads

  dynamic "statement" {
    for_each = each.value.enable_logs ? [1] : []

    content {
      sid    = "CloudWatchLogsCreateGroup"
      effect = "Allow"

      actions = ["logs:CreateLogGroup"]

      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = each.value.enable_logs ? [1] : []

    content {
      sid    = "CloudWatchLogsWriteStream"
      effect = "Allow"

      actions = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]

      resources = [
        "arn:${data.aws_partition.current.partition}:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*:*"
      ]
    }
  }

  dynamic "statement" {
    for_each = each.value.enable_xray ? [1] : []

    content {
      sid    = "XRayWrite"
      effect = "Allow"

      actions = [
        "xray:PutTelemetryRecords",
        "xray:PutTraceSegments"
      ]

      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "create_event" ? [1] : []

    content {
      sid    = "CreateEventWriteEventsTable"
      effect = "Allow"

      actions = ["dynamodb:PutItem"]

      resources = [var.events_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "get_event" ? [1] : []

    content {
      sid    = "GetEventReadEventsTable"
      effect = "Allow"

      actions = ["dynamodb:GetItem"]

      resources = [var.events_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "update_event" ? [1] : []

    content {
      sid    = "UpdateEventReadWriteEventsTable"
      effect = "Allow"

      actions = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ]

      resources = [var.events_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "cancel_event" ? [1] : []

    content {
      sid    = "CancelEventReadWriteEventsTable"
      effect = "Allow"

      actions = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ]

      resources = [var.events_table_arn]
    }
  }

  # `Scan` is included only as a temporary contract accommodation for the
  # current broad list-events behavior. The long-term direction remains
  # validated query access patterns and GSIs.
  dynamic "statement" {
    for_each = each.value.access_profile == "list_events" ? [1] : []

    content {
      sid    = "ListEventsReadEventsTable"
      effect = "Allow"

      actions = ["dynamodb:Scan"]

      # After the listing split, the public broad-list handler only uses a
      # temporary base-table Scan path. Creator-scoped query access now belongs
      # to the dedicated list-my-events workload.
      resources = [var.events_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "list_my_events" ? [1] : []

    content {
      sid    = "ListMyEventsQueryCreatorEventsIndex"
      effect = "Allow"

      actions = ["dynamodb:Query"]

      # This handler reads creator-scoped event pages from the creator-events
      # GSI and does not need table scan access.
      resources = ["${var.events_table_arn}/index/creator-events"]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "rsvp_transaction" ? [1] : []

    content {
      sid    = "RsvpReadUpdateEventsTable"
      effect = "Allow"

      actions = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ]

      # The handler reads the canonical event item first, and the transaction
      # later updates counters on the events table. No index access is needed.
      resources = [var.events_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "rsvp_transaction" ? [1] : []

    content {
      sid    = "RsvpReadWriteRsvpsTable"
      effect = "Allow"

      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ]

      # The handler reads the current RSVP subject record and writes the
      # canonical RSVP item back to the base RSVP table.
      resources = [var.rsvps_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "rsvp_transaction" ? [1] : []

    content {
      sid    = "RsvpTransactionalWrite"
      effect = "Allow"

      actions = ["dynamodb:TransactWriteItems"]

      # DynamoDB authorizes TransactWriteItems at the API level, so this
      # permission remains wildcarded even though the handler itself touches
      # only the events and RSVP tables above.
      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "get_event_rsvps" ? [1] : []

    content {
      sid    = "GetEventRsvpsReadEvent"
      effect = "Allow"

      actions = ["dynamodb:GetItem"]

      # The read flow starts by fetching the one canonical event item so the
      # handler can apply existence and creator/admin authorization rules.
      resources = [var.events_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "get_event_rsvps" ? [1] : []

    content {
      sid    = "GetEventRsvpsQueryRsvps"
      effect = "Allow"

      actions = ["dynamodb:Query"]

      # After the event read succeeds, the handler queries RSVP items directly
      # from the base RSVP table by event_pk. No write, scan, or index access
      # is needed for this phase.
      resources = [var.rsvps_table_arn]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "notification_consume" ? [1] : []

    content {
      sid    = "NotificationQueueConsume"
      effect = "Allow"

      actions = [
        "sqs:ChangeMessageVisibility",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ReceiveMessage"
      ]

      resources = [var.notification_dispatch_queue_arn]
    }
  }
}

############################################
# Lambda execution roles
############################################

resource "aws_iam_role" "workload" {
  for_each = local.resolved_workloads

  name               = each.value.role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(var.tags, {
    Name = each.value.role_name
  })
}

############################################
# Customer-managed workload policies
############################################

resource "aws_iam_policy" "workload" {
  for_each = local.resolved_workloads

  name   = each.value.policy_name
  policy = data.aws_iam_policy_document.workload[each.key].json

  tags = merge(var.tags, {
    Name = each.value.policy_name
  })
}

############################################
# Policy attachments
############################################

resource "aws_iam_role_policy_attachment" "workload" {
  for_each = local.resolved_workloads

  role       = aws_iam_role.workload[each.key].name
  policy_arn = aws_iam_policy.workload[each.key].arn
}
