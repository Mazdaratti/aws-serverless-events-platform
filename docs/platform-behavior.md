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
[project-setup.md](project-setup.md),
[frontend/README.md](../frontend/README.md), and the relevant infrastructure
documentation.

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
frontend does not depend on cross-origin API requests.

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

### Frontend Authentication Behavior

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

### Frontend Request-Shape Contract

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

### Frontend Response-Consumption Contract

The frontend must consume the backend response contracts exposed by the routed
API.

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

This preserves the backend/frontend responsibility split defined by the event
DTO contract.

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

### Frontend Non-Responsibilities

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

Sign-in is Cognito-managed. The sign-in contract uses:

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

The authorizer configuration uses:

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

#### Post-Commit EventBridge Publication

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

#### Request Contract

Support both:

- direct invocation payload
- API Gateway-style `queryStringParameters`

Supported request parameters:

- `limit`
- `next_cursor`

#### Response Contract

The Lambda returns an API Gateway-style wrapped response.

The response body shape is:

- `items`
- `next_cursor`

#### Event DTO Contract

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

#### Request Contract

Support both:

- direct invocation payload
- API Gateway-style `queryStringParameters`

Supported request parameters:

- `limit`
- `next_cursor`

#### Caller Context

Caller identity comes from:

- `caller.user_id`

#### Response Contract

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

#### Request Contract

Support both:

- direct invocation payload
- API Gateway-style `pathParameters`

Supported request input:

- `event_id`

Resolution order:

1. `pathParameters.event_id`
2. top-level `event_id`

#### Input Validation Contract

- `event_id` is required
- `event_id` must be a non-empty string after trimming
- clients must pass the public identifier only
- clients must not pass the internal storage key form `EVENT#...`

#### Response Contract

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

Route:

- `PATCH /events/{event_id}`

#### Access Rule

- event creator may update their own event
- admin may update any event

#### Operation Model

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

#### Request Contract

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

#### Payload Rules

- the payload must contain at least one mutable field
- only supported mutable fields may be sent
- unknown fields are rejected
- immutable fields are rejected, not silently ignored

#### Input Validation Contract

- `event_id` is required
- `event_id` must be a non-empty string after trimming
- clients must pass the public identifier only
- clients must not pass the internal storage key form `EVENT#...`
- if `body` is present but is not valid JSON, return `400`
- if `body` decodes to anything other than an object, return `400`
- if no mutable fields are provided, return `400`
- if unknown fields are present, return `400`
- if immutable fields are present, return `400`

#### Authorization Behavior

Caller identity comes from:

- `caller.user_id`
- `caller.is_admin`

- creator may update their own event
- admin may update any event
- all other authenticated callers receive `403`

#### Existence and Authorization Order

`update-event` evaluates the current item in this order:

1. read the event
2. if it does not exist, return `404`
3. if it exists but the caller is not allowed, return `403`
4. if allowed, continue to validation and update

This operation does not mask unauthorized update attempts as `404`.

#### Field Validation

Field-level validation reuses the `create-event` business rules where
applicable.

- only admin may set `requires_admin = true`

Capacity safety rule:

- if `capacity` is provided and is less than the current `attending_count`,
  reject with `400`
- the response explains that capacity cannot be reduced below the current
  number of attending RSVPs

#### DynamoDB Write Model

The update path uses:

- `GetItem` first
- authorization and business validation against the current item
- compare requested mutable values against the current item
- `UpdateItem` second, only when at least one mutable value actually changes

The write condition requires the item to still exist. Capacity changes are also
protected by a condition so concurrent RSVP activity cannot reduce capacity
below the effective attending count.

Conditional write failures are re-evaluated and translated into the appropriate
business error.

Valid update requests that do not change any mutable value should return `200`
with the current public event DTO, without writing to DynamoDB and without
publishing `event.updated`.

#### GSI Maintenance

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

#### Response Contract

`update-event` returns the standard API Gateway-style wrapper.

Success body shape:

- `item`

The returned `item` uses the same public event DTO as:

- `list-events`
- `get-event`

#### Error Contract

- `400` invalid input or business validation failure
- `401` missing or invalid authentication rejected at the API edge
- `403` authenticated caller is not allowed to update the event
- `404` event not found
- `500` internal/runtime/data issue

