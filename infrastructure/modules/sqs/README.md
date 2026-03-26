# SQS Messaging Baseline

This module creates the initial SQS messaging baseline for the serverless events platform.

This module is intentionally platform-specific, not a generic queue factory.
It defines the concrete queue infrastructure baseline that later IAM, Lambda, EventBridge, and environment wiring will depend on.

This module manages queue infrastructure only.

---

## What This Module Creates

This module currently creates one or more standard SQS queues from a `queues` map.

For each logical queue definition, it can create:

- a primary standard SQS queue
- an optional dedicated dead-letter queue
- a redrive policy on the source queue when a DLQ is enabled
- a redrive allow policy on the DLQ

This keeps the first messaging-layer implementation small, reviewable, and aligned with the current architecture decisions.

---

## Why This Module Stays Queue-Focused

This step is focused on the reusable messaging primitives that the platform needs first:

- standard SQS queues
- optional dedicated DLQs
- source-to-DLQ retry wiring

The module does not create Lambda event source mappings, IAM permissions, SNS subscriptions, EventBridge rules, or workload-specific message contracts. Those concerns become relevant later, but they are intentionally outside the scope of this first SQS layer.

Keeping the module limited to queue infrastructure makes the design easier to understand and avoids pretending that downstream consumer behavior is already finalized.

---

## Queue Responsibilities

### Primary queues

Primary queues hold the asynchronous work that later platform components may consume.

In v1, these queues are intended for:

- asynchronous side effects after durable business writes
- repair or reconciliation-style jobs
- future retryable background workflows

They are not part of the primary synchronous RSVP acceptance path.

### Dead-letter queues

Dedicated DLQs isolate failed messages per workload.

If a queue enables `create_dlq`, the module creates a dedicated DLQ for that queue and attaches the corresponding redrive and redrive-allow policies. This keeps failure handling explicit and avoids mixing unrelated failed messages into one shared queue.

---

## Key Design Decisions

### SQS remains outside the primary RSVP write path

This module is aligned with the locked architecture decision that the primary RSVP write path remains synchronous through durable DynamoDB commit.

The important boundary in this step is that SQS is reserved for asynchronous side effects and background work after durable state changes, not for the core RSVP acceptance path.

### Standard queues only in v1

This first implementation supports standard queues only.

That is intentional:

- the roadmap currently needs an initial asynchronous messaging baseline, not ordering-specific behavior
- standard queues are enough for downstream side effects and repair-style work
- adding FIFO support now would increase module complexity before a real workload requires it

FIFO, deduplication, and ordering-specific behavior can be added later if a validated use case appears.

### Dedicated DLQs are per queue

If a queue enables DLQ support, it receives its own dedicated DLQ.

That is intentional:

- easier debugging
- better future alarms and metrics
- cleaner operational isolation
- no mixing of unrelated failed messages

### Queue names derive from logical keys

Queue names are rendered from the shared `name_prefix` plus the logical queue key.

Primary queue naming:

- `<name_prefix>-<logical-key>`

DLQ naming:

- `<name_prefix>-<logical-key>-dlq`

Because logical keys become part of resource names and output map keys, they should stay stable, lowercase, and hyphenated.

---

## Inputs

This module keeps its public input surface intentionally small:

- `name_prefix`
- `tags`
- `queues`

This keeps naming and tagging aligned with the environment root while avoiding a premature over-generic abstraction.

---

## Outputs

The module exposes queue outputs keyed by logical queue name:

- `queue_names`
- `queue_arns`
- `queue_urls`

For queues that create dedicated DLQs, it also exposes:

- `dlq_names`
- `dlq_arns`
- `dlq_urls`

This gives later IAM, Lambda, and environment wiring the queue identifiers they need without over-exposing unrelated implementation details.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- build the shared `name_prefix`
- define the baseline tag map
- call the module with the minimal input surface
- exercise both supported v1 code paths:
  - a queue with a DLQ
  - a queue without a DLQ

The example is safe to run with local state and does not require environment wiring.

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
| [aws_sqs_queue.dlq](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue) | resource |
| [aws_sqs_queue.primary_with_dlq](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue) | resource |
| [aws_sqs_queue.primary_without_dlq](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue) | resource |
| [aws_sqs_queue_redrive_allow_policy.dlq](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue_redrive_allow_policy) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive SQS queue and DLQ names. | `string` | n/a | yes |
| <a name="input_queues"></a> [queues](#input\_queues) | Map of queue definitions keyed by logical queue name.<br/><br/>Logical queue keys should be stable, lowercase, and hyphenated because they<br/>are used to derive rendered queue names and output map keys. | <pre>map(object({<br/>    create_dlq                 = optional(bool)<br/>    visibility_timeout_seconds = optional(number)<br/>    message_retention_seconds  = optional(number)<br/>    receive_wait_time_seconds  = optional(number)<br/>    max_receive_count          = optional(number)<br/>  }))</pre> | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_dlq_arns"></a> [dlq\_arns](#output\_dlq\_arns) | Map of logical queue key to rendered DLQ ARN for queues that create a dedicated DLQ. |
| <a name="output_dlq_names"></a> [dlq\_names](#output\_dlq\_names) | Map of logical queue key to rendered DLQ name for queues that create a dedicated DLQ. |
| <a name="output_dlq_urls"></a> [dlq\_urls](#output\_dlq\_urls) | Map of logical queue key to rendered DLQ URL for queues that create a dedicated DLQ. |
| <a name="output_queue_arns"></a> [queue\_arns](#output\_queue\_arns) | Map of logical queue key to rendered SQS queue ARN. |
| <a name="output_queue_names"></a> [queue\_names](#output\_queue\_names) | Map of logical queue key to rendered SQS queue name. |
| <a name="output_queue_urls"></a> [queue\_urls](#output\_queue\_urls) | Map of logical queue key to rendered SQS queue URL. |
<!-- END_TF_DOCS -->
