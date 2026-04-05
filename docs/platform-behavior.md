# Platform Behavior Contracts

This document records the currently locked platform behavior contracts for the
serverless events platform.

It is intentionally more specific than `docs/architecture.md`.

The architecture document stays focused on high-level system design and service
boundaries. This document captures the current behavioral and authorization
rules that implementation work should follow across Lambda handlers, API
planning, and future environment wiring.

---

## Contract Scope

This document is the working source of truth for:

- event visibility and ownership behavior
- RSVP access rules
- account-management direction
- auth versus business-authorization boundaries
- Lambda implementation sequencing

It should be updated when the platform's intended behavior changes in a
meaningful way.

---

## Auth Boundary

Generic authentication is handled outside Lambda.

### Cognito and API Gateway are responsible for

- user registration
- user login
- token issuance
- password reset and change-password flows
- user verification
- generic route protection
- JWT validation
- admin group and claim delivery

### Lambda functions are not responsible for

- login
- session management
- JWT verification
- generic auth implementation

### Lambda functions are still responsible for

- ownership checks
- admin-versus-non-admin business decisions
- event-type-dependent authorization
- platform-specific deletion and cleanup decisions

This split is intentional:

- Cognito and API Gateway handle identity
- Lambda handles business authorization where the decision depends on resource
  ownership or event type

---

## Account Lifecycle Direction

### Cognito-native account behavior

The platform expects Cognito to handle:

- account creation
- account login
- password reset
- password change
- user verification
- user-group membership such as admin
- disabling or deleting the identity itself

### Platform-managed account behavior

The platform still needs application-level decisions for:

- account deletion side effects
- ownership reassignment or retention policy
- event and RSVP data cleanup strategy
- future app-specific profile logic if introduced

So account deletion is not just an identity-provider action.

It should later be implemented as a platform-controlled workflow plus the
relevant Cognito action.

---

## Event Behavior Contracts

### `create-event`

#### Access rule

- authenticated users may create public events
- authenticated users may create protected events
- admin users may also create admin-only events

#### Ownership rule

- event ownership must be derived from caller identity
- `creator_id` should come from `requestContext.authorizer.user_id`
- request-body `creator_id` must not be trusted as the source of ownership

#### Current implementation note

The deployed `create-event` Lambda now enforces the locked creation contract:

- authenticated-only event creation
- ownership derived from `requestContext.authorizer.user_id`
- request-body `creator_id` ignored as an ownership source
- admin-only events restricted to admin callers

### `list-events`

#### Access rule

- all users may use broad event listing
- authenticated users may additionally use `mine`

#### Query modes currently locked

- `all`
- `mine`

#### Request contract

Support both:

- direct invocation payload
- API Gateway-style `queryStringParameters`

Supported request parameters:

- `mode`
- `limit`
- `next_cursor`

#### Default

- `mode=all`

#### Response contract

The Lambda returns an API Gateway-style wrapped response.

The response body shape is:

- `items`
- `next_cursor`
- `mode`

#### Event DTO contract

`list-events` should return a stable public event DTO instead of raw or
half-cleaned DynamoDB storage items.

The public event DTO is:

- `event_id`
- `title`
- `date`
- `description`
- `location`
- `capacity`
- `is_public`
- `requires_admin`
- `created_by`
- `created_at`
- `rsvp_count`
- `attending_count`

These mappings are locked:

- `event_pk` -> `event_id` without the `EVENT#` prefix
- `creator_id` -> `created_by`
- `rsvp_total` -> `rsvp_count`

These fields must stay hidden from the public event DTO:

- all GSI helper fields
- `not_attending_count`

All DTO fields must always be present in the response.

Optional storage fields should be normalized to:

- empty string for text fields
- `null` for optional numeric fields where appropriate

For events, `capacity = null` means unlimited attendance.

Timestamp presentation is intentionally split across backend and frontend:

- Lambda/API responses return `created_at` as an ISO 8601 UTC timestamp
- the frontend is responsible for rendering user-friendly date/time text for
  people

This keeps the API-facing event model cleaner than the storage model while
still exposing the most useful UI-oriented event information.

#### Mapping ownership

Event DTO mapping belongs in Lambda code, not in API Gateway.

The storage model and API model are intentionally separate:

