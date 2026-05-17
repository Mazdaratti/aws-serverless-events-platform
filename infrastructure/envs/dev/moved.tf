############################################
# Terraform state moves
############################################

# notification-planner is moving from the original API/business Lambda module
# call into the notification-worker Lambda module call. These moved blocks keep
# Terraform state attached to the existing AWS Lambda function and log group
# instead of planning a destroy/create under the new module address.
moved {
  from = module.lambda.aws_lambda_function.function["notification-planner"]
  to   = module.notification_lambdas.aws_lambda_function.function["notification-planner"]
}

moved {
  from = module.lambda.aws_cloudwatch_log_group.function["notification-planner"]
  to   = module.notification_lambdas.aws_cloudwatch_log_group.function["notification-planner"]
}
