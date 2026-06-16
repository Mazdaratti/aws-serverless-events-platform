# SNS Admin Notification Module

This module creates an SNS topic for platform and administrative
notifications in the serverless events platform.

It is intentionally platform-specific rather than a generic SNS factory. The
module owns one broadcast topic and optional email subscription resources.

Each environment root defines its concrete topic configuration, subscribers,
publishers, and resource policies. The platform-wide notification model is
documented in the [architecture guide](../../../docs/architecture.md).

---

## What This Module Creates

This module creates:

- one SNS topic
- zero or more email subscriptions for that topic

It exposes:

- topic name
- topic ARN
- topic ID
- email subscription ARNs

The caller supplies shared naming, tags, an optional explicit topic name, and
the set of email endpoints.

---

## Module Boundary

The module owns:

- SNS topic creation and tagging
- optional email subscription resources
- topic and subscription outputs

It does not own:

- EventBridge rules or targets
- SNS topic policies
- SQS queues or subscriptions
- Lambda IAM permissions or environment variables
- message formatting or publisher behavior
- SES participant-email resources
- CloudWatch alarms and dashboards

Those responsibilities belong to callers, workload code, IAM, SES, or
observability.

---

## Notification Contract

The topic provides a broadcast surface for platform and administrative
notifications.

Callers determine:

- which services may publish
- which EventBridge rules or workloads act as publishers
- which email endpoints are subscribed
- how messages are formatted
- which topic policy grants publishing access

The module creates the topic and optional subscriptions without coupling them
to a particular publisher or routing topology.

---

## Email Subscriptions

Email subscriptions are optional and default to an empty set.

When email endpoints are supplied, SNS sends a confirmation message to each
recipient. A subscription does not receive messages until the recipient confirms
it.

Do not hardcode personal email addresses in reusable module code or examples.
Callers should pass email endpoints through environment-specific, uncommitted
configuration.

---

## Topic Policy Boundary

This module intentionally does not create a topic policy.

Publishing access should be scoped to the concrete source resource and AWS
account where supported. Those values are not known inside this standalone
module.

The target owner or composing root should create the narrowly scoped topic
policy when connecting a publisher to the topic.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to create the SNS topic without email subscriptions. That
avoids sending subscription confirmation emails.

Applying the example creates a real SNS topic and should be reviewed before use
in an AWS account.

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
| [aws_sns_topic.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic) | resource |
| [aws_sns_topic_subscription.email](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_subscription) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive SNS resource names. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_email_subscriptions"></a> [email\_subscriptions](#input\_email\_subscriptions) | Email endpoints to subscribe to the SNS topic. Email subscriptions require confirmation before receiving messages. | `set(string)` | `[]` | no |
| <a name="input_topic_name"></a> [topic\_name](#input\_topic\_name) | Optional explicit SNS topic name. When null, the module derives the name from name\_prefix. | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_email_subscription_arns"></a> [email\_subscription\_arns](#output\_email\_subscription\_arns) | Map of email endpoint to SNS email subscription ARN. |
| <a name="output_topic_arn"></a> [topic\_arn](#output\_topic\_arn) | ARN of the SNS topic. |
| <a name="output_topic_id"></a> [topic\_id](#output\_topic\_id) | ID of the SNS topic. |
| <a name="output_topic_name"></a> [topic\_name](#output\_topic\_name) | Name of the SNS topic. |
<!-- END_TF_DOCS -->
