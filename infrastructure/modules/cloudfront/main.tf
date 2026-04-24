############################################
# Managed CloudFront policies
############################################

data "aws_cloudfront_cache_policy" "static" {
  # Use AWS's managed static-content cache baseline instead of creating a
  # custom cache policy before the platform has real frontend traffic patterns.
  name = local.static_cache_policy_name
}

data "aws_cloudfront_cache_policy" "api" {
  # API requests must not be cached in this first edge baseline because the
  # backend contains authenticated reads and mutating routes.
  name = local.api_cache_policy_name
}

data "aws_cloudfront_origin_request_policy" "api" {
  # Forward viewer request details needed by API Gateway, including
  # Authorization, while letting CloudFront send the correct origin Host header.
  name = local.api_origin_request_policy_name
}

############################################
# S3 origin access control
############################################

resource "aws_cloudfront_origin_access_control" "s3" {
  # OAC is the modern replacement for legacy Origin Access Identity. It lets
  # CloudFront sign requests to the private S3 frontend bucket using SigV4.
  name                              = local.s3_origin_access_control_name
  description                       = "Allow CloudFront to read the private frontend S3 origin."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

############################################
# Edge distribution baseline
############################################

resource "aws_cloudfront_distribution" "this" {
  # This distribution is the future public entry point for both static frontend
  # files and the existing routed backend API. The module intentionally does
  # not create DNS records, ACM certificates, or S3 bucket policies.
  enabled             = var.enabled
  comment             = local.distribution_name
  default_root_object = var.default_root_object
  price_class         = var.price_class
  is_ipv6_enabled     = true
  web_acl_id          = var.web_acl_arn

  origin {
    domain_name                 = local.s3_origin_domain_name
    origin_id                   = local.s3_origin_id
    origin_access_control_id    = aws_cloudfront_origin_access_control.s3.id
    connection_attempts         = 3
    connection_timeout          = 10
    response_completion_timeout = 0
  }

  origin {
    domain_name                 = local.api_origin_domain_name
    origin_id                   = local.api_origin_id
    origin_path                 = local.api_origin_path
    connection_attempts         = 3
    connection_timeout          = 10
    response_completion_timeout = 0

    # API Gateway is modeled as a custom HTTPS origin. The stage path, such as
    # /dev, is supplied through origin_path by the environment root later.
    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_keepalive_timeout = 5
      origin_protocol_policy   = "https-only"
      origin_read_timeout      = 30
      origin_ssl_protocols     = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]

    cache_policy_id = data.aws_cloudfront_cache_policy.static.id
    compress        = true
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.api_path_patterns

    content {
      path_pattern           = ordered_cache_behavior.value
      target_origin_id       = local.api_origin_id
      viewer_protocol_policy = "redirect-to-https"

      allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods  = ["GET", "HEAD"]

      cache_policy_id          = data.aws_cloudfront_cache_policy.api.id
      origin_request_policy_id = data.aws_cloudfront_origin_request_policy.api.id
      compress                 = true
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    # Custom domains and ACM certificates are intentionally deferred. The first
    # module baseline uses the default CloudFront domain and certificate.
    cloudfront_default_certificate = true
  }

  tags = local.distribution_tags
}
