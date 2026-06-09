# Platform Behavior Contracts

This document defines the product, API, authorization, identity, and runtime
behavior contracts for the serverless events platform.

It is intentionally more specific than
[architecture.md](architecture.md), which owns service responsibilities and
system boundaries.

---

## Contract Scope

This document is the working source of truth for:

- event visibility and ownership behavior
- event and RSVP API contracts
- account-lifecycle behavior and deferred decisions
- frontend and edge-delivery behavior
- authentication and business-authorization boundaries
- normalized caller-context behavior
- post-commit notification publication and delivery behavior

Operational setup, deployment procedures, and validation evidence belong in
[project-setup.md](project-setup.md), `frontend/README.md`, and the relevant
infrastructure documentation.

---

## Frontend and Edge Delivery Behavior

This section defines the browser-facing routing, authentication, API
consumption, and presentation boundaries used by the frontend.

### Public Entry-Point Model

The public entry point for the product is one CloudFront distribution.

The distribution serves:

- static frontend assets from a private S3 bucket
- backend API requests using the canonical routed API paths

The browser-visible product therefore uses one origin for:

- static frontend assets
- backend API requests

The platform does not introduce a second browser-facing API namespace such as
`/api/*`.

### Routed API Path Contract

The frontend uses these canonical API routes:

- `GET /events`
- `GET /events/mine`
- `GET /events/{event_id}`
- `POST /events`
- `PATCH /events/{event_id}`
- `POST /events/{event_id}/cancel`
- `POST /events/{event_id}/rsvp`
- `GET /events/{event_id}/rsvps`

Frontend code must not invent alternate paths for these operations.

### Frontend Route Namespace

The frontend application uses a dedicated route namespace:

- `/app` and `/app/*`

The frontend must assume:

- all browser navigation occurs under `/app`
- backend API routes remain under `/events`
- no overlap between UI routes and API routes is allowed
- CloudFront serves `/app` routes from the frontend origin

The frontend must not:

- use `/events` paths for UI routing
- depend on API routes serving HTML

This keeps browser navigation and client-side routing separate from the routed
backend API contract.

### Same-Origin Contract

The frontend treats the backend API as same-origin application traffic through
CloudFront.

Rules:

- the frontend must call backend routes through relative paths such as:
  - `/events`
  - `/events/mine`
  - `/events/{event_id}`
- the frontend must not treat the raw API Gateway execute-api hostname as the
  normal browser-facing API base
- the frontend must not hardcode a direct API Gateway stage URL into
  application behavior
- the frontend must use the same browser origin
  for:
  - static frontend assets
  - backend API requests

### Same-Origin Path Separation

Although the frontend and API share the same origin, they are separated by path:

- frontend routes: `/app` and `/app/*`
- API routes: `/events` and `/events/*`

The frontend must:

- use relative paths for API calls, such as `/events`
- not prefix API calls with `/app`
- not assume API routes serve HTML

### CORS Behavior

The reusable API Gateway module supports optional CORS configuration, but the
deployed frontend does not depend on cross-origin API requests.

- the preferred product path is same-origin browser access through CloudFront
- the frontend should not be designed around cross-origin browser calls to the
  raw API Gateway URL
- API Gateway CORS support remains an infrastructure capability for exceptional
  cases such as:
  - temporary direct API testing
  - alternate environment setups
  - integrations that genuinely require cross-origin behavior

CORS remains an infrastructure capability rather than part of the normal
frontend integration contract.

### Frontend authentication behavior

Frontend authentication remains Cognito-managed.

The frontend is responsible for:

- initiating sign-in and sign-out through the chosen frontend auth flow
- holding the authenticated session state needed for browser interaction
- attaching a bearer token for ordinary protected API requests
- omitting authentication when calling public routes
- preserving optional-auth behavior for the mixed-mode RSVP route
- preserving the user's intended in-app destination when a protected UI prompt
  sends them through login, such as:
  - `/my-events`
  - protected/admin event RSVP prompts
  - `/events/{event_id}/rsvps`

The frontend must not:

- derive identity or admin status from request payloads
- invent user identity locally
- bypass Cognito as the source of authenticated user identity
- treat username or email as the internal user identifier

The frontend should understand the routed auth modes as:

- public routes:
  - no bearer token required
- authenticated routes:
  - bearer token required
- mixed-mode RSVP route:
  - bearer token may be absent for anonymous public RSVP
  - bearer token may be present for authenticated RSVP
  - malformed or invalid presented auth should be treated as a failed request,
    not silently downgraded to anonymous behavior

### Frontend request-shape contract

The frontend must follow the current routed API contract and must not rely on
internal storage model details.

Rules:

- use public route paths only
- use public event identifiers only
- never send internal storage key forms such as:
  - `EVENT#...`
- treat pagination cursors as opaque values
- pass `next_cursor` back exactly as received
- not infer DynamoDB key structure from API responses
- not depend on hidden storage-only fields

### Frontend response-consumption contract

The frontend must consume the already locked backend response contracts as they
are exposed by the routed API.

This includes:

- event DTOs returned by:
  - `list-events`
  - `list-my-events`
  - `get-event`
  - `update-event`
  - `cancel-event`
- RSVP write responses returned by:
  - `rsvp`
- RSVP read responses returned by:
  - `get-event-rsvps`

The frontend must treat those API-facing DTOs as the source of truth for UI
rendering rather than trying to reconstruct hidden backend state.

In particular:

- the frontend must use:
  - `event_id`
  - not internal `event_pk`
- the frontend must use:
  - `created_by`
  - not internal `creator_id`
- the frontend must not expect:
  - GSI helper fields
  - raw DynamoDB keys
  - `not_attending_count` inside public event DTOs

### Frontend Timestamp Behavior

Backend APIs return canonical timestamps as ISO 8601 UTC strings.

The frontend:

- the frontend is responsible for user-friendly timestamp rendering
- the frontend should convert backend UTC timestamps into readable UI text for
  people
- the frontend must not require the backend to pre-render presentation-specific
  date strings

This preserves the current backend/frontend responsibility split already used
by the event DTO contract.

### Frontend Route and Presentation Behavior

The frontend must not assume unimplemented routes exist.

The frontend provides:

