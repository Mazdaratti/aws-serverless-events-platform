# Observability Baseline

This module creates the reusable CloudWatch observability baseline for the
serverless events platform.

It is intentionally focused on native AWS service metrics. The goal is not to
create a full monitoring product or alert-routing layer. Instead, this module
defines the first high-signal alarms and a compact dashboard that environment
roots can compose around already deployed Lambda, API Gateway, SQS, and
EventBridge resources.

This module manages CloudWatch metric alarms and one optional CloudWatch
dashboard.

---

## What This Module Creates

This module currently creates CloudWatch metric alarms for:

- Lambda errors
- Lambda throttles
- API Gateway HTTP API 5xx responses
- SQS source queue visible messages
- SQS source queue oldest message age
- SQS dead-letter queue visible messages
- EventBridge failed invocations

It can also create one compact CloudWatch dashboard named:

- `<name_prefix>-observability`

The dashboard includes panels for:

- Lambda invocations, errors, throttles, and duration p95
- API Gateway request count, 4xx, 5xx, and latency
- SQS source queue depth, DLQ depth, and oldest message age
- EventBridge invocations and failed invocations

It also exposes the core outputs later platform layers need, including:

- alarm names
- alarm ARNs
- dashboard name
- dashboard ARN

This keeps the first observability implementation small, reviewable, and
aligned with the existing serverless architecture.

---

## Alarm Actions

Alarm actions are optional.

By default, this module creates alarms with no notification delivery:

- `alarm_actions = []`
- `ok_actions = []`

When both lists are empty, alarm actions are disabled. This lets an environment
create and inspect alarms before connecting SNS topics, incident routing, or
other alert delivery channels.

Alert routing belongs to environment composition or a later alerting module, not
to this first alarm baseline.

---

## Dashboard

Dashboard creation is optional and controlled by:

- `dashboard_enabled`

The dashboard is enabled by default. When enabled, the module requires at least
one dashboard-supported metric input so Terraform does not create an empty
dashboard.

The dashboard uses the active AWS provider region for its metric widgets. This
keeps the module interface small and avoids asking callers to pass a duplicate
dashboard-specific region.

Dashboard widgets are intentionally compact and grouped by platform layer. The
dashboard is for visual inspection and tuning; it does not replace alarms or
create alert delivery.

---

## Missing Data Strategy

The baseline uses:

- `treat_missing_data = "notBreaching"`
- one-minute metric periods
- two evaluation periods
- one datapoint to alarm

Most alarms in this module watch sparse failure or backlog metrics. For those
metrics, missing data usually means there was no failure signal in that period,
so treating missing data as not breaching avoids unnecessary
`INSUFFICIENT_DATA` noise.

The two-period evaluation window keeps the alarms responsive without using the
most twitchy possible one-period setup.

---

## Module Boundary

This module does not create:

- Lambda functions
- API Gateway APIs or stages
- SQS queues or DLQs
- EventBridge buses or rules
- SNS topics
- alert subscriptions
- CloudWatch log metric filters
- CloudFront or WAF alarms
- SES configuration sets
- budget or cost alarms
- OpenTelemetry, ADOT, or Powertools instrumentation

Those concerns belong to runtime modules, environment wiring, or later focused
observability slices.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example creates CloudWatch metric alarms and the optional dashboard. It
uses documentation-safe example metric dimensions instead of creating a full
Lambda/API/SQS/EventBridge stack, because this module owns observability
resources rather than runtime workloads.

The example can be planned and applied as-is, but the alarms and dashboard only
receive live metric data if matching workloads exist and emit the corresponding
AWS service metrics.

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
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.45.0 |



## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_dashboard.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_dashboard) | resource |
| [aws_cloudwatch_metric_alarm.metric](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_metric_alarm) | resource |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive CloudWatch alarm names. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and applied to taggable observability resources. | `map(string)` | n/a | yes |
| <a name="input_alarm_actions"></a> [alarm\_actions](#input\_alarm\_actions) | List of action ARNs to invoke when alarms enter ALARM state. Keep empty to create alarms without alert delivery. | `list(string)` | `[]` | no |
| <a name="input_api_gateway_5xx_threshold"></a> [api\_gateway\_5xx\_threshold](#input\_api\_gateway\_5xx\_threshold) | Number of API Gateway HTTP API 5xx responses in one period that causes the API alarm to enter ALARM state. | `number` | `1` | no |
| <a name="input_api_gateway_api_id"></a> [api\_gateway\_api\_id](#input\_api\_gateway\_api\_id) | Optional API Gateway HTTP API ID used for API-level CloudWatch alarms. | `string` | `null` | no |
| <a name="input_api_gateway_stage_name"></a> [api\_gateway\_stage\_name](#input\_api\_gateway\_stage\_name) | Optional API Gateway HTTP API stage name used with api\_gateway\_api\_id for stage-level CloudWatch alarms. | `string` | `null` | no |
| <a name="input_dashboard_enabled"></a> [dashboard\_enabled](#input\_dashboard\_enabled) | Whether to create the CloudWatch dashboard baseline. | `bool` | `true` | no |
| <a name="input_eventbridge_bus_name"></a> [eventbridge\_bus\_name](#input\_eventbridge\_bus\_name) | Optional custom EventBridge bus name used with eventbridge\_rule\_names for custom-bus rule alarms. | `string` | `null` | no |
| <a name="input_eventbridge_failed_invocations_threshold"></a> [eventbridge\_failed\_invocations\_threshold](#input\_eventbridge\_failed\_invocations\_threshold) | Number of EventBridge failed invocations in one period that causes a rule alarm to enter ALARM state. | `number` | `1` | no |
| <a name="input_eventbridge_rule_names"></a> [eventbridge\_rule\_names](#input\_eventbridge\_rule\_names) | Map of logical EventBridge rule key to deployed EventBridge rule name. | `map(string)` | `{}` | no |
| <a name="input_lambda_error_threshold"></a> [lambda\_error\_threshold](#input\_lambda\_error\_threshold) | Number of Lambda errors in one period that causes a Lambda error alarm to enter ALARM state. | `number` | `1` | no |
| <a name="input_lambda_functions"></a> [lambda\_functions](#input\_lambda\_functions) | Map of logical Lambda function key to deployed Lambda function name. | `map(string)` | `{}` | no |
| <a name="input_lambda_throttle_threshold"></a> [lambda\_throttle\_threshold](#input\_lambda\_throttle\_threshold) | Number of Lambda throttles in one period that causes a Lambda throttle alarm to enter ALARM state. | `number` | `1` | no |
| <a name="input_ok_actions"></a> [ok\_actions](#input\_ok\_actions) | List of action ARNs to invoke when alarms return to OK state. Keep empty to create alarms without OK notifications. | `list(string)` | `[]` | no |
| <a name="input_sqs_dlq_names"></a> [sqs\_dlq\_names](#input\_sqs\_dlq\_names) | Map of logical dead-letter queue key to deployed SQS DLQ name. | `map(string)` | `{}` | no |
| <a name="input_sqs_dlq_visible_messages_threshold"></a> [sqs\_dlq\_visible\_messages\_threshold](#input\_sqs\_dlq\_visible\_messages\_threshold) | Approximate number of visible DLQ messages that causes the SQS DLQ alarm to enter ALARM state. | `number` | `1` | no |
| <a name="input_sqs_oldest_message_age_seconds_threshold"></a> [sqs\_oldest\_message\_age\_seconds\_threshold](#input\_sqs\_oldest\_message\_age\_seconds\_threshold) | Approximate source-queue oldest message age in seconds that causes the SQS age alarm to enter ALARM state. | `number` | `300` | no |
| <a name="input_sqs_queue_names"></a> [sqs\_queue\_names](#input\_sqs\_queue\_names) | Map of logical source queue key to deployed SQS queue name. | `map(string)` | `{}` | no |
| <a name="input_sqs_visible_messages_threshold"></a> [sqs\_visible\_messages\_threshold](#input\_sqs\_visible\_messages\_threshold) | Approximate number of visible source-queue messages that causes the SQS depth alarm to enter ALARM state. | `number` | `10` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_alarm_arns"></a> [alarm\_arns](#output\_alarm\_arns) | Map of logical alarm key to CloudWatch alarm ARN. |
| <a name="output_alarm_names"></a> [alarm\_names](#output\_alarm\_names) | Map of logical alarm key to CloudWatch alarm name. |
| <a name="output_dashboard_arn"></a> [dashboard\_arn](#output\_dashboard\_arn) | ARN of the CloudWatch dashboard created by the module, or null when dashboard creation is disabled. |
| <a name="output_dashboard_name"></a> [dashboard\_name](#output\_dashboard\_name) | Name of the CloudWatch dashboard created by the module, or null when dashboard creation is disabled. |
<!-- END_TF_DOCS -->
