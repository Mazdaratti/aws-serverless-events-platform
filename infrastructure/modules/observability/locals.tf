############################################
# Shared alarm defaults
############################################

locals {
  # Apply consistent one-minute periods and explicit missing-data handling
  # across the module's standard-resolution CloudWatch service metrics.
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
      alarm_description = "SQS source queue ${queue_name} has visible messages above the configured threshold."
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
      alarm_description = "SQS source queue ${queue_name} has an oldest message age above the configured threshold."
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

############################################
# Dashboard metric definitions
############################################

locals {
  dashboard_name   = "${var.name_prefix}-observability"
  dashboard_region = data.aws_region.current.region

  lambda_invocation_metrics = [
    for function_key, function_name in var.lambda_functions :
    ["AWS/Lambda", "Invocations", "FunctionName", function_name, { label = "Lambda ${replace(function_key, "_", "-")} invocations" }]
  ]

  lambda_error_and_throttle_metrics = concat(
    [
      for function_key, function_name in var.lambda_functions :
      ["AWS/Lambda", "Errors", "FunctionName", function_name, { label = "Lambda ${replace(function_key, "_", "-")} errors" }]
    ],
    [
      for function_key, function_name in var.lambda_functions :
      ["AWS/Lambda", "Throttles", "FunctionName", function_name, { label = "Lambda ${replace(function_key, "_", "-")} throttles" }]
    ]
  )

  lambda_duration_metrics = [
    for function_key, function_name in var.lambda_functions :
    ["AWS/Lambda", "Duration", "FunctionName", function_name, { label = "Lambda ${replace(function_key, "_", "-")} p95" }]
  ]

  api_gateway_traffic_metrics = var.api_gateway_api_id == null ? [] : [
    ["AWS/ApiGateway", "Count", "ApiId", var.api_gateway_api_id, "Stage", var.api_gateway_stage_name, { label = "API Gateway requests" }],
    ["AWS/ApiGateway", "4xx", "ApiId", var.api_gateway_api_id, "Stage", var.api_gateway_stage_name, { label = "API Gateway 4xx" }],
    ["AWS/ApiGateway", "5xx", "ApiId", var.api_gateway_api_id, "Stage", var.api_gateway_stage_name, { label = "API Gateway 5xx" }]
  ]

  api_gateway_latency_metrics = var.api_gateway_api_id == null ? [] : [
    ["AWS/ApiGateway", "Latency", "ApiId", var.api_gateway_api_id, "Stage", var.api_gateway_stage_name, { label = "API Gateway latency" }]
  ]

  sqs_visible_message_metrics = concat(
    [
      for queue_key, queue_name in var.sqs_queue_names :
      ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", queue_name, { label = "SQS ${replace(queue_key, "_", "-")} visible" }]
    ],
    [
      for queue_key, queue_name in var.sqs_dlq_names :
      ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", queue_name, { label = "SQS ${replace(queue_key, "_", "-")} DLQ visible" }]
    ]
  )

  sqs_oldest_message_age_metrics = [
    for queue_key, queue_name in var.sqs_queue_names :
    ["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", queue_name, { label = "SQS ${replace(queue_key, "_", "-")} oldest age" }]
  ]

  eventbridge_invocation_metrics = concat(
    [
      for rule_key, rule_name in var.eventbridge_rule_names :
      ["AWS/Events", "Invocations", "EventBusName", var.eventbridge_bus_name, "RuleName", rule_name, { label = "EventBridge ${replace(rule_key, "_", "-")} invocations" }]
    ],
    [
      for rule_key, rule_name in var.eventbridge_rule_names :
      ["AWS/Events", "FailedInvocations", "EventBusName", var.eventbridge_bus_name, "RuleName", rule_name, { label = "EventBridge ${replace(rule_key, "_", "-")} failed" }]
    ]
  )
}

############################################
# Dashboard widgets
############################################

locals {
  # The dashboard stays compact and service-oriented. Widgets are added only
  # when the corresponding service inputs are present, so partial module use
  # does not create empty charts.
  dashboard_widgets = concat(
    length(local.lambda_invocation_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          title    = "Lambda invocations"
          region   = local.dashboard_region
          period   = 60
          stat     = "Sum"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.lambda_invocation_metrics
          legend = {
            position = "right"
          }
        }
      }
    ],
    length(local.lambda_error_and_throttle_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          title    = "Lambda errors and throttles"
          region   = local.dashboard_region
          period   = 60
          stat     = "Sum"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.lambda_error_and_throttle_metrics
          legend = {
            position = "right"
          }
        }
      }
    ],
    length(local.lambda_duration_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          title    = "Lambda duration p95"
          region   = local.dashboard_region
          period   = 60
          stat     = "p95"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.lambda_duration_metrics
          legend = {
            position = "right"
          }
        }
      }
    ],
    length(local.api_gateway_traffic_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          title    = "API Gateway traffic and errors"
          region   = local.dashboard_region
          period   = 60
          stat     = "Sum"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.api_gateway_traffic_metrics
          legend = {
            position = "right"
          }
        }
      }
    ],
    length(local.api_gateway_latency_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          title    = "API Gateway latency"
          region   = local.dashboard_region
          period   = 60
          stat     = "Average"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.api_gateway_latency_metrics
          legend = {
            position = "right"
          }
        }
      }
    ],
    length(local.sqs_visible_message_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6

        properties = {
          title    = "SQS visible messages"
          region   = local.dashboard_region
          period   = 60
          stat     = "Maximum"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.sqs_visible_message_metrics
          legend = {
            position = "right"
          }
        }
      }
    ],
    length(local.sqs_oldest_message_age_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6

        properties = {
          title    = "SQS oldest message age"
          region   = local.dashboard_region
          period   = 60
          stat     = "Maximum"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.sqs_oldest_message_age_metrics
          legend = {
            position = "right"
          }
        }
      }
    ],
    length(local.eventbridge_invocation_metrics) == 0 ? [] : [
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6

        properties = {
          title    = "EventBridge invocations"
          region   = local.dashboard_region
          period   = 60
          stat     = "Sum"
          view     = "timeSeries"
          stacked  = false
          liveData = false
          metrics  = local.eventbridge_invocation_metrics
          legend = {
            position = "right"
          }
        }
      }
    ]
  )

  dashboard_body = {
    start          = "-PT6H"
    periodOverride = "inherit"
    widgets        = local.dashboard_widgets
  }
}