- public event workflows:
  - public event listing with `GET /events`
  - public event detail with `GET /events/{event_id}`
  - mixed-mode RSVP with `POST /events/{event_id}/rsvp`
- Cognito-backed account access:
  - Cognito-backed register, confirmation, login, logout, and session restore
- event-management workflows:
  - event creation with `POST /events`
  - event editing with `PATCH /events/{event_id}`
  - event cancellation with `POST /events/{event_id}/cancel`
  - creator-scoped event listing with `GET /events/mine`
  - creator/admin RSVP list viewing with `GET /events/{event_id}/rsvps`
  - client-side search, sort, event-state, visibility, and RSVP availability
    controls over already loaded event DTOs
  - route-level lazy loading for page components without changing route paths,
    API paths, or CloudFront `/app` behavior
  - accessible route and form behavior including skip-link support, labelled
    lists, explicit loading/status feedback, and keyboard-reachable destructive
    confirmation flows

These client-side list controls must remain presentation behavior only. They
must not introduce backend query parameters or change the routed API contract.

Public event discovery and owner event management intentionally expose different
client-side control options:

- public event discovery must not expose cancelled-management options when the
  public API result set does not include cancelled events
- owner event management may expose cancelled and status-management options
  because `GET /events/mine` returns owned management records

The RSVP panel may use event visibility flags to choose user-facing guidance:

- public events may explain anonymous RSVP behavior
- protected events should prompt sign-in before RSVP
- admin-only events should explain that admin access is required

This is presentation guidance only. Backend authorizers and business rules remain
the source of truth for whether the RSVP request succeeds.

### Frontend Error-Handling Behavior

The frontend should respect the current routed API error semantics instead of
normalizing all failures into one generic UI state.

Important examples from the backend contract:

- `401`
  - ordinary protected route called without valid authentication
  - rejected at the API edge
- `403`
  - caller is authenticated but not allowed for the requested business action
  - or invalid presented auth on the mixed-mode RSVP route is denied at the
    API edge
- `404`
  - resource does not exist
- `400`
  - validation or business-rule failure

The frontend should preserve these distinctions in a user-appropriate way.

### Frontend non-responsibilities

The frontend must not:

- implement business authorization logic as the source of truth
- duplicate JWT validation logic that belongs to API Gateway or the dedicated
  RSVP authorizer
- depend on direct Lambda invocation shapes
- depend on raw API Gateway authorizer context
- depend on DynamoDB storage model details
- assume CORS is the primary browser integration mechanism
- use `/events` paths for browser UI routing
- depend on API routes serving frontend HTML

Detailed frontend tooling, local validation, deployment helper behavior, and
GitHub Actions workflows are documented in
[frontend/README.md](../frontend/README.md).

---

## Authentication Behavior

The platform uses **Amazon Cognito** as the sole identity provider.

Authentication, route protection, identity normalization, and business
authorization remain separate responsibilities.

### Responsibility Split

| Layer | Responsibility |
|---|---|
| Amazon Cognito | Registration, sign-in, token issuance, email verification, password recovery, and group membership |
| API Gateway | JWT validation for protected routes and invocation of the mixed-mode RSVP authorizer |
| RSVP Lambda authorizer | Optional bearer-token validation and caller-context projection for anonymous or authenticated RSVP access |
| Shared auth normalization | Conversion of upstream authorizer contexts into one internal caller contract |
| Business Lambdas | Resource ownership, event access, capacity, and workflow-specific authorization |

Business Lambdas do not validate JWTs, implement login flows, or infer identity
from headers and request payloads.

### Canonical Identity

The canonical internal user identifier is:

- Cognito user `sub`

It is used as:

- the internal user identifier
- the basis for ownership checks
- the key for user-scoped data such as authenticated RSVP subjects

Username and email must not be treated as internal platform identity keys.

### Normalized Caller Context Contract

Business Lambdas must consume one normalized caller shape:

- `caller.user_id`
- `caller.is_authenticated`
- `caller.is_admin`

Rules:

- authenticated caller:
  - `caller.user_id = <Cognito sub>`
  - `caller.is_authenticated = true`
  - `caller.is_admin = true|false`
- anonymous caller:
  - `caller.user_id = null`
  - `caller.is_authenticated = false`
  - `caller.is_admin = false`

The shared normalization helper accepts native JWT-authorizer and custom
Lambda-authorizer contexts. Handlers resolve caller context once at the request
boundary and use only the normalized values afterward.

For the HTTP API Lambda authorizer, projected values are available under
`requestContext.authorizer.lambda`. Business handlers must not bind their
authorization logic directly to that raw upstream shape.

Anonymous access means no authenticated caller context is present. Upstream
authorizers must not fabricate an anonymous user identity.

### Admin Authorization

Administrative capability comes from membership in the Cognito group:

- `admin`

Normalization sets `caller.is_admin = true` when the authenticated caller
belongs to that group. Business Lambdas trust the normalized value and must not
recompute admin status or accept it from request payloads.

### Sign-In Behavior

Sign-in is Cognito-managed. The deployed behavior uses:

- username as the primary sign-in attribute
- required email collection
- Cognito-managed email verification
- Cognito-managed password recovery

The canonical identity remains Cognito `sub`, so future sign-in changes do not
need to change ownership or user-scoped data keys.

### Route Authentication Modes

| Mode | Routes | Behavior |
|---|---|---|
| Public | `GET /events`, `GET /events/{event_id}` | No authentication required |
| Mixed | `POST /events/{event_id}/rsvp` | Anonymous access allowed; valid bearer tokens preserve authenticated identity |
| Authenticated | `POST /events`, `GET /events/mine`, `PATCH /events/{event_id}`, `POST /events/{event_id}/cancel`, `GET /events/{event_id}/rsvps` | API Gateway JWT validation required |

### Mixed-Mode RSVP Authorizer

The mixed-mode `rsvp` authorizer must not require anonymous callers to present
an `Authorization` header before the authorizer is invoked.

The deployed authorizer configuration uses:

- request authorizer `identity_sources` must be omitted
- `enable_simple_responses` must remain enabled
- request authorizer result TTL must be `0`

This preserves the required mixed-mode behavior:

- no header -> anonymous allowed path can still reach the Lambda authorizer
- valid header -> authenticated path is preserved
- malformed or invalid presented auth is denied instead of silently downgraded
  to anonymous

