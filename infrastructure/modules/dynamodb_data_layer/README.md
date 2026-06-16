# DynamoDB Business Data Module

This module creates the DynamoDB business data layer for the serverless events
platform.

It is intentionally platform-specific rather than a generic table factory. The
module owns the two canonical business tables and indexes required by the
platform's data-access model.

Concrete environment composition is documented by each environment root. The
platform-wide data model and runtime contracts are documented in the
[architecture guide](../../../docs/architecture.md) and
[platform behavior contract](../../../docs/platform-behavior.md).

---

## What This Module Creates

This module creates two business tables:

- `events`
  - partition key: `event_pk`
- `rsvps`
  - partition key: `event_pk`
  - sort key: `subject_sk`

It also creates two approved global secondary indexes on the `events` table:

- `public-upcoming-events`
- `creator-events`

The tables use configurable billing mode, table class, and point-in-time
recovery settings supplied by the composing environment.

---

## Module Boundary

The module owns:

- table creation and primary-key definitions
- the two approved event indexes
- billing, table-class, and recovery configuration
- table names, tags, and outputs

It does not own:

- Lambda workload permissions
- application item schemas beyond required key attributes
- runtime transactions or conditional expressions
- retry, idempotency, outbox, or worker-state tables
- API and event-driven integration wiring

Those responsibilities belong to IAM, Lambda code, or environment composition.

---

## Table Responsibilities

### `events`

The `events` table stores the canonical event records for the platform.

Its partition key uses:

```text
event_pk = EVENT#<event_id>
```

Event items contain event metadata, lifecycle state, creator ownership,
visibility attributes, and aggregate RSVP helper counters.

The aggregate counters support efficient reads, but they are not the source of
truth for individual RSVP membership.

### `rsvps`

The `rsvps` table stores the canonical RSVP membership records for each event.

This table is the source of truth for attendance membership. It uses an
event-scoped partition and a subject-scoped sort key so callers can query all
RSVP records for one event while supporting authenticated and anonymous
subjects.

The key patterns are:

```text
event_pk  = EVENT#<event_id>
subject_sk = USER#<user_id>
subject_sk = ANON#<anonymous_token>
```

---

## Key Design Decisions

### RSVP membership and counters share a transaction boundary

The table design supports transactional writes across the canonical RSVP
membership record and aggregate event counters. Runtime transaction handling
belongs to application code rather than this infrastructure module.

### Event counters are helper fields

The `events` table is allowed to store aggregate helper counters such as:

- `rsvp_total`
- `attending_count`
- `not_attending_count`

Those values improve read efficiency, but the `rsvps` table remains the source of truth for individual RSVP membership and attendance state.

### No RSVP-by-user GSI

The module does not create an RSVP-by-user index.

That is intentional:

- the base key supports event-scoped RSVP queries
- the module has no subject-centric query requirement
- speculative indexes would add write and maintenance overhead

### Sparse GSI behavior is application-driven

The `events` GSIs are intended to behave sparsely.

That sparse behavior depends on the application writing the GSI key attributes only on qualifying event items. If a record should not appear in a given index, the corresponding GSI key attributes should be omitted entirely.

### Event indexes support query-oriented reads

The two sparse event indexes support:

- public upcoming event discovery
- creator-owned event listing

The module creates the indexes but does not control which application workloads
use them or whether another access path performs a table scan.

---

## Inputs

This module keeps its public input surface intentionally small:

- `name_prefix`
- `tags`
- billing and durability settings

This keeps naming and tagging aligned with the composing root without turning
the module into a generic table abstraction.

---

## Outputs

The module exposes:

- events table name and ARN
- RSVP table name and ARN

Callers can pass these identifiers into IAM and compute composition without
requiring the module to own those integrations.

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
