############################################
# Normalized Web ACL configuration
############################################

locals {
  # Keep the rendered Web ACL identity in one place so naming stays consistent
  # between the resource itself, tags, and the internally rendered metric names.
  web_acl_name = "${var.name_prefix}-${var.web_acl_name_suffix}"

  # Extend the caller-supplied baseline tags with the rendered Name tag used by
  # this CloudFront-scoped Web ACL.
  web_acl_tags = merge(var.tags, {
    Name = local.web_acl_name
  })

  # WAF visibility config requires metric names at the Web ACL and rule level.
  # Render them internally so callers do not need to manage separate metrics
  # naming concerns for this fixed baseline module.
  web_acl_metric_name = replace(local.web_acl_name, "-", "_")

  # Keep the fixed managed-rule baseline centralized here so main.tf can focus
  # on the Web ACL structure rather than repeating rule metadata inline.
  managed_rules = [
    {
      name        = "AWSManagedRulesCommonRuleSet"
      priority    = 10
      vendor_name = "AWS"
    },
    {
      name        = "AWSManagedRulesKnownBadInputsRuleSet"
      priority    = 20
      vendor_name = "AWS"
    },
    {
      name        = "AWSManagedRulesAmazonIpReputationList"
      priority    = 30
      vendor_name = "AWS"
    },
  ]

  managed_rule_metric_names = {
    for rule in local.managed_rules :
    rule.name => "${local.web_acl_metric_name}_${replace(rule.name, "-", "_")}"
  }

  rate_limit_rule_name   = "${local.web_acl_name}-rate-limit"
  rate_limit_metric_name = "${local.web_acl_metric_name}_rate_limit"
}
