############################################
# Lambda event source mappings
############################################

# The notification planner consumes event-level participant notification work
# from notification-dispatch and emits recipient-level jobs to
# notification-email. Partial batch responses keep successfully planned SQS
# records from being retried when another record in the same batch fails.
resource "aws_lambda_event_source_mapping" "notification_planner_dispatch" {
  event_source_arn = module.sqs.queue_arns["notification-dispatch"]
  function_name    = module.lambda.function_names["notification-planner"]

  batch_size                         = 10
  maximum_batching_window_in_seconds = 0
  function_response_types            = ["ReportBatchItemFailures"]

  depends_on = [module.iam]
}
