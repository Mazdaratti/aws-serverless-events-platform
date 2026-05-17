# Lambda Execution IAM Baseline

This module creates the initial Lambda execution IAM baseline for the serverless events platform.

It is intentionally platform-specific. The goal is not to provide a generic IAM framework or arbitrary policy factory. Instead, this module defines the concrete workload execution roles and least-privilege policy baseline that later Lambda and environment wiring will depend on.

This module is Lambda-execution-only in v1.

---

## What This Module Creates

This module currently creates one IAM role and one customer-managed IAM policy per supported workload:

- `create-event`
- `get-event`
- `list-events`
- `list-my-events`
- `update-event`
- `cancel-event`
- `rsvp-authorizer`
- `rsvp`
- `get-event-rsvps`
- `notification-planner`
- `notification-sender`

Each role uses the Lambda service trust relationship, and each role receives its own workload-specific least-privilege policy.

This keeps the first IAM implementation small, reviewable, and aligned with the current architecture and workload boundaries.

---

## Why This Module Stays Lambda-Focused

This step is focused on the workload execution IAM that the platform clearly needs next:

- Lambda execution roles
- Lambda trust relationships
- workload-specific DynamoDB permissions
- workload-specific SQS consumer and producer permissions
- scoped Cognito user lookup permissions for notification sender
- scoped SES templated-send permissions for notification sender
- CloudWatch Logs write permissions
- optional X-Ray write permissions
- optional EventBridge `PutEvents` permissions for event-management write workloads

The module does not create EventBridge roles, EventBridge rules, EventBridge
targets, API Gateway roles, Cognito roles, Lambda functions, or arbitrary
caller-defined JSON policy documents. Those concerns may become relevant later,
but they are intentionally outside this IAM layer.

Keeping the module limited to Lambda execution IAM makes the design easier to understand and avoids forcing `envs/dev` to describe IAM internals later.

---

## Why Roles Are Separated By Workload

This module uses separate execution roles per workload instead of one shared broad Lambda role.

That is intentional:

- clearer least-privilege boundaries
- easier AWS inspection and validation
- easier future Lambda wiring
- less risk of permission growth across unrelated workloads

The current workload set is aligned to the repository's architecture and placeholder direction:

- `create-event`
- `get-event`
- `list-events`
- `list-my-events`
- `update-event`
- `cancel-event`
- `rsvp-authorizer`
- `rsvp`
- `get-event-rsvps`
- `notification-planner`
- `notification-sender`

---

## Workload Responsibilities

### `create-event`

This role is intended for the Lambda that creates new event records.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- DynamoDB write access for the `events` table
- optional EventBridge `PutEvents` access to the configured publish event bus

Only this event-management write role receives publish access when the optional EventBridge publish bus ARN is provided.

### `get-event`

This role is intended for the Lambda that reads a single canonical event
record by public identifier.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- narrow DynamoDB `GetItem` access for the `events` table

This role intentionally stays narrower than `list-events` because single-item
lookup does not need `Scan`, `Query`, or GSI access. The handler reads one
known record directly through:

- `event_pk = EVENT#<event_id>`

### `list-events`

This role is intended for the Lambda that reads event listings.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- temporary DynamoDB `Scan` access for the `events` table

`Scan` is currently included only as a temporary contract accommodation for the
public broad listing path. The long-term design direction remains validated
query access patterns and GSIs.

### `list-my-events`

This role is intended for the Lambda that reads creator-scoped event listings.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- narrow DynamoDB `Query` access for the `creator-events` GSI

### `update-event`

This role is intended for the Lambda that performs partial updates against a
single canonical event record.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- narrow DynamoDB `GetItem` and `UpdateItem` access for the `events` table
- optional EventBridge `PutEvents` access to the configured publish event bus

Only event-management write roles receive publish access when the optional EventBridge publish bus ARN is provided.

This role intentionally stays narrower than a generic write role because the
current `update-event` contract only needs:

- a primary-key read to load the current event
- a conditional in-place update of that same event item

It does not currently need:

- `Scan`
- `Query`
- GSI access
- RSVP table access
- SQS access

### `rsvp-authorizer`

This role is intended for the dedicated mixed-mode Lambda authorizer that
supports anonymous and authenticated RSVP access on the same route.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions

This role intentionally stays logs-only.

It does not currently need:

- DynamoDB access
- SQS access
- Cognito read permissions
- EventBridge access

The authorizer validates Cognito-issued JWTs from the presented bearer token
using token claims plus Cognito verification material. It does not call Cognito
read APIs as part of this v1 IAM shape.

### `cancel-event`

This role is intended for the Lambda that performs the soft-delete lifecycle
transition for a single canonical event record.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- narrow DynamoDB `GetItem` and `UpdateItem` access for the `events` table
- optional EventBridge `PutEvents` access to the configured publish event bus

Only event-management write roles receive publish access when the optional EventBridge publish bus ARN is provided.

This role intentionally stays narrow because the current `cancel-event`
contract only needs:

- a primary-key read to load the current event
- a conditional in-place update that sets `status = CANCELLED`
- removal of the public discovery helper attributes from that same event item

It does not currently need:

- `Scan`
- `Query`
- GSI access
- RSVP table access
- SQS access

### `rsvp`

This role is the most important IAM role in this step because it supports the synchronous transactional RSVP flow.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- DynamoDB access across both business tables
- `TransactWriteItems` support for the synchronous RSVP business flow

This role intentionally does not receive SQS permissions.

That boundary matters because the locked architecture keeps RSVP in the synchronous transactional core:

`Client -> API Gateway -> Lambda -> DynamoDB transaction`

Asynchronous processing begins only after the durable state change.

### `get-event-rsvps`

This role is intended for the Lambda that reads one event's RSVP list for the
event creator or an admin.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- narrow DynamoDB `GetItem` access for the `events` table
- narrow DynamoDB `Query` access for the `rsvps` table

This role stays read-only on purpose.

The handler flow first reads the canonical event item to apply existence and
authorization rules, then queries one event-scoped RSVP page. It does not
currently need:

- `PutItem`
- `UpdateItem`
- `Scan`
- GSI access
- SQS access

### `notification-planner`

This role is intended for the Lambda that translates one event-level
participant notification message into recipient-level email jobs.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- narrow SQS consumer permissions for `notification-dispatch`
- narrow DynamoDB `Query` access for the `rsvps` table
- narrow SQS `SendMessage` access for `notification-email`

It intentionally does not receive:

- Cognito read permissions
- SES permissions
- SQS consumer permissions for `notification-email`
- EventBridge publish permissions

### `notification-sender`

This role is intended for the Lambda that consumes recipient-level email
jobs and resolves the current recipient email address from Cognito at send time.

It currently receives:

- CloudWatch Logs write permissions
- optional X-Ray write permissions
- narrow SQS consumer permissions for `notification-email`
- scoped `cognito-idp:ListUsers` access for the configured Cognito User Pool
- scoped `ses:SendTemplatedEmail` access for the configured SES sender identity
  and participant notification templates

The sender uses `ListUsers` because participant recipient messages carry the
canonical Cognito `sub` as `recipient_user_id`. The sender implementation uses
an exact server-side `sub = "<recipient_user_id>"` filter and requires exactly
one matching user.

The sender uses SES templated sending so reusable participant email subject,
plain-text, and HTML definitions stay in SES template resources while the
Lambda supplies safe template data at send time.

SES templated sending authorizes both the sender identity and the stored
template resources, so this module requires the SES sender identity ARN and the
participant notification template ARNs.

It intentionally does not receive:

- RSVP table permissions
- SQS permissions for `notification-dispatch`
- EventBridge publish permissions

---

## Key Design Decisions

### Lambda trust only in v1

This module creates Lambda execution roles only.

Every role trusts:

- `lambda.amazonaws.com`

No other service principals are supported in this step.

### Policies are customer-managed and workload-specific

Each workload receives its own customer-managed policy.

That is intentional:

- clearer AWS console inspection
- easier validation evidence later
- cleaner least-privilege boundaries
- no monolithic shared policy growth

### EventBridge publishing is limited to event-management writes

When `eventbridge_publish_event_bus_arn` is set, this module grants
`events:PutEvents` only to:

- `create-event`
- `update-event`
- `cancel-event`

Read workloads, RSVP workloads, authorizers, and notification workers do not
receive EventBridge publish access.

This keeps post-commit domain event publishing tied to the write workloads that
can actually create the locked v1 event-management domain events.