Any future caching change must preserve these anonymous, authenticated, and
invalid-token outcomes.

---

## Account Lifecycle Behavior

### Cognito-Owned Identity Lifecycle

Cognito owns:

- account creation
- account login
- password reset
- password change
- user verification
- user-group membership such as admin
- disabling or deleting the identity itself

### Platform-Owned Account Lifecycle

Deleting or disabling a Cognito identity does not by itself define what happens
to platform-owned data.

The following account-lifecycle behavior remains intentionally undecided:

- account deletion side effects
- retention, reassignment, anonymization, or deletion of owned events
- retention, anonymization, or deletion of RSVP records
- effects on pending or historical notifications
- whether the first workflow supports deletion, disablement, anonymization, or
  a staged process

No platform account-deletion API or UI should be implemented until these
semantics are defined.

A future account lifecycle workflow must coordinate application-owned data with
the relevant Cognito identity action. The planned implementation work is tracked
in [implementation-roadmap.md](implementation-roadmap.md).

---

## Event Behavior Contracts

### `create-event`

Route:

- `POST /events`

#### Access and Ownership

- authenticated users may create public events
- authenticated users may create protected events
- admin users may also create admin-only events
- event ownership must be derived from caller identity
- `creator_id` comes from `caller.user_id`
- request-body `creator_id` must not be trusted as the source of ownership

#### Creation Contract

New canonical event records use `status = ACTIVE`. The successful response
returns the public event DTO, including `status`.

#### Post-commit EventBridge publication

After successful durable event creation, `create-event` publishes one
`event.created` domain event to EventBridge.

The published detail is compact and notification-safe:

- `event_id`
- `title`
- `actor_user_id`
- `occurred_at`
- `event_detail_path`

The event detail path uses:

- `/app/events/<event_id>`

`create-event` must not publish `event.created` when:

- caller authentication is missing or invalid
- input validation fails
- the caller is not authorized to create the requested event type
- DynamoDB creation does not durably succeed

EventBridge publication failure after durable creation is logged, but it must not:

- change the successful `201` API response
- roll back the DynamoDB creation
- turn the original API result into `500`

### `list-events`

Route:

- `GET /events`

#### Access Rule

- all users may use broad event listing
- the route is public
- no caller context is required or consumed by this handler

#### Request contract

Support both:

- direct invocation payload
- API Gateway-style `queryStringParameters`

Supported request parameters:

- `limit`
- `next_cursor`

#### Response contract

The Lambda returns an API Gateway-style wrapped response.

The response body shape is:

- `items`
- `next_cursor`

#### Event DTO contract

`list-events` returns a stable public event DTO instead of raw DynamoDB storage
items.

The public event DTO is:

- `event_id`
- `status`
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

Field mappings:

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

#### Mapping Ownership

Event DTO mapping belongs in Lambda code, not in API Gateway.

The storage model and API model are intentionally separate:

- DynamoDB keeps the canonical storage item shape
- Lambda handlers map storage items into the public event DTO

#### Pagination Contract

- `next_cursor` is an opaque string cursor
- internally it is derived from DynamoDB `LastEvaluatedKey`
- the public contract must not expose raw DynamoDB key structure directly

#### Read Model

- broad listing uses a temporary table `Scan`
- pagination is required
- creator-scoped listing behavior no longer belongs to this handler
- `list-my-events` owns authenticated creator-scoped listing

This is an explicit optimization boundary:

- the API contract remains independent of the storage access path
- replacing the scan with an indexed query must preserve pagination and DTO
  behavior unless the product contract is deliberately revised

#### Lifecycle and Visibility Behavior

- request parameters are limited to `limit` and `next_cursor`
- cancelled events are excluded by the Lambda
- active non-public and past events may appear in the broad result set
- every returned item includes `status`

### `list-my-events`

Route:

- `GET /events/mine`

#### Access Rule

- authenticated users may list the events they created
- anonymous callers are rejected at the API edge
- missing authenticated caller context must not fall back to public behavior

#### Read Model

This operation owns creator-scoped listing and uses the `creator-events` GSI.
Pagination is required.

The separate route keeps:

- broad event discovery remains public
- creator-scoped event listing authenticated
- route authentication enforced by API Gateway

#### Request contract

Support both:

- direct invocation payload
- API Gateway-style `queryStringParameters`

Supported request parameters:

- `limit`
- `next_cursor`

#### Caller context

Caller identity comes from:

- `caller.user_id`

#### Response contract

The Lambda returns an API Gateway-style wrapped response.

The response body shape is:

- `items`
- `next_cursor`

The returned items use the same public event DTO as:

- `list-events`
- `get-event`

#### Lifecycle Visibility

Visible in this route:

- `ACTIVE`
- `CANCELLED`
- past events

Every returned item includes `status`. Past and cancelled events remain visible
because this is an owner-management view rather than public discovery.

### `get-event`

Route:

- `GET /events/{event_id}`

#### Access Rule

- all users may read a single event by public identifier
- no caller context is required

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

The returned `item` uses the same public event DTO as `list-events`.

#### Visibility Behavior

Single-item reads are public:

- public events are readable by anyone
- protected non-public events are readable by anyone
- admin-only events are readable by anyone

- `is_public` and `requires_admin` affect business workflows such as RSVP and
  mutation
- they do not restrict single-item event-detail reads

Any future visibility change must consider both:

- `list-events`
- `get-event`

#### DynamoDB Lookup Contract

- `get-event` uses DynamoDB `GetItem`
- the public identifier is translated into the canonical key:
  - `event_pk = EVENT#<event_id>`
- no `Scan`
- no `Query`
- no GSI access pattern

#### Not-Found Behavior

- `404` is returned only when the event item does not exist
- the response body is:
  - `{"message": "Event not found."}`

Cancelled and non-public events remain readable by ID. Returned items include
`status`.

### `update-event`

Routed API shape:

- `PATCH /events/{event_id}`

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
- `status`
- `created_by`
- `created_at`
- `rsvp_count`
- `attending_count`

`status` is a system-managed lifecycle field and must never be set directly by
clients.

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
- otherwise, top-level fields are treated as the update payload for direct
  invocation

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

