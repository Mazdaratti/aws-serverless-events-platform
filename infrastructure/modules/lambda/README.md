# Lambda Compute Module

This module creates ZIP-based Lambda functions and their CloudWatch Logs log
groups for the serverless events platform.

It is intentionally infrastructure-focused rather than a build system or
general-purpose Lambda factory. Callers provide prepared ZIP artifacts,
execution-role ARNs, runtime configuration, and environment variables.

Each environment root defines its concrete workloads and composes the resulting
functions with API Gateway, SQS, EventBridge, IAM, and other platform services.
Packaging and code deployment are documented in
[`lambdas/README.md`](../../../lambdas/README.md).

---

## What This Module Creates

This module creates one or more ZIP-based Lambda functions from a
workload-keyed `functions` map.

For each logical function definition, it creates:

- one Lambda function
- one explicitly managed CloudWatch Logs log group

It also applies:

- optional X-Ray tracing mode
- the supplied execution role ARN
- runtime and handler settings
- memory and timeout settings
- environment variables
- explicit CloudWatch Logs retention

Function names and log-group names are derived from the caller's shared name
prefix and logical workload keys.

---

## Module Boundary

The module owns:

- Lambda function resources and names
- runtime, handler, memory, timeout, and tracing configuration
- execution-role references
- environment variables
- explicitly managed log groups and retention
- function and log-group outputs

It does not own:

- execution roles or workload IAM policies
- ZIP artifact generation
- code-only deployments after function creation
- API Gateway integrations or Lambda permissions
- SQS event source mappings
- EventBridge rules, targets, or resource policies
- Lambda layers, versions, aliases, or CodeDeploy resources

Those responsibilities belong to callers, packaging and deployment tooling, or
the modules that own the corresponding integrations.

---

## Package Input

This module consumes a ready ZIP artifact through `package_path`.

The package is required because AWS Lambda function creation requires code.
Terraform calculates the initial `source_code_hash` from that artifact.

Packaging remains outside the module so the same artifact-generation path can
be used by provisioning and code-deployment automation.

The runnable example uses `archive_file` only to create its example ZIP outside
the module.

---

## Why Log Groups Are Managed Explicitly

This module creates CloudWatch Logs log groups explicitly instead of relying on implicit creation during first invocation.

That is intentional:

- retention stays under Terraform control
- log group ownership is clearer in AWS
- validation does not depend on first invocation
- callers can apply consistent retention settings

---

## Why Tracing Mode Is Explicit

This module exposes Lambda X-Ray tracing through a per-function `tracing_mode`
setting.

The default is `PassThrough` so existing callers keep the lowest-cost behavior
unless an environment explicitly opts into active tracing. Environments that
enable `Active` tracing must also ensure the function execution role can write
trace segments and telemetry records to X-Ray.

---

## Function Definition

Each function definition supports:

- `description`
- `role_arn`
- `runtime`
- `handler`
- `package_path`
- `memory_size`
- `timeout`
- `environment_variables`
- `log_retention_in_days`
- `tracing_mode`

Logical function keys must be lowercase and hyphenated because they become part
of function names, log-group names, and output-map keys.

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
- enable active tracing on the example function
- inspect the resulting function and log group outputs

Applying the example creates real IAM, Lambda, and CloudWatch Logs resources
and should be reviewed before use in an AWS account.

---

## Lambda Code Ownership Boundary

Terraform still needs the package path and source-code hash for initial Lambda
function creation. Fresh provisioning must build the expected ZIP artifacts
before Terraform plan/apply.

After creation, Terraform ignores drift for the package-only fields:

- `filename`
- `source_code_hash`

This keeps Terraform responsible for Lambda infrastructure and configuration
while allowing deployment automation to update existing function code with
`aws lambda update-function-code`.

Terraform continues to detect changes to runtime, handler, role, memory,
timeout, tracing, environment variables, tags, and log-group configuration.

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
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.37 |



## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_lambda_function.function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_functions"></a> [functions](#input\_functions) | Map of Lambda function definitions keyed by logical workload name.<br/><br/>The module remains infrastructure-focused:<br/>- package\_path points to a ready ZIP artifact<br/>- IAM roles are consumed through role\_arn<br/>- environment variables are passed through as simple key/value pairs | <pre>map(object({<br/>    description           = string<br/>    role_arn              = string<br/>    runtime               = string<br/>    handler               = string<br/>    package_path          = string<br/>    memory_size           = optional(number)<br/>    timeout               = optional(number)<br/>    environment_variables = optional(map(string))<br/>    log_retention_in_days = optional(number)<br/>    tracing_mode          = optional(string, "PassThrough")<br/>  }))</pre> | n/a | yes |
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
