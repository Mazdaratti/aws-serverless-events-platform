############################################
# CloudFront-scoped Web ACL
############################################

resource "aws_wafv2_web_acl" "this" {
  # This Web ACL is scoped for association with a CloudFront distribution at
  # the public edge entry point.
  #
  # Important:
  # CloudFront-scoped WAFv2 resources must be managed through the AWS provider
  # configured for us-east-1. The caller is responsible for passing that
  # provider configuration into this module.
  name  = local.web_acl_name
  scope = "CLOUDFRONT"

  # The default action allows requests that are not blocked by managed-rule or
  # rate-limit protections.
  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = local.managed_rules

    content {
      name     = rule.value.name
      priority = rule.value.priority

      override_action {
        none {}
      }

      statement {
        managed_rule_group_statement {
          name        = rule.value.name
          vendor_name = rule.value.vendor_name
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = local.managed_rule_metric_names[rule.value.name]
        sampled_requests_enabled   = true
      }
    }
  }

  dynamic "rule" {
    for_each = var.rate_limit_enabled ? [1] : []

    content {
      name     = local.rate_limit_rule_name
      priority = 100

      action {
        block {}
      }

      statement {
        rate_based_statement {
          aggregate_key_type = "IP"
          limit              = var.rate_limit
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = local.rate_limit_metric_name
        sampled_requests_enabled   = true
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = local.web_acl_metric_name
    sampled_requests_enabled   = true
  }

  tags = local.web_acl_tags
}