- `caller.user_id`
- `caller.is_admin`

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

- if `capacity` is provided and is less than the current `attending_count`,
  reject with `400`
- the response should explain that capacity cannot be reduced below the current
  number of attending RSVPs

#### DynamoDB update strategy

The update path should use:

- `GetItem` first
- authorization and business validation against the current item
- compare requested mutable values against the current item
- `UpdateItem` second, only when at least one mutable value actually changes

The write should use a condition that the item still exists.

Valid update requests that do not change any mutable value should return `200`
with the current public event DTO, without writing to DynamoDB and without
publishing `event.updated`.

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

The returned `item` should use the same locked public event DTO already used
by:

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

#### Current implementation note

The deployed `update-event` Lambda now validates the currently locked partial
update contract in `dev`:

- creator may update their own event
- admin may update any event
- authenticated non-owner non-admin receives `403`
- direct invocation and API Gateway-style `body` JSON are both supported
- immutable and unknown fields are rejected with `400`
- `status` is rejected as immutable input
- `requires_admin = true` is restricted to admin callers
- `capacity` cannot be reduced below current `attending_count`
- conditional write protection (DynamoDB `ConditionExpression`) guards the
  capacity rule against concurrent changes
- conditional write failures are re-evaluated to return correct business errors
  instead of generic failures
- returned items use the locked public event DTO under `item`
- internal GSI helper fields remain hidden from the response
- valid no-op update requests return the current public event DTO without a
  DynamoDB update or EventBridge publication

#### Post-commit EventBridge publication

After successful durable event update, `update-event` publishes one
`event.updated` domain event to EventBridge.

The published detail is compact and notification-safe:

- `event_id`
- `title`
- `actor_user_id`
- `occurred_at`
- `event_detail_path`
- `changed_fields`

The event detail path uses:

- `/app/events/<event_id>`

`changed_fields` contains only mutable fields that actually changed.

`update-event` must not publish `event.updated` when:

- caller authentication is missing or invalid
- input validation fails
- the event does not exist
- the caller is not authorized
- the event is already `CANCELLED`
- the request contains no actual mutable value changes
- DynamoDB update does not durably succeed

EventBridge publication failure after durable update is logged, but it must not:

- change the successful `200` API response
- roll back the DynamoDB update
- turn the original API result into `500`

Lifecycle note:

- once effective status is `CANCELLED`, `update-event` must return `400`
- there is no reactivation path in this phase
- there are no metadata edits after cancellation in this phase

### `cancel-event`

Routed API shape:

- `POST /events/{event_id}/cancel`

#### Access rule

- event creator may cancel their own event
- admin may cancel any event

#### Naming direction

`cancel-event` is preferred over hard delete as the default operation because
it is safer, more realistic, and leaves room for history, notifications, and
later auditability.

#### Deletion model

`cancel-event` is a soft delete, not a hard delete.

- the event item remains in DynamoDB
- cancellation is represented as lifecycle state, not item removal

#### Lifecycle field

Canonical event records use:

- `status = ACTIVE | CANCELLED`

Rules:

- new events must be written with explicit `status = ACTIVE`
- `cancel-event` sets `status = CANCELLED`
- all canonical event records must include `status`
- missing `status` is invalid state and should not be relied on by handlers

#### Response contract

Successful cancel returns the standard API Gateway-style wrapper:

- `item`

The returned `item` uses the locked public event DTO, including:

- `status`

#### Idempotency

`cancel-event` is idempotent.

- if the event is already cancelled, return `200`
- repeated cancel attempts return the normal wrapped `item` response instead of
  an error

#### Post-commit EventBridge publication

After a successful durable `ACTIVE -> CANCELLED` state transition,
`cancel-event` publishes one `event.cancelled` domain event to EventBridge.

The published detail is compact and notification-safe:

- `event_id`
- `title`
- `actor_user_id`
- `occurred_at`
- `event_detail_path`

The event detail path uses:

- `/app/events/<event_id>`

`cancel-event` must not publish `event.cancelled` when:

- input validation fails
- the event does not exist
- the caller is not authorized
- the event was already `CANCELLED` before the update
- a conditional write failure re-read shows the event is already `CANCELLED`
- DynamoDB cancellation does not durably succeed

EventBridge publish failure after durable cancellation is logged, but it must
not:

- change the successful `200` API response
- roll back the DynamoDB cancellation
- turn the original API result into `500`

#### GSI behavior

On cancel:

- remove `public_upcoming_gsi_pk`
- remove `public_upcoming_gsi_sk`
- keep `creator_events_gsi_pk`
- keep `creator_events_gsi_sk`

This removes cancelled events from public discovery while preserving
creator/admin visibility.

#### Write model

The cancel flow should use:

1. `GetItem`
2. if missing, return `404`
3. authorize caller
4. if already cancelled, return `200`
5. otherwise `UpdateItem`

Recommended condition:

- `attribute_exists(event_pk) AND #status = :active`

If the conditional write fails:

- re-read item
- if missing, return `404`
- if now cancelled, return `200`
- otherwise return `500`

This keeps the mutation retry-safe and translates conditional-write outcomes
back into the correct business result.

#### Interaction with other handlers

- `get-event` still returns cancelled events by ID
- `list-my-events` includes cancelled events
- `list-events` must filter cancelled events during the current scan-based
  phase
- long-term `list-events` behavior should rely on index-based access patterns
  instead of scan filtering
- `update-event` is blocked once an event is cancelled
- there is no reactivation path in this phase

#### Past events versus cancelled events

Past events are not the same as cancelled events.

- past/outdated is derived from `date`
- cancelled is an explicit stored lifecycle state
- past events should not be auto-cancelled
- no extra lifecycle state such as `COMPLETED` is introduced in this step

Future RSVP behavior should reject:

- cancelled events
- past events

---

## RSVP Behavior Contracts

### `rsvp`

RSVP authorization depends on event type.

- public event:
  - anonymous RSVP allowed
  - authenticated RSVP allowed
- protected event:
  - authenticated user required
- admin event:
  - admin user required

This decision remains business-driven inside Lambda even after API Gateway and
Cognito handle generic auth.

#### Mixed-mode route direction

`rsvp` remains one mixed-mode business route.

Rules:

