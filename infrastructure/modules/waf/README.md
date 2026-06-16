# CloudFront WAF Module

This module creates a CloudFront-scoped AWS WAFv2 Web ACL for the serverless
events platform.

It is intentionally platform-specific rather than a generic WAF rule engine.
The module owns a fixed managed-rule set, optional IP-based rate limiting, and
visibility configuration.

Each environment root decides whether to create the Web ACL and passes its ARN
to the edge-delivery layer. The platform-wide edge security model is documented
in the [architecture guide](../../../docs/architecture.md).

---

## What This Module Creates

This module creates:

- one WAFv2 Web ACL

That Web ACL is configured with:

- CloudFront scope
- default allow behavior
- a fixed AWS managed-rule baseline
- an optional simple IP-based rate-limit rule
- CloudWatch visibility configuration for:
  - the Web ACL
  - each managed rule
  - the optional rate-limit rule

It exposes:

- the Web ACL ARN
- the Web ACL ID
- the Web ACL name

The caller controls shared naming, tags, the Web ACL name suffix, and optional
rate-limit behavior.

---

## Module Boundary

The module owns:

- CloudFront-scoped Web ACL creation
- the fixed AWS managed-rule groups
- one optional IP-based rate-limit rule
- CloudWatch metrics and sampled-request settings
- Web ACL naming, tags, and outputs

It does not own:

- CloudFront distributions
- Web ACL association with a concrete distribution
- WAF logging destinations
- custom response bodies
- IP sets or regex pattern sets
- scope-down statements
- arbitrary caller-defined rules

Those responsibilities belong to callers or require an explicit module-contract
change.

---

## CloudFront Scope Requirement

This module is intentionally locked to:

- `scope = "CLOUDFRONT"`

That is deliberate because this module protects:

- a global CloudFront distribution
- browser and API traffic entering through that distribution

Important:

CloudFront-scoped WAFv2 resources must be managed through the AWS provider
configured for:

- `us-east-1`

Callers must therefore pass an AWS provider configured for `us-east-1` into
this module.

The module itself does not declare a second provider alias internally because
provider selection belongs with the caller or environment root.

---

## Fixed Managed Rules

This module intentionally uses a small fixed managed-rule baseline instead of a
fully caller-defined rules engine.

The fixed set includes:

- `AWSManagedRulesCommonRuleSet`
- `AWSManagedRulesKnownBadInputsRuleSet`
- `AWSManagedRulesAmazonIpReputationList`

That is intentional:

- it provides a reviewable baseline against common and known-bad requests
- it keeps the module small and reviewable
- it prevents callers from injecting arbitrary rule trees

The managed rule groups use:

- `override_action { none {} }`

so AWS WAF applies the rule-group actions normally.

---

## Optional Rate Limit

This module also supports one optional simple rate-limit rule.

The rate-limit rule is intentionally narrow:

- enabled or disabled with one boolean input
- configured with one request limit input
- aggregated by:
  - client IP

The module does not support:

- scope-down statements
- multiple rate-limit rules
- path-specific rate limits
- arbitrary caller-defined statement trees

This keeps rate limiting predictable rather than turning the module into a
broad WAF authoring framework.

---

## Visibility Defaults

Visibility configuration is enabled by default at every level created by the
module:

- the Web ACL
- each managed rule
- the optional rate-limit rule

That is intentional:

- metrics should be available immediately for operational visibility
- sampled requests should be available immediately for debugging and review
- callers do not need to manage separate visibility toggles

Metric names are rendered internally from normalized names so the caller does
not need to supply additional metrics inputs.

---

## Inputs

This module keeps its public input surface intentionally small:

- `name_prefix`
- `tags`
- `web_acl_name_suffix`
- `rate_limit_enabled`
- `rate_limit`

This keeps naming and tagging aligned with the composing root while preserving
explicit caller control over rate limiting.

---

## Outputs

The module exposes:

- `web_acl_arn`
- `web_acl_id`
- `web_acl_name`

Callers can use the ARN to associate the Web ACL with a CloudFront distribution
without requiring this module to own that distribution.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- define a small naming baseline
- define the baseline tag map
- configure an AWS provider alias for:
  - `us-east-1`
- pass that provider explicitly into the module
- enable the simple IP-based rate-limit rule

The example intentionally does not create:

- CloudFront distributions
- Web ACL associations
- Route 53 records
- ACM certificates
- frontend hosting resources

Applying the example creates a real global WAFv2 Web ACL in `us-east-1` and
should be reviewed before use in an AWS account.

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.42.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_wafv2_web_acl.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_web_acl) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive the CloudFront-scoped Web ACL name. | `string` | n/a | yes |
| <a name="input_rate_limit"></a> [rate\_limit](#input\_rate\_limit) | Request limit for the fixed IP-based rate-limit rule when rate limiting is enabled. | `number` | `2000` | no |
| <a name="input_rate_limit_enabled"></a> [rate\_limit\_enabled](#input\_rate\_limit\_enabled) | Whether the fixed IP-based rate-limit rule is enabled in the CloudFront-scoped Web ACL. | `bool` | `true` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_web_acl_name_suffix"></a> [web\_acl\_name\_suffix](#input\_web\_acl\_name\_suffix) | Suffix appended to name\_prefix when rendering the CloudFront-scoped Web ACL name. | `string` | `"edge"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_web_acl_arn"></a> [web\_acl\_arn](#output\_web\_acl\_arn) | ARN of the CloudFront-scoped Web ACL. |
| <a name="output_web_acl_id"></a> [web\_acl\_id](#output\_web\_acl\_id) | ID of the CloudFront-scoped Web ACL. |
| <a name="output_web_acl_name"></a> [web\_acl\_name](#output\_web\_acl\_name) | Name of the CloudFront-scoped Web ACL. |
<!-- END_TF_DOCS -->
