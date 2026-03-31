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
  # repository so the Lambda module can be validated in a realistic context.
  project_name = "aws-serverless-events-platform"
  environment  = "example"
  name_prefix  = "${local.project_name}-${local.environment}"

  tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
  }
}

############################################
# Example package built outside the module
############################################

# The module contract expects a ready ZIP artifact. This example creates that
# ZIP locally so the example remains runnable while the module stays focused on
# infrastructure instead of packaging orchestration.
data "archive_file" "create_event_package" {
  type        = "zip"
  output_path = "${path.module}/artifacts/create-event.zip"

  source {
    content  = <<-PYTHON
      def lambda_handler(event, context):
          return {
              "message": "example lambda package",
              "received_event": event,
          }
    PYTHON
    filename = "handler.py"
  }
}

############################################
# Minimal supporting resources
############################################

# The Lambda module consumes an existing execution role ARN. This example uses
# a tiny local IAM role and attachment only so the module contract can be
# validated end to end in a runnable example root.
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
  name               = "${local.name_prefix}-create-event-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-create-event-role"
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.example_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

############################################
# Lambda module basic usage
############################################

module "lambda" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  functions = {
    create-event = {
      description  = "Example create-event Lambda used to validate the module contract."
      role_arn     = aws_iam_role.example_lambda.arn
      runtime      = "python3.13"
      handler      = "handler.lambda_handler"
      package_path = data.archive_file.create_event_package.output_path
      memory_size  = 256
      timeout      = 10
      environment_variables = {
        EVENTS_TABLE_NAME = "${local.name_prefix}-events"
      }
      log_retention_in_days = 14
    }
  }
}
