# Lambda Compute Baseline

This module creates the initial Lambda compute baseline for the serverless events platform.

It is intentionally platform-specific. The goal is not to provide a generic build system or an over-abstracted Lambda factory. Instead, this module defines the concrete Lambda infrastructure baseline that later environment and API wiring will depend on.

This module is infrastructure-focused in v1.

---

## What This Module Creates

This module currently creates one or more ZIP-packaged Lambda functions from a workload-keyed `functions` map.

For each logical function definition, it creates:

- one Lambda function
- one explicitly managed CloudWatch Logs log group

It also applies:

- the supplied execution role ARN
- runtime and handler settings
- memory and timeout settings
- environment variables
- explicit CloudWatch Logs retention

This keeps the first Lambda implementation small, reviewable, and aligned with the current rollout order.

---

## Why This Module Stays Infrastructure-Focused

This step is focused on the reusable Lambda infrastructure that the platform needs first:

- Lambda function deployment
- existing IAM role attachment
- package-path based ZIP deployment
- explicit log group ownership

The module does not create IAM roles, build ZIP packages, configure API Gateway integrations, add SQS event source mappings, manage EventBridge permissions, or introduce Lambda layers. Those concerns may become relevant later, but they are intentionally outside the scope of this first Lambda layer.

Keeping the module limited to Lambda infrastructure makes the design easier to understand and preserves the current ownership boundaries:

- IAM stays in `modules/iam`
- packaging stays outside the module
- `envs/dev` stays thin and composition-focused

---

## Why The Module Consumes `package_path`

This module consumes a ready ZIP artifact through `package_path`.

That is intentional:

- Terraform should deploy Lambda artifacts here, not become the long-term build system
- the module stays usable whether packaging is done locally now or in CI/CD later
- the interface remains stable even if the packaging workflow evolves

The runnable example uses `archive_file` only as a small local convenience to create a ZIP outside the module. That is an example-level choice, not the module's design direction.

---

## Why Log Groups Are Managed Explicitly

This module creates CloudWatch Logs log groups explicitly instead of relying on implicit creation during first invocation.

That is intentional:

- retention stays under Terraform control
- log group ownership is clearer in AWS
- later validation is easier
- the deployed shape is more production-like

---

## Current V1 Deployment Shape

Each function definition currently supports:

- `description`
- `role_arn`
- `runtime`
- `handler`
- `package_path`
- `memory_size`
- `timeout`
- `environment_variables`
- `log_retention_in_days`

This keeps the module reusable for future workloads such as:

- `create-event`
- `list-events`
- `rsvp`
- `notification-worker`

without turning the module into a speculative catch-all abstraction.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- build the shared `name_prefix`
- define the baseline tag map
- prepare a small ZIP artifact outside the module
- provide an existing Lambda execution role ARN
- call the module with one function definition
- inspect the resulting function and log group outputs

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
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.38.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_lambda_function.function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_functions"></a> [functions](#input\_functions) | Map of Lambda function definitions keyed by logical workload name.<br/><br/>The module stays infrastructure-focused in v1:<br/>- package\_path points to a ready ZIP artifact<br/>- IAM roles are consumed through role\_arn<br/>- environment variables are passed through as simple key/value pairs | <pre>map(object({<br/>    description           = string<br/>    role_arn              = string<br/>    runtime               = string<br/>    handler               = string<br/>    package_path          = string<br/>    memory_size           = optional(number)<br/>    timeout               = optional(number)<br/>    environment_variables = optional(map(string))<br/>    log_retention_in_days = optional(number)<br/>  }))</pre> | n/a | yes |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive Lambda function and log group names. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_function_arns"></a> [function\_arns](#output\_function\_arns) | Map of logical function key to rendered Lambda function ARN. |
| <a name="output_function_names"></a> [function\_names](#output\_function\_names) | Map of logical function key to rendered Lambda function name. |
| <a name="output_invoke_arns"></a> [invoke\_arns](#output\_invoke\_arns) | Map of logical function key to rendered Lambda invoke ARN. |
| <a name="output_log_group_arns"></a> [log\_group\_arns](#output\_log\_group\_arns) | Map of logical function key to CloudWatch Logs log group ARN owned by the module. |
| <a name="output_log_group_names"></a> [log\_group\_names](#output\_log\_group\_names) | Map of logical function key to CloudWatch Logs log group name owned by the module. |
<!-- END_TF_DOCS -->