- DynamoDB keeps the current canonical storage item shape
- Lambda handlers map storage items into the public event DTO

#### Pagination contract

- `next_cursor` is an opaque string cursor
- internally it is derived from DynamoDB `LastEvaluatedKey`
- the public contract must not expose raw DynamoDB key structure directly

#### Caller context for direct invocation and tests

Before API Gateway wiring, caller identity is represented as:

- `requestContext.authorizer.user_id`

This keeps test and direct-invocation event shapes aligned with the future
API Gateway/Cognito handoff.

#### Current implementation direction

- `mode=all` uses a temporary table `Scan`
- `mode=mine` uses the `creator-events` GSI
- pagination is required in both modes

This is an intentional tradeoff:

- broad listing preserves the current product direction
- creator-scoped listing already aligns with the validated DynamoDB access
  pattern
- long-term scan reduction remains desirable, but broad listing is currently an
  intentional platform behavior

#### Current implementation note

The deployed `list-events` Lambda now validates the currently locked read
contract in `dev`:

- broad `all` mode returns the current event collection
- authenticated `mine` mode returns creator-scoped events
- `mine` without caller context returns `400`
- returned items use the locked public event DTO

### `get-event`

#### Access rule

- all users may read a single event by public identifier
- no caller context is required in this step

#### Request contract

Support both:

- direct invocation payload
- API Gateway-style `pathParameters`

Supported request input:

- `event_id`

Resolution order:

1. `pathParameters.event_id`
2. top-level `event_id`

#### Input validation contract

- `event_id` is required
- `event_id` must be a non-empty string after trimming
- clients must pass the public identifier only
- clients must not pass the internal storage key form `EVENT#...`

#### Response contract

The Lambda returns an API Gateway-style wrapped response.

The response body shape is:

- `item`

The returned `item` uses the same locked public event DTO as `list-events`.

#### Visibility direction

The current single-item read behavior is intentionally public:

- public events are readable by anyone
- protected non-public events are readable by anyone
- admin-only events are readable by anyone

At this stage:

- `is_public` and `requires_admin` affect business workflows such as RSVP and
  later mutation rules
- they do not restrict single-item event-detail reads

If this product direction changes later, both read handlers should be updated
together:

- `list-events`
- `get-event`

#### DynamoDB lookup contract

- `get-event` uses DynamoDB `GetItem`
- the public identifier is translated into the canonical key:
  - `event_pk = EVENT#<event_id>`
- no `Scan`
- no `Query`
- no GSI access pattern

#### Not-found behavior

- `404` is returned only when the event item does not exist
- the response body is:
  - `{"message": "Event not found."}`

#### Current implementation note

The deployed `get-event` Lambda now validates the currently locked single-item
read contract in `dev`:

- direct single-item reads succeed without caller context
- API Gateway-style `pathParameters.event_id` is supported
- missing items return `404`
- returned items use the locked public event DTO under `item`

### `update-event`

#### Access rule

- event creator may update their own event
- admin may update any event

#### Operation model

`update-event` is a partial update operation, not a full replace.

Mutable fields:

- `title`
- `date`
- `description`
- `location`
- `capacity`
- `is_public`
- `requires_admin`

Immutable/system-managed fields:

- `event_id`
- `created_by`
- `created_at`
- `rsvp_count`
- `attending_count`

#### Request contract

Support both:

- direct invocation payload
- API Gateway-style invocation with `body` JSON

Event identity resolution order:

1. `pathParameters.event_id`
2. top-level `event_id`

Update payload resolution:

- if `body` is present, it must be a JSON string that decodes to an object
- that decoded object becomes the update payload
- otherwise, top-level fields are treated as the update payload for direct invocation

#### Payload rules

- the payload must contain at least one mutable field
- only supported mutable fields may be sent
- unknown fields are rejected
- immutable fields are rejected, not silently ignored

#### Input validation contract

- `event_id` is required
- `event_id` must be a non-empty string after trimming
- clients must pass the public identifier only
- clients must not pass the internal storage key form `EVENT#...`
- if `body` is present but is not valid JSON, return `400`
- if `body` decodes to anything other than an object, return `400`
- if no mutable fields are provided, return `400`
- if unknown fields are present, return `400`
- if immutable fields are present, return `400`

