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

      actions = [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ]

      resources = [
        var.events_table_arn,
        "${var.events_table_arn}/index/*"
      ]
    }
  }

  dynamic "statement" {
    for_each = each.value.access_profile == "rsvp_transaction" ? [1] : []

    content {
      sid    = "RsvpTransactionalDynamoAccess"
      effect = "Allow"

      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:TransactWriteItems",
        "dynamodb:UpdateItem"
      ]

      resources = [
        var.events_table_arn,
        "${var.events_table_arn}/index/*",
        var.rsvps_table_arn,
        "${var.rsvps_table_arn}/index/*"
      ]
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