- anonymous RSVP must remain supported for public events
- authenticated RSVP must remain supported for public events
- protected-event RSVP requires authenticated caller context
- admin-event RSVP requires authenticated admin caller context
- authenticated callers on public events must not be collapsed into anonymous
  callers

The dedicated `rsvp` Lambda authorizer exists to preserve this mixed-mode
behavior while keeping JWT parsing and validation out of the business handler.

Current routed direction:

- the real mixed-mode route is:
  - `POST /events/{event_id}/rsvp`
- it is wired through API Gateway using the dedicated Lambda request authorizer
- the business Lambda consumes normalized caller context only
- the business Lambda must not parse raw authorizer payloads directly

#### Mixed-mode authorizer behavior

The dedicated `rsvp` Lambda authorizer must support both anonymous and
authenticated callers on the same route.

Rules:

- if no bearer token is present:
  - allow anonymous route access
  - project anonymous caller context
- if a valid Cognito token is present:
  - allow authenticated route access
  - project authenticated caller context
- if a malformed or invalid token is present:
  - deny the request at the API edge
  - the observed result is `403`
  - the business `rsvp` Lambda must not run
- the projected authorizer context is observed downstream under:
  - `requestContext.authorizer.lambda`

Locked v1 projected caller fields are:

- `user_id`
- `is_authenticated`
- `is_admin`

Observed downstream shape for successful mixed-mode requests:

- anonymous:
  - `requestContext.authorizer.lambda.user_id = null`
  - `requestContext.authorizer.lambda.is_authenticated = false`
  - `requestContext.authorizer.lambda.is_admin = false`
- authenticated non-admin:
  - `requestContext.authorizer.lambda.user_id = <Cognito sub>`
  - `requestContext.authorizer.lambda.is_authenticated = true`
  - `requestContext.authorizer.lambda.is_admin = false`
- authenticated admin:
  - `requestContext.authorizer.lambda.user_id = <Cognito sub>`
  - `requestContext.authorizer.lambda.is_authenticated = true`
  - `requestContext.authorizer.lambda.is_admin = true`

Observed typing:

- `is_authenticated` arrives as a real boolean
- `is_admin` arrives as a real boolean
- anonymous `user_id` arrives as `null`

#### Vendored dependency direction for the mixed-mode authorizer

The dedicated `rsvp` Lambda authorizer uses a vendored JWT verification stack.

Locked v1 dependency direction:

- `PyJWT`
- `cryptography`

Vendored dependencies live under:

- `lambdas/rsvp_authorizer/vendor/`

Packaging direction:

- `scripts/package_lambda.py --vendor-dir ...`
- vendored dependency contents must land at the ZIP archive root so the
  authorizer can import them directly

Build target direction:

- the vendor tree must be built for the deployed Lambda runtime and
  architecture
- current locked build target:
  - Python `3.13`
  - `x86_64`

Repository-scoping rule:

- the vendor tree is workload-local to `rsvp_authorizer`
- it must not become a shared repo-wide dependency bucket
- this step does not introduce a Lambda layer

#### Anonymous subject strategy

Anonymous RSVP is supported only for public events.

For anonymous RSVP in this phase, the caller must provide:

- `anonymous_token`

Rules:

- `anonymous_token` is required for anonymous RSVP
- trim leading and trailing whitespace before validation and storage
- reject if empty after trim
- store the trimmed value
- build the canonical anonymous subject key from the trimmed token
- authenticated callers must not send `anonymous_token`
- protected and admin-only events reject anonymous callers before token
  handling matters

#### Canonical RSVP key shape

The canonical RSVP storage shape is:

- partition key:
  - `event_pk = EVENT#<event_id>`
- sort key:
  - authenticated subject:
    - `subject_sk = USER#<user_id>`
  - anonymous subject:
    - `subject_sk = ANON#<anonymous_token>`

Canonical RSVP items should stay minimal and currently include:

- `event_pk`
- `subject_sk`
- `attending`
- `created_at`
- `updated_at`
- `subject_type`
- `user_id` for authenticated subjects
- `anonymous_token` for anonymous subjects

No speculative metadata should be added beyond what the current handler needs.

#### Lifecycle and time gating

RSVP must reject:

- missing event with `404`
- cancelled event with `400`
- past event with `400`

Locked messages:

- `Event not found.`
- `Cancelled events cannot accept RSVPs.`
- `Past events cannot accept RSVPs.`

Past-event evaluation uses the stored event date compared against current UTC
time.

Rules:

- if `event.date <= now`, reject RSVP
- stored `event.date` is expected to be a valid canonical ISO 8601 UTC
  timestamp
- if stored `event.date` cannot be parsed, return `500`

#### Write semantics

The write is an upsert per:

- `(event_id, subject)`

Locked behavior:

- no prior RSVP + `attending = true`:
  - create RSVP item
- no prior RSVP + `attending = false`:
  - create RSVP item
- prior RSVP exists with same `attending` value:
  - counters remain unchanged
  - preserve original `created_at`
  - update `updated_at`
  - return `200`
  - return `operation = "updated"`
- prior RSVP `true -> false`:
  - same item key is overwritten
  - counters update transactionally
- prior RSVP `false -> true`:
  - same item key is overwritten
  - counters update transactionally

Timestamp rules:

- on first create:
  - `created_at = now`
  - `updated_at = now`
- on overwrite or change:
  - preserve original `created_at`
  - set `updated_at = now`

#### Counter delta rules

The helper counters on the event item must remain transactionally correct:

- `rsvp_total`
- `attending_count`
- `not_attending_count`

Locked deltas:

- no previous RSVP -> new `attending = true`:
  - `rsvp_total +1`
  - `attending_count +1`
  - `not_attending_count +0`
- no previous RSVP -> new `attending = false`:
  - `rsvp_total +1`
  - `attending_count +0`
  - `not_attending_count +1`
- previous `attending = true` -> new `attending = true`:
  - all counters unchanged
- previous `attending = false` -> new `attending = false`:
  - all counters unchanged
- previous `attending = true` -> new `attending = false`:
  - `rsvp_total +0`
  - `attending_count -1`
  - `not_attending_count +1`
- previous `attending = false` -> new `attending = true`:
  - `rsvp_total +0`
  - `attending_count +1`
  - `not_attending_count -1`