#### Post-Commit EventBridge Publication

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

#### Lifecycle Boundary

- once effective status is `CANCELLED`, `update-event` returns `400`
- cancelled events cannot be reactivated
- event metadata cannot be edited after cancellation

### `cancel-event`

Route:

- `POST /events/{event_id}/cancel`

#### Access Rule

- event creator may cancel their own event
- admin may cancel any event

#### Lifecycle Model

`cancel-event` is a soft delete, not a hard delete.

- the event item remains in DynamoDB
- cancellation is represented as lifecycle state, not item removal
- new events must be written with explicit `status = ACTIVE`
- `cancel-event` sets `status = CANCELLED`
- all canonical event records must include `status`
- missing `status` is invalid state and should not be relied on by handlers

#### Response Contract

Successful cancel returns the standard API Gateway-style wrapper:

- `item`

The returned `item` uses the public event DTO, including:

- `status`

#### Idempotency

`cancel-event` is idempotent.

- if the event is already cancelled, return `200`
- repeated cancel attempts return the normal wrapped `item` response instead of
  an error

#### Post-Commit EventBridge Publication

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

#### GSI Behavior

On cancel:

- remove `public_upcoming_gsi_pk`
- remove `public_upcoming_gsi_sk`
- keep `creator_events_gsi_pk`
- keep `creator_events_gsi_sk`

This removes cancelled events from public discovery while preserving
creator/admin visibility.

#### DynamoDB Write Model

The cancel flow uses:

1. `GetItem`
2. if missing, return `404`
3. authorize caller
4. if already cancelled, return `200`
5. otherwise `UpdateItem`

Write condition:

- `attribute_exists(event_pk) AND #status = :active`

If the conditional write fails:

- re-read item
- if missing, return `404`
- if now cancelled, return `200`
- otherwise return `500`

This keeps the mutation retry-safe and translates conditional-write outcomes
back into the correct business result.

#### Interaction with Other Handlers

- `get-event` still returns cancelled events by ID
- `list-my-events` includes cancelled events
- `list-events` filters cancelled events from its scan result
- `update-event` is blocked once an event is cancelled
- cancelled events cannot be reactivated

#### Past Events Versus Cancelled Events

Past events are not the same as cancelled events.

- past/outdated is derived from `date`
- cancelled is an explicit stored lifecycle state
- past events are not automatically cancelled
- no additional lifecycle state such as `COMPLETED` exists

RSVP writes reject:

- cancelled events
- past events

---

## RSVP Behavior Contracts

### `rsvp`

Route:

- `POST /events/{event_id}/rsvp`

#### Access Behavior

| Event type | Allowed callers |
|---|---|
| Public | Anonymous and authenticated callers |
| Protected | Authenticated callers |
| Admin-only | Authenticated admin callers |

The dedicated Lambda authorizer preserves optional authentication at the API
edge. The business Lambda consumes normalized caller context and decides
whether that caller may RSVP to the selected event.

