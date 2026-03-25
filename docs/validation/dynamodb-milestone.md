# DynamoDB Milestone Validation

This document describes how the first DynamoDB infrastructure milestone is
validated.

It covers:

- the `dynamodb_data_layer` Terraform module
- the `envs/dev` wiring of that module
- the expected infrastructure checks after provisioning

---

## Milestone Context

This milestone introduces the first durable business data foundation for the
platform.

The DynamoDB data layer establishes:

- the canonical event write model
- the synchronous RSVP transaction pattern
- the initial access-pattern-driven index strategy

Later infrastructure layers such as IAM, Lambda, API Gateway, and messaging
depend on the table names and ARNs exported by this environment.

---

## Validation Goals

This milestone is considered validated when all of the following are confirmed:

- the DynamoDB data layer can be provisioned successfully through Terraform
- the `envs/dev` root composes the module correctly
- the expected tables, indexes, and outputs are created
- the resulting Terraform state is idempotent under a follow-up plan

---

## Required Validation Checks

Confirm all of the following:

- `terraform apply` succeeds in `infrastructure/envs/dev`
- both DynamoDB tables are created in the target AWS region
- table names follow the environment naming convention derived from `name_prefix`
- the `events` table has the approved GSIs:
  - `public-upcoming-events`
  - `creator-events`
- both tables use `PAY_PER_REQUEST`
- both tables use table class `STANDARD`
- point-in-time recovery is enabled on both tables
- expected tags are present
- post-apply `terraform plan` returns a clean result

---

## Terraform Validation

Run from:

- `infrastructure/envs/dev`

Apply the environment:

```bash
terraform apply
```

Check idempotency after apply:

```bash
terraform plan
```

Optional output confirmation:

```bash
terraform output
```

Expected outputs:

- `events_table_name`
- `events_table_arn`
- `rsvps_table_name`
- `rsvps_table_arn`

---

## AWS CLI Validation

Replace the placeholders below with the current environment values:

- `<YOUR_CURRENT_REGION>`
- `<YOUR_EVENTS_TABLE_NAME>`
- `<YOUR_RSVPS_TABLE_NAME>`

List tables:

```bash
aws dynamodb list-tables --region <YOUR_CURRENT_REGION>
```

Describe the `events` table:

```bash
aws dynamodb describe-table \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_EVENTS_TABLE_NAME>
```

Describe the `rsvps` table:

```bash
aws dynamodb describe-table \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_RSVPS_TABLE_NAME>
```

Check point-in-time recovery for `events`:

```bash
aws dynamodb describe-continuous-backups \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_EVENTS_TABLE_NAME>
```

Check point-in-time recovery for `rsvps`:

```bash
aws dynamodb describe-continuous-backups \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_RSVPS_TABLE_NAME>
```

---

## Optional Data Validation

This step is optional but useful for confirming the key design in practice.

Insert one event item and one RSVP item, then verify:

- the event item can be read back
- the RSVP item can be read back
- the public events GSI can be queried
- the RSVP table supports event-scoped partition queries

Replace the placeholders below with the current environment values:

- `<YOUR_CURRENT_REGION>`
- `<YOUR_EVENTS_TABLE_NAME>`
- `<YOUR_RSVPS_TABLE_NAME>`

Optional event insert:

```bash
aws dynamodb put-item \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_EVENTS_TABLE_NAME> \
  --item '{
    "event_pk": {"S": "EVENT#demo-001"},
    "title": {"S": "Portfolio Demo Event"},
    "created_by": {"S": "USER#demo-organizer"},
    "event_date": {"S": "2026-04-10T18:00:00Z"},
    "is_public": {"BOOL": true},
    "public_upcoming_gsi_pk": {"S": "PUBLIC"},
    "public_upcoming_gsi_sk": {"S": "2026-04-10T18:00:00Z#EVENT#demo-001"},
    "creator_events_gsi_pk": {"S": "CREATOR#USER#demo-organizer"},
    "creator_events_gsi_sk": {"S": "2026-04-10T18:00:00Z#EVENT#demo-001"},
    "rsvp_total": {"N": "1"},
    "attending_count": {"N": "1"},
    "not_attending_count": {"N": "0"}
  }'
```

Optional RSVP insert:

```bash
aws dynamodb put-item \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_RSVPS_TABLE_NAME> \
  --item '{
    "event_pk": {"S": "EVENT#demo-001"},
    "subject_sk": {"S": "USER#demo-attendee"},
    "response": {"S": "attending"},
    "created_at": {"S": "2026-03-25T12:00:00Z"}
  }'
```

Optional GSI query:

```bash
aws dynamodb query \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_EVENTS_TABLE_NAME> \
  --index-name public-upcoming-events \
  --key-condition-expression "public_upcoming_gsi_pk = :pk" \
  --expression-attribute-values '{
    ":pk": {"S": "PUBLIC"}
  }'
```

Optional RSVP partition query:

```bash
aws dynamodb query \
  --region <YOUR_CURRENT_REGION> \
  --table-name <YOUR_RSVPS_TABLE_NAME> \
  --key-condition-expression "event_pk = :pk" \
  --expression-attribute-values '{
    ":pk": {"S": "EVENT#demo-001"}
  }'
```

If optional demo data is inserted, delete it after validation.

---

## Cleanup

After validation is complete, destroy the temporary development infrastructure:

```bash
terraform destroy
```

Run it from:

- `infrastructure/envs/dev`

This step is recommended when validating locally. In real environments,
infrastructure lifecycle should follow environment promotion and retention
policies.