#### Capacity handling

Capacity rules are:

- `capacity = null` means unlimited
- capacity applies only to `attending = true`
- `attending = false` is always allowed, even if the event is full
- first RSVP with `attending = true` must be rejected when
  `attending_count >= capacity`
- `false -> true` must be rejected when `attending_count >= capacity`
- same-value overwrite `true -> true` is allowed when already attending
  because it does not consume a new seat
- `true -> false` is always allowed
- first RSVP with `attending = false` is always allowed

Full-capacity rejection message:

- `Event is at full capacity.`

#### Concurrent final-slot contention

Concurrent seat consumption must be guarded transactionally.

Rules:

- if two callers compete for the final seat, only one may succeed
- the losing transaction must be translated into business `400`
- the event update inside the transaction must enforce capacity availability
  at write time

#### Transactional write model

The current RSVP business write must not be split into best-effort separate
writes.

Locked flow:

1. `GetItem` on `events`
2. validate existence, lifecycle, time, and access rules
3. `GetItem` on the existing RSVP item for the resolved subject
4. calculate counter deltas and capacity impact
5. perform one `TransactWriteItems` call across:
   - RSVP `Put`
   - event `Update`

The event update inside the transaction must:

- keep helper counters transactionally correct
- require `attribute_exists(event_pk)`
- require `status = ACTIVE`
- enforce capacity availability for seat-consuming writes

If the transaction fails, re-read the event item first and classify in this
order:

- event missing -> `404`
- event cancelled -> `400`
- event full for a seat-consuming write -> `400`
- otherwise unexpected failure -> `500`

Do not re-read the RSVP item unless a later implementation detail makes that
strictly necessary.

#### Request contract

Support both:

- direct invocation payload
- API Gateway-style body input

Resolved request inputs are:

- `event_id`
  - resolution order:
    1. `pathParameters.event_id`
    2. top-level `event_id`
- `attending`
  - required boolean
- `anonymous_token`
  - required only for anonymous RSVP
  - forbidden for authenticated RSVP

Caller context:

- `caller.user_id`
- `caller.is_authenticated`
- `caller.is_admin`

Anonymous is defined as:

- `caller.is_authenticated = false`

#### Response contract

The Lambda returns the standard API Gateway-style wrapper.

Successful response body shape:

- `item`
- `event_summary`
- `operation`

Successful RSVP `item` includes:

- `event_id`
- `subject`
- `attending`
- `created_at`
- `updated_at`

Successful `event_summary` includes:

- `status`
- `capacity`
- `rsvp_count`
- `attending_count`
- `not_attending_count`

Rules:

- `operation` is `created` or `updated`
- do not expose `subject_sk`
- do not expose raw DynamoDB keys
- do not expose GSI helper fields
- `not_attending_count` is allowed here even though it remains hidden from the
  public event DTO used by event-read handlers

Anonymous success uses:

- `subject.type = ANON`
- `subject.user_id = null`
- `subject.anonymous = true`

Authenticated success uses:

- `subject.type = USER`
- `subject.user_id = <caller.user_id>`
- `subject.anonymous = false`

#### Internal implementation notes for future async integration

The handler should internally distinguish:

- actor
- RSVP subject

The handler should also internally classify the change outcome, for example:

- created attending
- created not attending
- changed to attending
- changed to not attending
- unchanged attending
- unchanged not attending

This should support later domain-event publication without changing the current
API contract.

#### Status code contract

Locked status codes:

- `200` updated existing RSVP
- `201` created new RSVP
- `400` invalid input, cancelled event, past event, full capacity
- `403` authenticated caller lacks business permission for event type
- `404` event not found
- `500` unexpected internal/runtime/data issue

#### Current implementation note

The deployed `rsvp` Lambda now validates the locked RSVP write contract in
`dev`:

- direct and API Gateway-style request input are both supported
- the handler now consumes shared normalized caller context instead of parsing
  raw authorizer shapes locally
- public events allow anonymous and authenticated RSVP
- protected events require authentication
- admin-only events require an authenticated admin caller
- missing events return `404`
- cancelled events return `400`
- past events return `400`
- full-capacity attending writes return `400`
- same-subject overwrites preserve `created_at`, refresh `updated_at`, and
  keep counters stable when the RSVP value is unchanged
- RSVP writes are committed transactionally across the `events` and `rsvps`
  tables
- successful responses return the locked public RSVP contract:
  - `item`
  - `event_summary`
  - `operation`

Routed mixed-mode authorizer compatibility is now locked in the business
handler for:

- anonymous caller context delivered under:
  - `requestContext.authorizer.lambda`
- authenticated non-admin caller context delivered under:
  - `requestContext.authorizer.lambda`
- authenticated admin caller context delivered under:
  - `requestContext.authorizer.lambda`

End-to-end AWS validation for the routed `POST /events/{event_id}/rsvp` path
is now complete for this contract.

### `get-event-rsvps`

Routed API shape:

- `GET /events/{event_id}/rsvps`

The old monolith/OpenAPI contract exposed this broadly, but the current
platform deliberately narrows RSVP-read visibility to the operational users who
actually need subject-level attendee visibility.

#### Access rule

Allowed:

- event creator for their own event
- admin for any event

Rejected:

- anonymous caller
- authenticated non-owner non-admin caller

Unauthorized access returns `403`, not `404`, when the event exists.

#### Existence and authorization order

Use this exact order:

1. resolve and validate `event_id`
2. `GetItem` on `events`
3. if missing: `404`
4. if present but caller not allowed: `403`
5. if allowed: query `rsvps`

This keeps the handler operationally useful for creators and admin callers
while matching the current ownership/admin authorization direction used
elsewhere in the platform.

#### Authorization direction

Caller identity comes from normalized caller context:

- `caller.user_id`
- `caller.is_admin`

#### Lifecycle behavior

Readable:

- `ACTIVE`
- `CANCELLED`
- past events

This is a read/reporting operation, not a write path, so cancelled and past
events still expose RSVP lists to the creator and admins.

#### Request contract

Support both:

- direct invocation payload
- API Gateway-style `pathParameters` + `queryStringParameters`

Resolved inputs are:

- `event_id`
  - resolution order:
    1. `pathParameters.event_id`
    2. top-level `event_id`
