############################################
# Example provider and shared context
############################################

provider "aws" {
  # CloudFront is a global service, but this example still creates its
  # supporting S3 bucket and HTTP API in one concrete AWS region.
  region = "eu-central-1"
}

data "aws_caller_identity" "current" {}

locals {
  # Keep the example self-contained by defining a small naming and tagging
  # baseline here instead of depending on any environment root.
  name_prefix = "example-events-platform"

  tags = {
    Project     = "aws-serverless-events-platform"
    Environment = "example"
    ManagedBy   = "Terraform"
  }

  # S3 bucket names are globally unique. Including the account ID makes this
  # example easier to apply in a real account without colliding with others.
  frontend_bucket_name = "${local.name_prefix}-cf-example-${data.aws_caller_identity.current.account_id}"
}

############################################
# Minimal private S3 frontend origin
############################################

resource "aws_s3_bucket" "frontend" {
  # This example creates its own private bucket instead of depending on another
  # local module, so the CloudFront module example remains self-contained.
  bucket        = local.frontend_bucket_name
  force_destroy = true

  tags = merge(local.tags, {
    Name = local.frontend_bucket_name
  })
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  depends_on = [aws_s3_bucket_public_access_block.frontend]

  bucket = aws_s3_bucket.frontend.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

############################################
# Minimal API Gateway origin
############################################

resource "aws_apigatewayv2_api" "example" {
  # The CloudFront module only needs the API Gateway origin domain and stage
  # path. A tiny HTTP API is enough to make those values real for planning.
  name          = "${local.name_prefix}-cloudfront-example-http-api"
  protocol_type = "HTTP"

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-cloudfront-example-http-api"
  })
}

resource "aws_apigatewayv2_stage" "example" {
  api_id      = aws_apigatewayv2_api.example.id
  name        = "example"
  auto_deploy = true

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-cloudfront-example-stage"
  })
}

############################################
# CloudFront module basic usage
############################################

module "cloudfront" {
  source = "../../"

  # This example demonstrates the first edge distribution baseline:
  # - private S3 frontend origin as the default behavior
  # - API Gateway as the /events backend origin
  # - HTTPS redirect at the edge
  # - managed cache policies for static and API behavior
  name_prefix = local.name_prefix
  tags        = local.tags

  s3_origin_bucket_regional_domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name

  api_origin_domain_name = replace(aws_apigatewayv2_api.example.api_endpoint, "https://", "")
  api_origin_path        = "/${aws_apigatewayv2_stage.example.name}"

  price_class         = "PriceClass_100"
  enabled             = true
  default_root_object = "index.html"

  # WAF association is supported by the module, but this basic example omits it
  # so the example can focus on CloudFront origin and behavior wiring.
  web_acl_arn = null
}

############################################
# Caller-owned S3 origin policy
############################################

data "aws_iam_policy_document" "allow_cloudfront_read" {
  statement {
    sid    = "AllowCloudFrontRead"
    effect = "Allow"

    actions = ["s3:GetObject"]

    resources = [
      "${aws_s3_bucket.frontend.arn}/*",
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
  # OAC signs CloudFront requests, but the bucket still needs a caller-owned
  # policy that trusts only this distribution ARN. Keeping the policy outside
  # the module avoids coupling the CloudFront module to a specific bucket owner.
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.allow_cloudfront_read.json
}