Malformed or invalid presented authentication is rejected by the authorizer
with `403`; the business Lambda is not invoked. Detailed authorizer behavior is
defined in [Mixed-Mode RSVP Authorizer](#mixed-mode-rsvp-authorizer).

Authorizer dependency and packaging operations are documented in
[lambdas/README.md](../lambdas/README.md).

#### Anonymous Subject Identity

Anonymous RSVP is supported only for public events.

Anonymous callers must provide:

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

#### Canonical RSVP Identity

The canonical storage identity is:

- partition key:
  - `event_pk = EVENT#<event_id>`
- sort key:
  - authenticated subject:
    - `subject_sk = USER#<user_id>`
  - anonymous subject:
    - `subject_sk = ANON#<anonymous_token>`

Canonical RSVP items include:

- `event_pk`
- `subject_sk`
- `attending`
- `created_at`
- `updated_at`
- `subject_type`
- `user_id` for authenticated subjects
- `anonymous_token` for anonymous subjects

#### Lifecycle and Time Gating

RSVP must reject:

- missing event with `404`
- cancelled event with `400`
- past event with `400`

Response messages:

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

#### Write Semantics

The write is an upsert per:

- `(event_id, subject)`

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

#### Counter Deltas

The helper counters on the event item must remain transactionally correct:

- `rsvp_total`
- `attending_count`
- `not_attending_count`

| Previous RSVP | New RSVP | `rsvp_total` | `attending_count` | `not_attending_count` |
|---|---|---:|---:|---:|
| None | Attending | +1 | +1 | 0 |
| None | Not attending | +1 | 0 | +1 |
| Attending | Attending | 0 | 0 | 0 |
| Not attending | Not attending | 0 | 0 | 0 |
| Attending | Not attending | 0 | -1 | +1 |
| Not attending | Attending | 0 | +1 | -1 |

#### Capacity Handling

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

#### Concurrent Final-Slot Contention

Concurrent seat consumption must be guarded transactionally.

Rules:

- if two callers compete for the final seat, only one may succeed
- the losing transaction must be translated into business `400`
- the event update inside the transaction must enforce capacity availability
  at write time

#### Transactional Write Model

The RSVP business write must not be split into best-effort separate writes.

Write flow:

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

#### Request Contract

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

#### Response Contract

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

#### Status Code Contract

- `200` updated existing RSVP
- `201` created new RSVP
- `400` invalid input, cancelled event, past event, full capacity
- `403` authenticated caller lacks business permission for event type
- `404` event not found
- `500` unexpected internal/runtime/data issue

Deployment wiring and AWS validation evidence are documented in the
[development environment README](../infrastructure/envs/dev/README.md).

### `get-event-rsvps`

Route:

- `GET /events/{event_id}/rsvps`

#### Access Rule

Allowed:

- event creator for their own event
- admin for any event

Rejected:

- anonymous caller
- authenticated non-owner non-admin caller

Unauthorized access returns `403`, not `404`, when the event exists.

#### Existence and Authorization Order

The handler evaluates the request in this order:

1. resolve and validate `event_id`
2. `GetItem` on `events`
3. if missing: `404`
4. if present but caller not allowed: `403`
5. if allowed: query `rsvps`

Caller identity comes from normalized caller context:

- `caller.user_id`
- `caller.is_admin`

#### Lifecycle Behavior

Readable:

- `ACTIVE`
- `CANCELLED`
- past events

This is a read/reporting operation, not a write path, so cancelled and past
events still expose RSVP lists to the creator and admins.

#### Request Contract

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

#### Pagination Contract

- default limit: `50`
- max limit: `100`
- `next_cursor` is an opaque string derived from DynamoDB `LastEvaluatedKey`
- the public contract must not expose raw DynamoDB key structure directly

The endpoint does not support filtering, custom sorting, or attendee search.

#### Read Model

The read model is:

1. `GetItem` from `events`
2. authorize against that canonical event
3. `Query` `rsvps` where:
   - `event_pk = EVENT#<event_id>`
4. paginate using `ExclusiveStartKey`

The query uses the default ascending sort-key order. The existing primary key
supports event-scoped reads without an additional RSVP GSI.

#### Stats Source

Global RSVP stats come from the canonical event helper counters:

- `rsvp_total`
- `attending_count`
- `not_attending_count`

Do not recalculate totals from the queried page.

This keeps the read efficient and prevents page-local item counts from
masquerading as global event totals.

#### Empty RSVP Behavior

An existing event with zero RSVPs returns:

- `200`
- `items: []`
- `stats.total = 0`
- `stats.attending = 0`
- `stats.not_attending = 0`
- `next_cursor = null`

This is not a not-found or special-case failure.

#### Response Contract

The Lambda returns the standard API Gateway-style wrapper.

Success body shape:

- `event`
- `items`
- `stats`
- `next_cursor`

The `event` summary includes:

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

#### Hidden Fields

Never expose:

- `subject_sk`
- `anonymous_token`
- `event_pk`
- raw DynamoDB keys
- helper GSI attributes
- internal storage-only fields

#### Status Code Contract

- `200` success
- `400` invalid input
- `401` missing or invalid authentication rejected at the API edge
- `403` caller is not allowed to view RSVP subjects for the event
- `404` event not found
- `500` unexpected internal/runtime/data issue

Deployment wiring and AWS validation evidence are documented in the
[development environment README](../infrastructure/envs/dev/README.md).

---

## Post-Commit Notification Behavior

Notifications extend the transactional business flow after a durable change.
They do not determine the success or failure of the original API request.

Detailed service topology is documented in
[`architecture.md`](architecture.md). Concrete `dev` wiring, IAM, SES
configuration, and validation evidence are documented in
[`infrastructure/envs/dev/README.md`](../infrastructure/envs/dev/README.md).

### Publication Contract

Event-management write Lambdas publish a compact domain event only after the
corresponding DynamoDB write succeeds.

The publication contract is:

- the durable business write completes first
- each successful business change publishes one domain event
- EventBridge owns downstream routing and fanout
- write Lambdas do not publish target-specific notification messages
- publication or downstream delivery failure does not change the successful API
  response
- publication failures are logged without retroactively failing the committed
  business operation

This contract applies to:

- `create-event`
- `update-event`
- `cancel-event`

Changes to RSVP records do not currently publish notification events.

### Domain Event Contract

| Event type | Trigger | Current audiences |
|---|---|---|
| `event.created` | Successful event creation | Admin |
| `event.updated` | Successful event update | Admin and authenticated RSVP users |
| `event.cancelled` | Successful event cancellation | Admin and authenticated RSVP users |

Domain events describe completed business changes rather than delivery requests
for a specific notification channel.

Allowed notification-safe fields are:

- `event_id`
- `title`
- `actor_user_id`
- `occurred_at`
- `event_detail_path`
- `changed_fields` for `event.updated`

The event detail path uses:

```text
/app/events/<event_id>
```

Domain events must not contain:

- email addresses
- anonymous RSVP tokens
- raw DynamoDB keys
- full RSVP lists
- JWT claims
- complete before-and-after item snapshots

### Admin Notification Behavior

Admin notifications are lightweight platform broadcasts for:

- event creation
- event updates
- event cancellation

Messages may include:

- event title
- event type
- actor user ID
- the full event link derived from `event_detail_path`
- changed fields for event updates

Creation and cancellation messages do not include an empty
`changed_fields` value. Exact SNS email rendering is not a product contract.

### Participant Notification Behavior

Participant emails are sent for:

- `event.updated`
- `event.cancelled`

Eligible recipients are authenticated users with an RSVP record for the event.
Both `attending = true` and `attending = false` records are included.

Anonymous RSVP subjects are skipped because the anonymous RSVP model does not
collect a verified email address.

One event-level notification may expand into one recipient-level job per
eligible user. A failure for one recipient must not cause successfully
processed recipients from the same batch to be retried.

Participant emails support:

- event title
- event detail link
- changed fields for event updates
- notification-specific update or cancellation wording

Participant emails use stable templates and must not expose raw EventBridge,
SQS, DynamoDB, or internal storage payloads.

### Notification Worker Contracts

| Worker | Responsibilities | Explicit exclusions |
|---|---|---|
| `notification-planner` | Parse supported event notifications, query RSVP records, select authenticated recipients, and enqueue one recipient-level job per user | Does not resolve email addresses or send email |
| `notification-sender` | Resolve the current Cognito email, select the notification template, construct safe template data, and send the participant email | Does not query RSVP records or publish domain events |

Both workers use partial SQS batch responses so a failed record can be retried
without retrying successful records from the same batch.

### Identity and Privacy Boundary

Cognito `sub` remains the canonical authenticated user identifier.

The notification contract therefore requires:

- RSVP records store the canonical `user_id`, not a copied email address
- recipient-level jobs contain `recipient_user_id`, not email
- `notification-sender` resolves the current email from Cognito at send time
- username and email are not used as internal identity keys
- dynamic template values are validated and encoded for their text or HTML
  context

This avoids stale contact data in RSVP records and limits the spread of
personal information through asynchronous messages.

### Deferred Notification Behavior

The following behavior is not currently implemented:

- notifications triggered by RSVP creation or updates
- per-event notification subscriptions
- user notification preferences
- anonymous RSVP email collection
- participant delivery channels other than email
- deployed-environment notification integration tests in CI
