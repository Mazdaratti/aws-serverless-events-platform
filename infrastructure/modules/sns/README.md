# SNS Admin Notification Topic Baseline

This module creates the reusable SNS topic baseline for platform/admin
notifications in the serverless events platform.

It is intentionally platform-specific. The goal is not to provide a generic SNS
factory or broad notification abstraction. Instead, this module defines the
concrete SNS topic shape that later EventBridge routing, environment wiring,
and admin/dev email subscription configuration will compose around.

This module manages SNS topic and optional email subscription infrastructure
only.

---

## What This Module Creates

This module currently creates:

- one SNS topic
- zero or more email subscriptions for that topic

It also exposes the core outputs later platform layers need, including:

- topic name
- topic ARN
- topic ID
- email subscription ARNs

This keeps the first SNS implementation small, reviewable, and aligned with the
locked admin notification routing contract.

---

## Why This Module Stays SNS-Focused

This step is focused on the reusable SNS topic baseline the platform clearly
needs next:

- admin/platform broadcast topic creation
- optional email subscription resources
- stable topic identifiers for later EventBridge routing

The module does not create EventBridge rules, EventBridge targets, SNS topic
policies, SQS queues, Lambda publishing permissions, Lambda environment
variables, Lambda code, SES resources, or environment wiring. Those resources
either belong to their own modules or to the environment composition layer that
owns the concrete routing relationship.

Keeping this module limited to SNS resource logic makes the design easier to
understand while preserving thin `envs/dev` composition later.

---

## Admin Notification Direction

The platform's locked async notification direction uses SNS for simple
platform/admin broadcast notifications.

The intended admin path is:

`Write Lambda -> DynamoDB commit -> EventBridge -> SNS admin topic`

This module creates the SNS topic side of that path. It does not create
EventBridge routing or grant EventBridge permission to publish to the topic.
Those concerns depend on the concrete EventBridge rule ARN and are added in a
later wiring step.

---

## Email Subscriptions

Email subscriptions are optional and default to an empty set.

When email endpoints are supplied, SNS sends a confirmation message to each
recipient. A subscription does not receive messages until the recipient confirms
it.

Do not hardcode personal email addresses in reusable module code or examples.
Environment wiring can pass admin or developer email endpoints through
environment-specific configuration when that step is implemented.

---

## Topic Policy Boundary

This module intentionally does not create an SNS topic policy for EventBridge.

That policy should be scoped to the concrete EventBridge rule ARN that is
allowed to publish to the topic. The rule ARN is not known inside this standalone
SNS module baseline, so adding the policy here would either be too broad or
force unrelated routing inputs into the SNS module.

The later environment wiring should add a narrowly scoped topic policy when it
connects EventBridge routing to this topic.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to create the SNS topic without email subscriptions. That
keeps the example safe to plan and apply because it does not send subscription
confirmation emails.

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
