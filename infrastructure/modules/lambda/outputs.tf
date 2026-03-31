############################################
# Lambda function outputs
############################################

output "function_names" {
  description = "Map of logical function key to rendered Lambda function name."
  value = {
    for function_key, function in aws_lambda_function.function :
    function_key => function.function_name
  }
}

output "function_arns" {
  description = "Map of logical function key to rendered Lambda function ARN."
  value = {
    for function_key, function in aws_lambda_function.function :
    function_key => function.arn
  }
}

output "invoke_arns" {
  description = "Map of logical function key to rendered Lambda invoke ARN."
  value = {
    for function_key, function in aws_lambda_function.function :
    function_key => function.invoke_arn
  }
}

############################################
# CloudWatch Logs outputs
############################################

output "log_group_names" {
  description = "Map of logical function key to CloudWatch Logs log group name owned by the module."
  value = {
    for function_key, log_group in aws_cloudwatch_log_group.function :
    function_key => log_group.name
  }
}

output "log_group_arns" {
  description = "Map of logical function key to CloudWatch Logs log group ARN owned by the module."
  value = {
    for function_key, log_group in aws_cloudwatch_log_group.function :
    function_key => log_group.arn
  }
}
