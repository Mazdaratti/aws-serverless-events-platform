############################################
# Example provider and shared context
############################################

provider "aws" {
  # This example configures the AWS provider inline so a beginner can run it
  # without needing extra files beyond the minimal example set.
  #
  # The region should match the region configured in envs/dev.
  region = "eu-central-1"
}

locals {
  # The example keeps the same naming and tagging shape used elsewhere in the
  # repository so the API Gateway module can be validated in a realistic
  # context.
  project_name = "aws-serverless-events-platform"
  environment  = "example"
  name_prefix  = "${local.project_name}-${local.environment}"

  tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
  }

  # API Gateway access logs are easier to inspect when they are structured as
  # JSON. The stage writes this format into the caller-owned log group below.
  access_log_format = jsonencode({
    request_id = "$context.requestId"
    route_key  = "$context.routeKey"
    status     = "$context.status"
    source_ip  = "$context.identity.sourceIp"
  })
}

############################################
# Minimal supporting resources
############################################

# The example creates its own CloudWatch Logs log group so the enabled access
# logging path is truly runnable while the module still stays focused on stage
# configuration instead of log-group creation.
resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.name_prefix}-http-api-access"
  retention_in_days = 14

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-http-api-access"
  })
}

# The API Gateway module consumes existing Lambda function names and invoke
# ARNs. This example creates the smallest supporting IAM role and two Lambda
# functions needed to prove:
# - ordinary route integration
# - the optional Lambda request-authorizer path
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

resource "aws_iam_role" "example_lambda" {
  name               = "${local.name_prefix}-api-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-api-role"
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.example_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# The committed example ZIP keeps this example small and reviewable.
# source_code_hash ensures Terraform notices when the ZIP content changes.
resource "aws_lambda_function" "integration" {
  function_name    = "${local.name_prefix}-integration"
  role             = aws_iam_role.example_lambda.arn
  runtime          = "python3.13"
  handler          = "handler.lambda_handler"
  filename         = "${path.module}/files/example-lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/files/example-lambda.zip")

  depends_on = [aws_iam_role_policy_attachment.basic_execution]

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-integration"
  })
}

resource "aws_lambda_function" "request_authorizer" {
  function_name    = "${local.name_prefix}-request-authorizer"
  role             = aws_iam_role.example_lambda.arn
  runtime          = "python3.13"
  handler          = "handler.authorizer_handler"
  filename         = "${path.module}/files/example-lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/files/example-lambda.zip")

  depends_on = [aws_iam_role_policy_attachment.basic_execution]

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-request-authorizer"
  })
}

############################################
# API Gateway module basic usage
############################################

module "api_gateway" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  stage_name   = local.environment
  jwt_issuer   = "https://example.com"
  jwt_audience = ["example-audience"]

  # CORS is optional in the module. This example enables it so the example
  # proves the rendered HTTP API shape before frontend work begins.
  cors_configuration = {
    allow_origins     = ["https://app.example.com"]
    allow_methods     = ["GET", "POST", "PATCH", "OPTIONS"]
    allow_headers     = ["Authorization", "Content-Type"]
    expose_headers    = ["X-Request-Id"]
    allow_credentials = true
    max_age           = 300
  }

  access_log_enabled         = true
  access_log_destination_arn = aws_cloudwatch_log_group.api_access.arn
  access_log_format          = local.access_log_format

  default_throttling_burst_limit = 100
  default_throttling_rate_limit  = 50

  request_authorizers = {
    # This optional request-authorizer path demonstrates the reusable
    # CUSTOM-route contract without making Lambda authorizers mandatory for
    # every caller of the module.
    mixed-mode = {
      authorizer_uri                   = aws_lambda_function.request_authorizer.invoke_arn
      lambda_function_name             = aws_lambda_function.request_authorizer.function_name
      enable_simple_responses          = true
      authorizer_result_ttl_in_seconds = 0
    }
  }

  routes = {
    public-events = {
      route_key            = "GET /events"
      lambda_invoke_arn    = aws_lambda_function.integration.invoke_arn
      lambda_function_name = aws_lambda_function.integration.function_name
      authorization_type   = "NONE"
    }

    create-event = {
      route_key              = "POST /events"
      lambda_invoke_arn      = aws_lambda_function.integration.invoke_arn
      lambda_function_name   = aws_lambda_function.integration.function_name
      authorization_type     = "JWT"
      throttling_burst_limit = 20
      throttling_rate_limit  = 10
    }

    rsvp = {
      route_key              = "POST /events/{event_id}/rsvp"
      lambda_invoke_arn      = aws_lambda_function.integration.invoke_arn
      lambda_function_name   = aws_lambda_function.integration.function_name
      authorization_type     = "CUSTOM"
      authorizer_key         = "mixed-mode"
      throttling_burst_limit = 10
      throttling_rate_limit  = 5
    }
  }
}
