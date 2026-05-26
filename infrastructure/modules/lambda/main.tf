############################################
# CloudWatch log groups
############################################

# Own Lambda log groups explicitly so retention and naming stay under
# Terraform control instead of being created implicitly on first invocation.
resource "aws_cloudwatch_log_group" "function" {
  for_each = local.resolved_functions

  name              = each.value.log_group_name
  retention_in_days = each.value.log_retention_in_days

  tags = merge(var.tags, {
    Name = each.value.log_group_name
  })
}

############################################
# Lambda functions
############################################

# This module deploys Lambda infrastructure only. IAM ownership stays outside
# the module, so each function consumes an existing execution role ARN.
resource "aws_lambda_function" "function" {
  for_each = local.resolved_functions

  function_name = each.value.function_name
  description   = each.value.description
  role          = each.value.role_arn
  runtime       = each.value.runtime
  handler       = each.value.handler

  filename         = each.value.package_path
  source_code_hash = each.value.source_code_hash

  memory_size = each.value.memory_size
  timeout     = each.value.timeout

  dynamic "environment" {
    for_each = length(each.value.environment_variables) > 0 ? [1] : []

    content {
      variables = each.value.environment_variables
    }
  }

  # Keep tracing explicit per function. The module defaults to PassThrough so
  # existing callers do not start emitting X-Ray traces unless they opt in.
  tracing_config {
    mode = each.value.tracing_mode
  }

  tags = merge(var.tags, {
    Name = each.value.function_name
  })

  # Terraform needs the package fields for initial function creation, but
  # Lambda code updates are owned by deployment automation after creation.
  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
    ]
  }

  depends_on = [aws_cloudwatch_log_group.function]
}