- `limit`
  - resolution order:
    1. `queryStringParameters.limit`
    2. top-level `limit`
- `next_cursor`
  - resolution order:
    1. `queryStringParameters.next_cursor`
    2. top-level `next_cursor`

Validation rules:

- `event_id` is required
- `event_id` must be a trimmed non-empty string
- `event_id` must use the public identifier, not internal `EVENT#...` form
- `limit` is optional
- `next_cursor` is optional and must be an opaque string when provided

#### Pagination contract

Pagination is included now to avoid later contract churn on an event-scoped
query path.

Rules:

- default limit: `50`
- max limit: `100`
- `next_cursor` is an opaque string derived from DynamoDB `LastEvaluatedKey`
- the public contract must not expose raw DynamoDB key structure directly

Do not add filtering, sorting options, or attendee search in this phase.

#### Read model

Use this exact read model:

1. `GetItem` from `events`
2. authorize against that canonical event
3. `Query` `rsvps` where:
   - `event_pk = EVENT#<event_id>`
4. paginate using `ExclusiveStartKey`

Ascending default DynamoDB sort order is acceptable for now.

Do not add an RSVP GSI for this step. The existing RSVP table shape is already
efficient for per-event reads.

#### Stats source

Global RSVP stats come from the canonical event helper counters:

- `rsvp_total`
- `attending_count`
- `not_attending_count`

Do not recalculate totals from the queried page.

This keeps the read efficient and prevents page-local item counts from
masquerading as global event totals.

#### Empty RSVP behavior

An existing event with zero RSVPs returns:

- `200`
- `items: []`
- `stats.total = 0`
- `stats.attending = 0`
- `stats.not_attending = 0`
- `next_cursor = null`

This is not a not-found or special-case failure.

#### Response contract

The Lambda returns the standard API Gateway-style wrapper.

Success body shape:

- `event`
- `items`
- `stats`
- `next_cursor`

Locked `event` summary fields:

- `event_id`
- `status`
- `title`
- `date`
- `capacity`
- `created_by`
- `rsvp_count`
- `attending_count`

Each RSVP item includes:

- `subject`
- `attending`
- `created_at`
- `updated_at`

`subject` rules:

- authenticated RSVP:
  - `type = USER`
  - `user_id = <stored user_id>`
  - `anonymous = false`
- anonymous RSVP:
  - `type = ANON`
  - `user_id = null`
  - `anonymous = true`

`stats` includes:

- `total`
- `attending`
- `not_attending`

#### Hidden fields

Never expose:

- `subject_sk`
- `anonymous_token`
- `event_pk`
- raw DynamoDB keys
- helper GSI attributes
- internal storage-only fields

#### Status code contract

Locked status codes:

- `200` success
- `400` invalid input
- `403` caller is not allowed to view RSVP subjects for the event
- `404` event not found
- `500` unexpected internal/runtime/data issue

#### Current implementation note

The deployed `get-event-rsvps` Lambda now validates the locked RSVP read
contract in `dev`:

- direct invocation and API Gateway-style request input are both supported
- event creator can read RSVP subjects for their own events
- admin can read RSVP subjects for any event
- anonymous callers return `403`
- authenticated non-owner non-admin callers return `403`
- missing events return `404`
- existing events with zero RSVPs return `200` with empty `items`
- cancelled events remain readable to the creator and admins
- past events remain readable to the creator and admins
- response bodies return the locked public RSVP read contract:
  - `event`
  - `items`
  - `stats`
  - `next_cursor`
- internal storage fields remain hidden from the response
- pagination uses opaque `next_cursor`

---

## Post-Commit Async Notification Direction

The platform uses a transactional core with asynchronous notification
extensions.

The core synchronous business path remains:

`Client -> CloudFront -> API Gateway -> Lambda -> DynamoDB`

Asynchronous notification work must be added only after durable business state
changes. It must not become part of the user-facing success or failure outcome
for the primary API request.

### Core async publication rules

Write Lambdas publish compact domain events to EventBridge only after the
primary DynamoDB business write succeeds.

Locked rules:

- the durable DynamoDB business write must complete first
- EventBridge publication must happen only after successful durable commit
- each successful business change publishes exactly one EventBridge domain event
- write Lambdas must not publish separate events for separate downstream
  notification targets
- EventBridge owns fanout to downstream notification targets
- async publication or downstream delivery failure must not change the
  synchronous API response
- API responses must remain independent from EventBridge, SNS, SQS, worker
  Lambdas, SES, and future notification integrations
- publication failures should be logged, but they must not retroactively turn a
  successful business write into an API failure

This direction applies first to these write operations:

- `create-event`
- `update-event`
- `cancel-event`

RSVP notification events are intentionally deferred.

### Published v1 domain events

The v1 event-management notification domain events are:

- `event.created`
- `event.updated`
- `event.cancelled`

These events represent successful event-management business changes, not
delivery requests for a specific notification target.

### Domain event payload contract

EventBridge domain event payloads should remain compact and
notification-safe.

Allowed notification-safe v1 fields:

- `event_id`
- `title`
- `actor_user_id`
- `occurred_at`
- `event_detail_path`

For `event.updated`, also include:

- `changed_fields`

The frontend event detail path is:

- `/app/events/<event_id>`

Domain events must not include:

- email addresses
- anonymous RSVP tokens
- raw DynamoDB keys
- full RSVP lists
- JWT claims
- full before/after DynamoDB item snapshots

This keeps EventBridge payloads useful for notification routing while avoiding
unnecessary personal data spread and storage-model leakage.

### Admin notification path

Admin notifications use direct EventBridge-to-SNS fanout.

For:

- `event.created`
- `event.updated`
- `event.cancelled`

Locked flow:

`Write Lambda -> DynamoDB commit -> EventBridge -> SNS admin topic`

Rules:

- admin notifications are platform/admin broadcast notifications
- the admin path uses SNS directly
- no SQS worker is required for admin notifications in v1
- no Cognito admin-group lookup is required for admin notifications in v1
- the SNS topic supports confirmed admin or dev email subscriptions, but
  personal email addresses must not be hardcoded into reusable modules or
  committed environment configuration
- dev admin email subscriptions are configured through local untracked tfvars
- EventBridge target input transformers may format direct SNS admin messages
  with environment-specific presentation details such as a full browser URL
