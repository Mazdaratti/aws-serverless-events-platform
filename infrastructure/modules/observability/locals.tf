############################################
# Shared alarm defaults
############################################

locals {
  # Keep the first baseline intentionally simple: standard-resolution
  # CloudWatch service metrics, one-minute periods, and explicit missing-data
  # handling so sparse failure metrics do not sit in INSUFFICIENT_DATA forever.
  alarm_defaults = {
    period              = 60
    evaluation_periods  = 2
    datapoints_to_alarm = 1
    comparison_operator = "GreaterThanOrEqualToThreshold"
    treat_missing_data  = "notBreaching"
  }
}

############################################
# Lambda alarm definitions
############################################

locals {
  lambda_error_alarms = {
    for function_key, function_name in var.lambda_functions :
    "lambda-${function_key}-errors" => merge(local.alarm_defaults, {
      alarm_name        = "${var.name_prefix}-lambda-${function_key}-errors"
      alarm_description = "Lambda function ${function_name} reported one or more errors in the current period."
      namespace         = "AWS/Lambda"
      metric_name       = "Errors"
      statistic         = "Sum"
      threshold         = var.lambda_error_threshold
      dimensions = {
        FunctionName = function_name
      }
    })
  }

  lambda_throttle_alarms = {
    for function_key, function_name in var.lambda_functions :
    "lambda-${function_key}-throttles" => merge(local.alarm_defaults, {
      alarm_name        = "${var.name_prefix}-lambda-${function_key}-throttles"
      alarm_description = "Lambda function ${function_name} reported one or more throttled invocations in the current period."
      namespace         = "AWS/Lambda"
      metric_name       = "Throttles"
      statistic         = "Sum"
      threshold         = var.lambda_throttle_threshold
      dimensions = {
        FunctionName = function_name
      }
    })
  }
}

############################################
# API Gateway alarm definitions
############################################

locals {
  api_gateway_5xx_alarms = var.api_gateway_api_id == null ? {} : {
    "api-gateway-5xx" = merge(local.alarm_defaults, {
      alarm_name        = "${var.name_prefix}-api-gateway-5xx"
      alarm_description = "API Gateway HTTP API stage ${var.api_gateway_stage_name} reported one or more 5xx responses in the current period."
      namespace         = "AWS/ApiGateway"
      metric_name       = "5xx"
      statistic         = "Sum"
      threshold         = var.api_gateway_5xx_threshold
      dimensions = {
        ApiId = var.api_gateway_api_id
        Stage = var.api_gateway_stage_name
      }
    })
  }
}

############################################
# SQS alarm definitions
############################################

locals {
  sqs_visible_message_alarms = {
    for queue_key, queue_name in var.sqs_queue_names :
    "sqs-${queue_key}-visible-messages" => merge(local.alarm_defaults, {
      alarm_name        = "${var.name_prefix}-sqs-${queue_key}-visible-messages"
      alarm_description = "SQS source queue ${queue_name} has visible messages above the baseline threshold."
      namespace         = "AWS/SQS"
      metric_name       = "ApproximateNumberOfMessagesVisible"
      statistic         = "Maximum"
      threshold         = var.sqs_visible_messages_threshold
      dimensions = {
        QueueName = queue_name
      }
    })
  }

  sqs_oldest_message_age_alarms = {
    for queue_key, queue_name in var.sqs_queue_names :
    "sqs-${queue_key}-oldest-message-age" => merge(local.alarm_defaults, {
      alarm_name        = "${var.name_prefix}-sqs-${queue_key}-oldest-message-age"
      alarm_description = "SQS source queue ${queue_name} has an oldest message age above the baseline threshold."
      namespace         = "AWS/SQS"
      metric_name       = "ApproximateAgeOfOldestMessage"
      statistic         = "Maximum"
      threshold         = var.sqs_oldest_message_age_seconds_threshold
      dimensions = {
        QueueName = queue_name
      }
    })
  }

  sqs_dlq_visible_message_alarms = {
    for queue_key, queue_name in var.sqs_dlq_names :
    "sqs-${queue_key}-dlq-visible-messages" => merge(local.alarm_defaults, {
      alarm_name        = "${var.name_prefix}-sqs-${queue_key}-dlq-visible-messages"
      alarm_description = "SQS dead-letter queue ${queue_name} has one or more visible messages."
      namespace         = "AWS/SQS"
      metric_name       = "ApproximateNumberOfMessagesVisible"
      statistic         = "Maximum"
      threshold         = var.sqs_dlq_visible_messages_threshold
      dimensions = {
        QueueName = queue_name
      }
    })
  }
}

############################################
# EventBridge alarm definitions
############################################

locals {
  eventbridge_failed_invocation_alarms = {
    for rule_key, rule_name in var.eventbridge_rule_names :
    "eventbridge-${rule_key}-failed-invocations" => merge(local.alarm_defaults, {
      alarm_name        = "${var.name_prefix}-eventbridge-${rule_key}-failed-invocations"
      alarm_description = "EventBridge rule ${rule_name} reported one or more failed target invocations in the current period."
      namespace         = "AWS/Events"
      metric_name       = "FailedInvocations"
      statistic         = "Sum"
      threshold         = var.eventbridge_failed_invocations_threshold
      dimensions = {
        EventBusName = var.eventbridge_bus_name
        RuleName     = rule_name
      }
    })
  }
}

############################################
# Flattened alarm map
############################################

locals {
  metric_alarms = merge(
    local.lambda_error_alarms,
    local.lambda_throttle_alarms,
    local.api_gateway_5xx_alarms,
    local.sqs_visible_message_alarms,
    local.sqs_oldest_message_age_alarms,
    local.sqs_dlq_visible_message_alarms,
    local.eventbridge_failed_invocation_alarms
  )
}