#### Authorization direction

Caller identity comes from:

- `requestContext.authorizer.user_id`
- admin flag in authorizer context

Current mutation rule:

- creator may update their own event
- admin may update any event
- all other authenticated callers receive `403`

#### Existence and authorization behavior

`update-event` should evaluate the current item in this order:

1. read the event
2. if it does not exist, return `404`
3. if it exists but the caller is not allowed, return `403`
4. if allowed, continue to validation and update

This operation does not mask unauthorized update attempts as `404`.

#### Field validation direction

Field-level validation should reuse the same business rules already locked in
`create-event` where applicable.

Additional locked rule:

- only admin may set `requires_admin = true`

Capacity safety rule:

- if `capacity` is provided and is less than the current `attending_count`, reject with `400`
- the response should explain that capacity cannot be reduced below the current number of attending RSVPs

#### DynamoDB update strategy

The update path should use:

- `GetItem` first
- authorization and business validation against the current item
- `UpdateItem` second

The write should use a condition that the item still exists.

#### GSI maintenance rules

Index helper attributes must stay correct after updates.

If `date` changes:

- update `creator_events_gsi_sk`
- update `public_upcoming_gsi_sk` if the event remains public

If `is_public` changes:

- add or remove `public_upcoming_gsi_pk`
- add or remove `public_upcoming_gsi_sk`

Also:

- `creator_events_gsi_pk` remains tied to the original creator
- `creator_id` must never change

#### Response contract

`update-event` should return the same API Gateway-style wrapper used by the
other implemented Lambdas.

Success body shape:

- `item`

The returned `item` should use the same locked public event DTO already used by:

- `list-events`
- `get-event`

#### Error contract

- `400` invalid input or business validation failure
- `403` authenticated caller is not allowed to update the event
- `404` event not found
- `500` internal/runtime/data issue

Not used in this direct invocation stage:

- `401`

Not currently locked for this step:

- `409`

### `cancel-event`

#### Access rule

- event creator may cancel their own event
- admin may cancel any event

#### Naming direction

`cancel-event` is preferred over hard delete as the default operation because it
is safer, more realistic, and leaves room for history, notifications, and
later auditability.

---

## RSVP Behavior Contracts

### `rsvp`

RSVP authorization depends on event type.

- public event:
  - anonymous RSVP allowed
- protected event:
  - authenticated user required
- admin event:
  - admin user required

This decision remains business-driven inside Lambda even after API Gateway and
Cognito handle generic auth.

### `get-event-rsvps`

The old monolith/OpenAPI contract exposed this broadly, but the final platform
visibility policy for event RSVP reads is still open.

That final read-policy decision should be locked later when the RSVP read side
is implemented.

---

## OpenAPI Reference Alignment

The older reference OpenAPI currently establishes these broad directions:

- `GET /api/events` is public
- `GET /api/events/{event_id}` is public
- `POST /api/events` requires authentication
- RSVP access varies by event type
- `GET /api/rsvps/event/{event_id}` is public in the old contract

This repository uses that contract as a reference point, not as a requirement
to preserve every old behavior unchanged.

Where the platform intentionally evolves beyond the older behavior, this
document should be treated as the newer source of truth.

---

## Lambda Set

The currently locked Lambda set is:

- `create-event` ✅
- `list-events` ✅
- `get-event` ✅
- `update-event`
- `cancel-event`
- `rsvp`
- `get-event-rsvps`
- `notification-worker`

---

## Locked Implementation Order

The currently locked Lambda implementation order is:

1. `create-event` ✅
2. `list-events` ✅
3. `get-event` ✅
4. `update-event`
5. `cancel-event`
6. `rsvp`
7. `get-event-rsvps`
8. `notification-worker`

This sequence is intentional:

- first create and read basics
- then ownership-based event management
- then transactional RSVP complexity
- then RSVP read/reporting
- then asynchronous side effects

---

## Current Open Questions

The following behaviors are intentionally not fully locked yet:

- final private/admin visibility behavior for `get-event`
- final visibility policy for `get-event-rsvps`
- exact account-deletion cleanup semantics
- implementation details for admin-only event creation beyond the already
  locked business rule that only admins may create admin-only events

These should be decided in the implementation steps where they become
immediately relevant.