- exact direct SNS email rendering is not a business contract; polished admin
  email formatting can be introduced later through a dedicated formatter if
  needed

Admin notification messages should be able to include:

- event title
- event type
- actor user id
- full event link derived from the published `event_detail_path`
- changed fields for `event.updated`

For `event.created` and `event.cancelled`, admin notification messages should
not include an empty or irrelevant `changed_fields` line.

### Participant notification path

Participant notifications are event-specific email notifications for users who
already have authenticated RSVP records for an event.

For:

- `event.updated`
- `event.cancelled`

Locked flow:

`Write Lambda -> DynamoDB commit -> EventBridge -> notification-dispatch SQS -> notification-planner Lambda -> notification-email SQS -> notification-sender Lambda -> SES`

Rules:

- participant notifications use the two-queue/two-worker design
- the existing `notification-dispatch` queue is the event-level planning queue
- `notification-email` is the recipient-level user-facing email work queue
  between the planner and sender
- `notification-planner` is implemented and deployed in the current
  infrastructure baseline
- `notification-sender` is implemented and deployed in the current
  infrastructure baseline
- the planner and sender have separate least-privilege IAM roles and SQS event
  source mappings with partial batch responses
- participant email delivery uses a Terraform-managed SES sender identity and
  SES templates
- SQS provides durable buffering, retry isolation, and rate/concurrency control
- one event-level message can produce many recipient-level messages
- each recipient-level message represents one authenticated RSVP user recipient
- one worker must not query all recipients and send all emails in the same
  invocation

Participant emails are user-facing product emails, not admin/debug messages.
The planner produces safe recipient-level jobs, and the sender owns final
presentation through stable templates. EventBridge does not send directly to
`notification-email`.

The notification worker layer is implemented for update and cancellation
participant emails. The planner creates recipient-level jobs, and the sender
resolves the current recipient email through Cognito before sending a
Terraform-managed SES template.

Participant notification emails include template support for:

- event title
- event detail link
- changed fields for `event.updated`
- cancellation or update wording based on the event type

### SES participant email baseline

The current infrastructure baseline uses Amazon SES for participant email
identity and template management.

Rules:

- the sender identity is a dedicated project inbox
- the sender identity is configured through local untracked `terraform.tfvars`
- private personal email addresses must not be used as the project sender
- Terraform creates the SES email identity
- SES sender identity verification is manual through the dedicated project
  inbox
- Terraform manages SES templates for:
  - `event.updated`
  - `event.cancelled`
- SES templates contain the subject, plain-text body, and HTML body
- `notification-sender` uses `ses:SendTemplatedEmail`
- sender IAM allows SES templated sending for the configured sender identity,
  participant templates, and SES recipient identity scope required by sandbox
  validation
- SES sandbox assumptions remain explicit in `dev`
- sandbox email delivery requires verified recipient email addresses

This baseline does not request SES production access and does not configure a
domain identity, DKIM, SPF, DMARC, or custom MAIL FROM.

### Participant recipient rules

For `event.updated` and `event.cancelled`, participant recipients are:

- authenticated RSVP users for the event
- RSVP users with `attending = true`
- RSVP users with `attending = false`

Skipped in v1:

- anonymous RSVP subjects

Reason:

- the current anonymous RSVP model stores an anonymous token, not a verified
  email address

### RSVP identity and contact-data rule

Do not store user email addresses in RSVP records.

Locked rules:

- RSVP records remain business membership records
- RSVP records keep Cognito `sub` as the canonical `user_id`
- participant recipient messages contain `recipient_user_id`, not email
- `notification-sender` resolves the current email address at send time through
  Cognito
- username and email must not become internal platform identity keys

This avoids stale RSVP email data when a user changes email in Cognito and
avoids spreading personal contact data into RSVP business rows.

### `notification-planner`

The `notification-planner` Lambda consumes event-level messages from
`notification-dispatch` and enqueues recipient-level jobs to
`notification-email`.

The planner IAM role allows it to consume `notification-dispatch`, query RSVP
records, and send recipient-level jobs to `notification-email`.

Responsibilities:

- parse EventBridge-routed SQS messages for `event.updated` and
  `event.cancelled`
- query the RSVP table by `event_id`
- select authenticated RSVP subjects
- include both `attending = true` and `attending = false`
- skip anonymous RSVP subjects
- enqueue one recipient-level message per authenticated RSVP user to
  `notification-email`
- use partial batch responses so successful SQS records are not retried when
  another record in the same batch fails

Non-responsibilities:

- do not send email
- do not call SES
- do not resolve recipient email addresses
- do not require email stored in RSVP records

### `notification-sender`

The `notification-sender` Lambda consumes recipient-level messages from
`notification-email` and sends participant emails through SES.

The sender IAM role allows it to consume `notification-email`, call
`cognito-idp:ListUsers` against the configured Cognito user pool, and call
`ses:SendTemplatedEmail` for the configured sender address and participant
templates. The Cognito lookup uses a constrained `ListUsers` lookup by
canonical `sub`, because participant recipient messages carry
`recipient_user_id` as the Cognito `sub`.

Responsibilities:

- resolve the current recipient email address from Cognito at send time using
  the canonical `recipient_user_id`
- select the correct SES template for the notification type
- build validated template data with separate text-safe and HTML-safe fields
  for SES
- send templated email through SES `SendTemplatedEmail`
- use partial batch responses so successful SQS records are not retried when
  another record in the same batch fails

Non-responsibilities:

- do not query the RSVP table
- do not call EventBridge
- do not depend on RSVP-stored email addresses
- do not send raw EventBridge, SQS, or DynamoDB payloads to participants
- do not treat stale copied email data as the source of truth

### Intentionally deferred notification scope

The following are intentionally deferred:

- RSVP-created notifications
- RSVP-updated notifications
- per-event SNS topics
- subscribe-to-event-notifications feature
- notification preferences
- anonymous RSVP email collection
- SES production access request
- domain identity, DKIM, SPF, DMARC, or custom MAIL FROM
- Step Functions
- EventBridge Pipes
- deployed AWS notification tests in CI


These features should be introduced only when their behavior is explicitly
locked in a future implementation step.
