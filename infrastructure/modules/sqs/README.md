# SQS Queue Module

This module creates standard SQS queues with optional dedicated dead-letter
queues for the serverless events platform.

It is intentionally focused on queue infrastructure rather than application
routing or consumer behavior.

Each environment root documents its concrete queues, producers, consumers, and
event-source mappings. The platform-wide messaging model is documented in the
[architecture guide](../../../docs/architecture.md).

---

## What This Module Creates

This module creates one or more standard SQS queues from a `queues` map.

For each logical queue definition, it can create:

- a primary standard SQS queue
- an optional dedicated dead-letter queue
- a redrive policy on the source queue when a DLQ is enabled
- a redrive allow policy on the DLQ

The caller controls each queue's visibility timeout, message retention,
long-polling wait time, and redrive threshold.

---

## Module Boundary

The module owns:

- standard queue creation and configuration
- optional dedicated DLQs
- source-queue redrive policies
- DLQ redrive allow policies
- queue and DLQ names, ARNs, URLs, and tags

It does not own:

- Lambda event source mappings
- IAM permissions or queue resource policies
- EventBridge targets
- SNS subscriptions
- message schemas or consumer behavior
- CloudWatch alarms and dashboards

Those responsibilities belong to callers, workload code, IAM, or observability.

---

## Queue Behavior

### Primary queues

Primary queues buffer asynchronous work for consumers defined by the composing
root. The module does not prescribe producers, consumers, message schemas, or
event-source mappings.

### Dead-letter queues

Dedicated DLQs isolate failed messages per logical queue.

If a queue enables `create_dlq`, the module creates a dedicated DLQ and attaches
the corresponding redrive and redrive-allow policies. This keeps failure
handling explicit and avoids mixing unrelated failed messages into one shared
queue.

---

## Key Design Decisions

### Standard queues only

The module supports standard queues only.

That is intentional:

- the module's supported use cases require retry and buffering rather than
  ordering guarantees
- the module does not expose unused FIFO or deduplication configuration
- callers that require FIFO semantics need a separate, explicit module contract

### Dedicated DLQs are per queue

If a queue enables DLQ support, it receives its own dedicated DLQ.

That is intentional:

- easier debugging
- workload-specific alarms and metrics
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

This keeps naming and tagging aligned with the composing root without turning
the module into an unrestricted queue factory.

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

Callers can use these identifiers for IAM policies, resource policies,
producers, consumers, event-source mappings, and observability without requiring
the module to own those integrations.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- build the shared `name_prefix`
- define the baseline tag map
- call the module with the minimal input surface
- exercise both supported queue paths:
  - a queue with a DLQ
  - a queue without a DLQ

Applying the example creates real SQS resources and should be reviewed before
use in an AWS account.

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
