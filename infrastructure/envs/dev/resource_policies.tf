############################################
# Environment-owned resource policies
############################################

# This file contains policies that bind concrete dev resources together.
#
# Reusable modules still own their resource internals. These policies stay in
# envs/dev because each one grants a real deployed source resource access to a
# real deployed target resource in this environment.

############################################
# CloudFront access to the private S3 origin
############################################

data "aws_iam_policy_document" "frontend_bucket_cloudfront_read" {
  statement {
    sid    = "AllowCloudFrontRead"
    effect = "Allow"

    actions = ["s3:GetObject"]

    resources = [
      "${module.s3_frontend_bucket.bucket_arn}/*",
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [module.cloudfront.distribution_arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend_origin" {
  # OAC signs CloudFront requests, but S3 still needs an explicit bucket policy
  # that trusts only this distribution ARN. The policy belongs here because the
  # environment owns the concrete bucket/distribution relationship.
  bucket = module.s3_frontend_bucket.bucket_id
  policy = data.aws_iam_policy_document.frontend_bucket_cloudfront_read.json
}

############################################
# EventBridge access to the SNS admin topic
############################################

data "aws_iam_policy_document" "sns_admin_eventbridge_publish" {
  statement {
    sid    = "AllowEventBridgeAdminNotifications"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = [
      "sns:Publish",
    ]

    resources = [
      module.sns_admin_notifications.topic_arn,
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values = [
        module.eventbridge.rule_arns["admin_lifecycle_notifications"],
        module.eventbridge.rule_arns["admin_update_notifications"],
      ]
    }
  }
}

resource "aws_sns_topic_policy" "admin_notifications" {
  # EventBridge can publish admin notifications only from the concrete admin
  # lifecycle and update rules. The topic policy belongs here because the
  # environment owns the concrete rule/topic relationship.
  arn    = module.sns_admin_notifications.topic_arn
  policy = data.aws_iam_policy_document.sns_admin_eventbridge_publish.json
}

############################################
# EventBridge access to notification-dispatch SQS
############################################

data "aws_iam_policy_document" "notification_dispatch_eventbridge_send" {
  version = "2012-10-17"

  statement {
    sid    = "AllowEventBridgeParticipantDispatch"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      module.sqs.queue_arns["notification-dispatch"],
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values = [
        module.eventbridge.rule_arns["participant_notification_dispatch"],
      ]
    }
  }
}

resource "aws_sqs_queue_policy" "notification_dispatch_eventbridge" {
  # EventBridge can enqueue participant-notification planning work only from
  # the concrete participant dispatch rule. Lambda consumer permissions remain
  # separate and are not changed by this routing PR.
  queue_url = module.sqs.queue_urls["notification-dispatch"]
  policy    = data.aws_iam_policy_document.notification_dispatch_eventbridge_send.json
}
