# EventBridge Routing Baseline

This module creates the reusable EventBridge routing baseline for the
serverless events platform.

It is intentionally platform-specific. The goal is not to provide a generic
EventBridge framework or a broad event integration factory. Instead, this
module defines the concrete EventBridge bus, rule, and target primitives that
later SNS, SQS, IAM, Lambda, and environment wiring will compose around.

This module manages EventBridge resources only.

---

## What This Module Creates

This module currently creates:

- one custom EventBridge event bus
- zero or more EventBridge rules on that bus
- one or more EventBridge targets per declared rule, with optional input transformers

It also exposes the core outputs later platform layers need, including:

- event bus name
- event bus ARN
- event bus ID
- rule names and ARNs
- target IDs and target ARNs

This keeps the first EventBridge implementation small, reviewable, and aligned
with the locked async notification routing contract.

---

## Why This Module Stays EventBridge-Focused

This step is focused on the reusable EventBridge routing primitives the
platform clearly needs next:

- custom event bus creation
- rule creation from caller-supplied event patterns
- target attachment for matched events
- multiple targets per rule
- optional target-level input transformers for formatted downstream messages

The module does not create SNS topics, SQS queues, SQS queue policies, SNS topic
policies, Lambda publishing permissions, Lambda environment variables, Lambda
code, or environment wiring. Those resources either belong to their own modules
or to the environment composition layer that owns the concrete target resources.

Keeping this module limited to EventBridge resource logic makes the design
easier to understand while preserving thin `envs/dev` composition later.

---

## Routing Direction

The platform's locked async notification direction uses EventBridge as the
post-commit domain event router.

Later environment wiring is expected to compose rules for:

- admin/platform notification fanout to SNS
- participant-notification planning fanout to SQS

The current locked v1 event-management domain events are:

- `event.created`
- `event.updated`
- `event.cancelled`

This module does not publish those events. It only creates the EventBridge
resources that later publishing and routing work will use.

---

## Target Permission Boundary

EventBridge targets often need resource policies before delivery can work.

Examples:

- an SQS queue policy allowing `events.amazonaws.com` to send messages
- an SNS topic policy allowing `events.amazonaws.com` to publish messages
- a Lambda permission allowing EventBridge to invoke a function

Those permissions are intentionally outside this module.

That is because the policy protects the target resource, and the target owner
or environment composition layer has the clearest view of the correct scope.
This module accepts target ARNs and creates EventBridge target attachments, but
it does not mutate target resources it does not own.

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

Targets may also define an optional EventBridge input transformer. This is
useful when a downstream target, such as an SNS topic, needs a readable message
shape without changing the compact domain event payload published by Lambdas.

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
  still making
  the example runnable

The example is safe to validate with local state and does not require
environment wiring.

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
