# EventBridge Routing Module

This module creates the custom EventBridge bus, rules, and targets used to route
platform domain events.

It owns EventBridge routing resources only. Target resources, resource
policies, event publishers, and consumers remain outside the module.

The deployed event topology is documented in the
[`dev` environment guide](../../envs/dev/README.md) and
[architecture guide](../../../docs/architecture.md).

---

## What This Module Creates

This module creates:

- one custom EventBridge event bus
- zero or more EventBridge rules on that bus
- one or more targets per declared rule
- optional target-level input transformers

It exposes:

- event bus name
- event bus ARN
- event bus ID
- rule names and ARNs
- target IDs and target ARNs

Rules receive structured Terraform event patterns, which the module encodes as
the JSON required by EventBridge.

---

## Module Boundary

The module owns:

- custom event bus creation and tagging
- rules built from caller-supplied event patterns
- target attachments and optional target roles
- target input transformers
- bus, rule, and target outputs

It does not own:

- SNS topics or SQS queues
- target resource policies
- Lambda IAM permissions or environment variables
- domain-event publishing code
- target consumer behavior
- CloudWatch alarms and dashboards

Those responsibilities belong to target modules, IAM, workload code,
observability, or environment composition.

---

## Deployed Routing

The platform uses the custom bus as its post-commit domain-event router.

The `dev` environment composes these rules:

| Rule key | Matched detail types | Target |
| --- | --- | --- |
| `admin_lifecycle_notifications` | `event.created`, `event.cancelled` | Admin SNS topic |
| `admin_update_notifications` | `event.updated` | Admin SNS topic |
| `participant_notification_dispatch` | `event.updated`, `event.cancelled` | SQS `notification-dispatch` |

The event-management workloads publish:

- `event.created`
- `event.updated`
- `event.cancelled`

The module routes these events but does not publish them or process target
deliveries.

---

## Target Permission Boundary

EventBridge targets often need resource policies before delivery can work.

The current environment owns:

- the SNS topic policy allowing the two admin rules to publish
- the SQS queue policy allowing the participant dispatch rule to send messages

Those permissions are intentionally outside this module.

Each policy protects a concrete target resource and is scoped to the deployed
source rule ARN and AWS account. The environment root owns those cross-resource
relationships. This module accepts target ARNs without mutating resources it
does not own.

---

## Rule and Target Model

Rules are passed as a map.

Each rule defines:

- an optional rule name override
- an optional description
- one EventBridge event pattern
- one or more targets

Event patterns are supplied as Terraform values and encoded to JSON inside the
module. This lets callers write readable Terraform such as:

```hcl
event_pattern = {
  source        = ["aws-serverless-events-platform"]
  "detail-type" = ["event.updated", "event.cancelled"]
}
```

Targets are nested under each rule in the input because that is easiest for a
caller to read. The module flattens them internally so Terraform can create one
`aws_cloudwatch_event_target` resource per target.

Targets may define an optional EventBridge input transformer. The deployed
admin SNS targets use transformers to create readable email messages while the
participant SQS target receives the domain event without a transformer.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- create a custom EventBridge event bus
- define rules using structured event patterns
- attach an SNS target with an input transformer
- attach an SQS target without an input transformer
- keep SNS topic and SQS queue policies outside the EventBridge module while
  keeping the example runnable

Applying the example creates real EventBridge, SNS, and SQS resources and
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
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.37 |



## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_event_bus.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_bus) | resource |
| [aws_cloudwatch_event_rule.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule) | resource |
| [aws_cloudwatch_event_target.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive EventBridge resource names. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_event_bus_name"></a> [event\_bus\_name](#input\_event\_bus\_name) | Optional explicit custom EventBridge event bus name. When null, the module derives the name from name\_prefix. | `string` | `null` | no |
| <a name="input_rules"></a> [rules](#input\_rules) | EventBridge rules and targets to create on the custom event bus.<br/><br/>Each rule defines one event pattern and one or more targets. Target<br/>resource policies, such as SNS topic policies or SQS queue policies, are<br/>intentionally owned outside this module by the target resource owner or<br/>environment composition. | <pre>map(object({<br/>    name          = optional(string)<br/>    description   = optional(string)<br/>    event_pattern = any<br/>    targets = map(object({<br/>      arn      = string<br/>      role_arn = optional(string)<br/>      input_transformer = optional(object({<br/>        input_paths    = map(string)<br/>        input_template = string<br/>      }))<br/>    }))<br/>  }))</pre> | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_event_bus_arn"></a> [event\_bus\_arn](#output\_event\_bus\_arn) | ARN of the custom EventBridge event bus. |
| <a name="output_event_bus_id"></a> [event\_bus\_id](#output\_event\_bus\_id) | ID of the custom EventBridge event bus. |
| <a name="output_event_bus_name"></a> [event\_bus\_name](#output\_event\_bus\_name) | Name of the custom EventBridge event bus. |
| <a name="output_rule_arns"></a> [rule\_arns](#output\_rule\_arns) | Map of logical rule key to EventBridge rule ARN. |
| <a name="output_rule_names"></a> [rule\_names](#output\_rule\_names) | Map of logical rule key to EventBridge rule name. |
| <a name="output_target_arns"></a> [target\_arns](#output\_target\_arns) | Map of logical target key in rule.target form to target ARN. |
| <a name="output_target_ids"></a> [target\_ids](#output\_target\_ids) | Map of logical target key in rule.target form to EventBridge target ID. |
<!-- END_TF_DOCS -->
