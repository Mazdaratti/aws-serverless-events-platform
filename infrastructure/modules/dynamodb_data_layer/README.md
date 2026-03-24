# DynamoDB Data Layer Module

This module creates the initial DynamoDB business data layer for the serverless events platform.

It is intentionally platform-specific. The goal is not to provide a generic "create any DynamoDB table" abstraction. Instead, this module defines the concrete data-layer baseline that the later API and Lambda layers will depend on.

---

## What This Module Creates

This module currently creates two business tables:

- `events`
- `rsvps`

It also creates two approved global secondary indexes on the `events` table:

- `public-upcoming-events`
- `creator-events`

This keeps the first data-layer implementation small, reviewable, and aligned with the current API and architecture decisions.

---

## Why There Are Only Two Tables

This step is focused on the business data that the platform needs first:

- event records
- RSVP membership records

The module does not create extra operational tables for retry tracking, idempotency, outbox state, or worker state. Those concerns may become relevant later, but they are intentionally outside the scope of this first DynamoDB layer.

Keeping the module limited to the two core business tables makes the design easier to understand and avoids pretending that downstream asynchronous processing requirements are already finalized.

---

## Table Responsibilities

### `events`

The `events` table stores the canonical event records for the platform.

It is intended to hold:

- event identity and metadata
- organizer information
- visibility and access-control flags
- aggregate RSVP helper counters

The aggregate counters are useful for efficient reads, but they are not the source of truth for who has RSVP'd.

### `rsvps`

The `rsvps` table stores the canonical RSVP membership records for each event.

This table is the source of truth for attendance membership. It uses an event-scoped partition and a subject-scoped sort key so the platform can efficiently query all RSVP records for one event while still supporting both authenticated and anonymous RSVP subjects.

---

## Key Design Decisions

### RSVP remains synchronous through durable commit

This module is aligned with the locked architecture decision that the primary RSVP write path is:

`Client -> API Gateway -> Lambda -> DynamoDB transaction -> EventBridge -> downstream async consumers`

The important boundary in this step is that the business write is completed synchronously through DynamoDB first. Asynchronous consumers come after the durable commit and are not part of the core RSVP acceptance path.

### Event counters are helper fields

The `events` table is allowed to store aggregate helper counters such as:

- `rsvp_total`
- `attending_count`
- `not_attending_count`

Those values improve read efficiency, but the `rsvps` table remains the source of truth for individual RSVP membership and attendance state.

### No RSVP GSI yet

This first implementation does not create an RSVP-by-user index.

That is intentional:

- the current contract requires efficient per-event RSVP access, which the base key already supports
- there is no current requirement to list RSVPs by user
- adding speculative indexes too early would make the module larger without solving a current problem

### Sparse GSI behavior is application-driven

The `events` GSIs are intended to behave sparsely.

That sparse behavior depends on the application writing the GSI key attributes only on qualifying event items. If a record should not appear in a given index, the corresponding GSI key attributes should be omitted entirely.

### `/api/events` may still use `Scan` in dev

The current API contract still describes `/api/events` broadly as a "get all events" endpoint.

For the dev baseline, a table `Scan` is acceptable for that endpoint. This is a short-term compromise for the current contract, not the intended long-term production query strategy.

The two `events` GSIs exist to support the next step toward query-based reads:

- public upcoming event discovery
- creator/organizer event listing

---

## Inputs

This module keeps its public input surface intentionally small:

- `name_prefix`
- `tags`
- billing and durability settings

This keeps naming and tagging aligned with the environment root while avoiding a premature generic-table abstraction.

---

## Outputs

The module exposes only the names and ARNs that later layers are likely to need:

- events table name and ARN
- RSVP table name and ARN

This gives future API, Lambda, and IAM wiring the identifiers they need without over-exposing internal implementation details.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- build the shared `name_prefix`
- define the baseline tag map
- call the module with the minimal input surface
- inspect the resulting table names and ARNs

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
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.37.0 |



## Resources

| Name | Type |
|------|------|
| [aws_dynamodb_table.events](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table) | resource |
| [aws_dynamodb_table.rsvps](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive DynamoDB table names. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_billing_mode"></a> [billing\_mode](#input\_billing\_mode) | Billing mode for the DynamoDB tables. | `string` | `"PAY_PER_REQUEST"` | no |
| <a name="input_point_in_time_recovery_enabled"></a> [point\_in\_time\_recovery\_enabled](#input\_point\_in\_time\_recovery\_enabled) | Enable point-in-time recovery for the DynamoDB tables. | `bool` | `true` | no |
| <a name="input_table_class"></a> [table\_class](#input\_table\_class) | Table class for the DynamoDB tables. | `string` | `"STANDARD"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_events_table_arn"></a> [events\_table\_arn](#output\_events\_table\_arn) | ARN of the DynamoDB events table used to store canonical event records. |
| <a name="output_events_table_name"></a> [events\_table\_name](#output\_events\_table\_name) | Name of the DynamoDB events table used to store canonical event records. |
| <a name="output_rsvps_table_arn"></a> [rsvps\_table\_arn](#output\_rsvps\_table\_arn) | ARN of the DynamoDB RSVP table used to store canonical RSVP membership records. |
| <a name="output_rsvps_table_name"></a> [rsvps\_table\_name](#output\_rsvps\_table\_name) | Name of the DynamoDB RSVP table used to store canonical RSVP membership records. |
<!-- END_TF_DOCS -->
