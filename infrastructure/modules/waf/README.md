# CloudFront Edge WAF Baseline

This module creates the reusable WAFv2 baseline for the serverless events
platform's future CloudFront edge layer.

It is intentionally platform-specific. The goal is not to provide a generic
WAF rules engine or a broad abstraction over every AWS WAF feature. Instead,
this module defines the concrete CloudFront-scoped Web ACL baseline that the
later edge-delivery layer will depend on.

This module is CloudFront-edge-WAF-only in v1.

---

## What This Module Creates

This module currently creates:

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

It also exposes the Web ACL identifiers later layers are most likely to need:

- the Web ACL ARN
- the Web ACL ID
- the Web ACL name

This keeps the first edge-protection implementation small, reviewable, and
aligned with the platform's locked edge-delivery direction.

---

## Why This Module Stays WAF-Focused

This step is focused on the reusable edge-protection baseline the platform
clearly needs before CloudFront wiring can be added cleanly:

- one CloudFront-scoped Web ACL
- one small fixed managed-rule baseline
- one optional simple rate-limit rule
- CloudWatch visibility configuration

The module does not create CloudFront distributions, Web ACL associations,
logging configuration, custom response bodies, IP sets, regex pattern sets,
scope-down statements, or a caller-defined arbitrary rules engine. Those
concerns may become relevant later, but they are intentionally outside the
scope of this first WAF baseline.

Keeping the module limited to the Web ACL baseline makes the design easier to
understand and avoids coupling this step too early to later CloudFront
composition details.

---

## CloudFront Scope Requirement

This module is intentionally locked to:

- `scope = "CLOUDFRONT"`

That is deliberate because the current platform edge direction is:

- CloudFront as the public browser-facing layer
- AWS WAF attached at the CloudFront edge

Important:

CloudFront-scoped WAFv2 resources must be managed through the AWS provider
configured for:

- `us-east-1`

So callers must pass an AWS provider configured for `us-east-1` into this
module.

The module itself does not declare a second provider alias internally because
provider selection belongs with the caller or environment root.

---

## Fixed Managed-Rule Baseline

This module intentionally uses a small fixed managed-rule baseline instead of a
fully caller-defined rules engine.

The current baseline includes:

- `AWSManagedRulesCommonRuleSet`
- `AWSManagedRulesKnownBadInputsRuleSet`
- `AWSManagedRulesAmazonIpReputationList`

That is intentional:

- it gives the edge layer an immediately useful production-shaped protection baseline
- it keeps the module small and reviewable
- it avoids widening the module interface before later edge validation proves more flexibility is actually needed

The managed rule groups use:

- `override_action { none {} }`

so AWS WAF applies the rule-group actions normally.

---

## Rate-Limit Direction

This module also supports one optional simple rate-limit rule.

The rate-limit rule is intentionally narrow:

- enabled or disabled with one boolean input
- configured with one request limit input
- aggregated by:
  - client IP

This first version does not support:

- scope-down statements
- multiple rate-limit rules
- path-specific rate limits
- arbitrary caller-defined statement trees

That keeps the first edge-protection step aligned with the project's current
goal: a small, practical baseline rather than a broad WAF authoring framework.

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
- callers should not need to manage separate metrics toggles for this first baseline

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

This keeps naming and tagging aligned with the environment root while leaving a
small amount of control over the optional rate-limit behavior.

---

## Outputs

The module exposes the Web ACL values later layers are most likely to need:

- `web_acl_arn`
- `web_acl_id`
- `web_acl_name`

These values are the practical identifiers later environment wiring and
CloudFront composition will need when the edge layer is attached.

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