### The module consumes only exact resource ARNs

The input surface stays intentionally small:

- `name_prefix`
- `tags`
- `events_table_arn`
- `rsvps_table_arn`
- `notification_dispatch_queue_arn`
- `notification_email_queue_arn`
- `cognito_user_pool_arn`
- `ses_sender_identity_arn`
- `ses_template_arns`
- `eventbridge_publish_event_bus_arn`
- `workloads`

This keeps the module aligned with the thin-environment rule and avoids premature generic IAM abstraction.

---

## Outputs

The module exposes only the role identifiers later layers are likely to need:

- `role_names`
- `role_arns`

Both outputs are keyed by logical workload name.

This gives later environment and Lambda wiring the role identities they need without over-exposing unrelated implementation details.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- build the shared `name_prefix`
- define the baseline tag map
- create minimal DynamoDB, SQS, and Cognito supporting resources
- provide an SES sender identity ARN and SES template ARNs for scoped sender
  permissions
- create a minimal custom EventBridge bus for scoped publish permissions
- call the module with all currently supported workload roles, including the
  logs-only `rsvp-authorizer` workload and split notification planner/sender
  roles
- inspect the resulting role names and ARNs

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

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_iam_policy.workload](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_role.workload](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy_attachment.workload](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_policy_document.lambda_assume_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.workload](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_partition.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/partition) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_cognito_user_pool_arn"></a> [cognito\_user\_pool\_arn](#input\_cognito\_user\_pool\_arn) | ARN of the Cognito User Pool used by the notification sender to resolve recipient email addresses by canonical user ID. | `string` | n/a | yes |
| <a name="input_eventbridge_publish_event_bus_arn"></a> [eventbridge\_publish\_event\_bus\_arn](#input\_eventbridge\_publish\_event\_bus\_arn) | ARN of the EventBridge event bus write workloads may publish domain events to. When null, no EventBridge publish permissions are granted. | `string` | `null` | no |
| <a name="input_events_table_arn"></a> [events\_table\_arn](#input\_events\_table\_arn) | ARN of the DynamoDB events table used by workload-specific IAM policies. | `string` | n/a | yes |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive IAM role and policy names. | `string` | n/a | yes |
| <a name="input_notification_dispatch_queue_arn"></a> [notification\_dispatch\_queue\_arn](#input\_notification\_dispatch\_queue\_arn) | ARN of the notification-dispatch SQS queue consumed by the notification planner. | `string` | n/a | yes |
| <a name="input_notification_email_queue_arn"></a> [notification\_email\_queue\_arn](#input\_notification\_email\_queue\_arn) | ARN of the notification-email SQS queue written by the notification planner and consumed by the notification sender. | `string` | n/a | yes |
| <a name="input_rsvps_table_arn"></a> [rsvps\_table\_arn](#input\_rsvps\_table\_arn) | ARN of the DynamoDB RSVP table used by workload-specific IAM policies. | `string` | n/a | yes |
| <a name="input_ses_sender_identity_arn"></a> [ses\_sender\_identity\_arn](#input\_ses\_sender\_identity\_arn) | ARN of the SES sender identity used by the notification sender to send participant email through SES templates. | `string` | n/a | yes |
| <a name="input_ses_template_arns"></a> [ses\_template\_arns](#input\_ses\_template\_arns) | Map of SES participant notification template ARNs used by the notification sender. | `map(string)` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_workloads"></a> [workloads](#input\_workloads) | Map of Lambda workload role definitions keyed by logical workload name.<br/><br/>Supported workload keys in v1:<br/>- create-event<br/>- get-event<br/>- list-events<br/>- list-my-events<br/>- update-event<br/>- cancel-event<br/>- rsvp-authorizer<br/>- rsvp<br/>- get-event-rsvps<br/>- notification-planner<br/>- notification-sender | <pre>map(object({<br/>    access_profile = string<br/>    enable_logs    = optional(bool)<br/>    enable_xray    = optional(bool)<br/>  }))</pre> | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_role_arns"></a> [role\_arns](#output\_role\_arns) | Map of logical workload key to rendered IAM role ARN. |
| <a name="output_role_names"></a> [role\_names](#output\_role\_names) | Map of logical workload key to rendered IAM role name. |
<!-- END_TF_DOCS -->
