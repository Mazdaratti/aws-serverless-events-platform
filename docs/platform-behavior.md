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
- frontend and edge-delivery behavior
- auth versus business-authorization boundaries
- normalized caller-context rules
- Lambda implementation sequencing
- future post-commit async event direction

It should be updated when the platform's intended behavior changes in a
meaningful way.

---

## Frontend and Edge Delivery Behavior

The platform's frontend and edge-delivery direction is now locked strongly
enough that future frontend implementation should follow it.

This section defines the behavioral contract the future frontend app should use
when interacting with the already implemented backend.

### Public entry-point model

The intended public entry point for the product is one CloudFront distribution.

That distribution is expected to serve:

- static frontend assets from a private S3 bucket
- backend API requests using the existing routed API path shape

This means the long-term browser-visible product is intended to present one
origin for:

- static frontend assets
- backend API requests

The platform is intentionally not introducing a second browser-facing API path
contract such as `/api/*` in this phase.

Instead, the future edge layer should preserve the already implemented routed
backend path shape.

### Routed API path contract for the frontend

The frontend should follow the same route paths already implemented and
validated in the backend:

- `GET /events`
- `GET /events/mine`
- `GET /events/{event_id}`
- `POST /events`
- `PATCH /events/{event_id}`
- `POST /events/{event_id}/cancel`
- `POST /events/{event_id}/rsvp`
- `GET /events/{event_id}/rsvps`

This is the primary frontend integration direction for the product.

The frontend must be implemented assuming these route paths remain the
canonical public API shape.

### Current deployment-path note

The currently deployed direct API Gateway entry point still includes the stage
path for the active environment.

In `dev`, that means direct non-CloudFront API testing currently uses the
stage-qualified API Gateway invoke path shape, for example:

- `/dev/events`
- `/dev/events/mine`
- `/dev/events/{event_id}`

That stage-qualified execute-api URL is a deployment detail of the current
backend-only phase, not the intended long-term browser-facing product shape.

The future CloudFront layer should preserve the routed backend path contract
without forcing the frontend to adopt a separate translated API path family.

### Same-origin contract

The frontend should treat the backend API as same-origin application traffic in
the final edge-delivery model.

Rules:

- the frontend should call backend routes through relative paths such as:
  - `/events`
  - `/events/mine`
  - `/events/{event_id}`
- the frontend should not treat the raw API Gateway execute-api hostname as the
  normal browser-facing API base
- the frontend should not hardcode a direct API Gateway stage URL into normal
  application behavior
- the frontend should assume the final browser-visible product uses one origin
  for:
  - static frontend assets
  - backend API requests

### CORS direction

The reusable API Gateway module now supports optional CORS configuration, but
that is not the primary frontend integration strategy.

Locked direction:

- the preferred product path is same-origin browser access through CloudFront
- the frontend should not be designed around cross-origin browser calls to the
  raw API Gateway URL
- API Gateway CORS support remains an infrastructure capability for exceptional
  cases such as:
  - temporary direct API testing
  - alternate environment setups
  - future integration needs that genuinely require cross-origin behavior

So CORS readiness remains useful, but the frontend app contract is not based on
cross-origin API usage.

### Frontend authentication behavior

Frontend authentication remains Cognito-managed.

The frontend is responsible for:

- initiating sign-in and sign-out through the chosen frontend auth flow
- holding the authenticated session state needed for browser interaction
- attaching a bearer token for ordinary protected API requests
- omitting authentication when calling public routes
- preserving optional-auth behavior for the mixed-mode RSVP route

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

### Frontend timestamp behavior

Backend APIs return canonical timestamps as ISO 8601 UTC strings.

Locked frontend direction:

- the frontend is responsible for user-friendly timestamp rendering
- the frontend should convert backend UTC timestamps into readable UI text for
  people
- the frontend must not require the backend to pre-render presentation-specific
  date strings

This preserves the current backend/frontend responsibility split already used
by the event DTO contract.

### Frontend route-usage direction

The initial frontend should align with the currently implemented routed API
surface only.

Locked initial browser-facing API surface:

- `GET /events`
- `GET /events/mine`
- `GET /events/{event_id}`
- `POST /events`
- `PATCH /events/{event_id}`
- `POST /events/{event_id}/cancel`
- `POST /events/{event_id}/rsvp`
- `GET /events/{event_id}/rsvps`

The frontend must not assume unimplemented routes exist.

### Frontend error-handling direction

The frontend should respect the current routed API error semantics instead of
normalizing all failures into one generic UI state.

Important examples from the locked backend contract:

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

---

## Authentication Behavior

The platform uses **Amazon Cognito** as the sole identity provider.

Authentication is externalized from Lambda business logic, but the routed API
uses two authorizer modes:

- API Gateway native JWT authorizer for ordinary protected routes
- a dedicated custom Lambda authorizer for the mixed-mode `rsvp` route

Business Lambdas must consume one normalized caller contract regardless of
which upstream authorizer mode produced the request context.

### Responsibility Split

- Cognito is responsible for:
  - user registration
  - user login
  - token issuance
  - email verification
  - password reset and recovery
  - user group membership such as admin
- API Gateway is responsible for:
  - native JWT validation on ordinary protected routes
  - invoking the dedicated custom Lambda authorizer on the mixed-mode `rsvp` route
  - rejecting unauthorized requests before they reach business Lambdas
- shared request/auth normalization is responsible for:
  - reading the upstream authorizer context shape
  - supporting multiple upstream authorizer context shapes
  - mapping authenticated identity into the normalized internal caller shape
- business Lambda functions:
  - must not validate JWTs
  - must not implement login or generic identity logic
  - must not scatter raw authorizer parsing throughout business logic
  - must rely on normalized caller context
  - must enforce only resource- and workflow-specific authorization
- the dedicated `rsvp` Lambda authorizer:
  - may validate a presented bearer token
  - may project normalized caller context for the `rsvp` business Lambda
  - is part of the platform auth layer, not business logic

### Request Identity Contract

Business Lambdas receive platform identity information via:

- `requestContext.authorizer`

The previous simplified direct platform-boundary assumption:

- `requestContext.authorizer.user_id`
- `requestContext.authorizer.is_admin`

is now deprecated as the raw platform-boundary truth.

The platform must support multiple upstream authorizer context shapes,
including:

- native JWT authorizer context
- custom Lambda authorizer context

For the mixed-mode RSVP route, the real routed HTTP API simple-response Lambda
authorizer shape observed in AWS is:

- `requestContext.authorizer.lambda`

Business Lambdas must not depend directly on those raw shapes. They must
consume normalized caller context produced by shared request/auth parsing
logic.

### Canonical Identity Rule

The canonical internal user identifier is:

- Cognito user `sub`

Locked raw identity sources:

- authenticated user identity comes from Cognito `sub`
- admin capability comes from Cognito group membership
- the locked admin group name is:
  - `admin`

This canonical identity must be used as:

- the internal user identifier
- the basis for ownership checks
- the key for user-scoped data such as authenticated RSVP subjects

Username and email must not be treated as internal platform identity keys.

### Admin Authorization Rule

Administrative privileges are derived from Cognito group membership.

Locked admin rule:

- `admin`

Normalized caller context must derive:

- `caller.is_admin = true` when Cognito groups include `admin`
- `caller.is_admin = false` otherwise

Business Lambdas must:

- trust normalized admin context
- not recompute admin status independently
- not rely on request payload fields for admin decisions

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

This normalized shape is the internal business-logic contract.

Anonymous caller definition:

- anonymous is not a Cognito-provided identity
- anonymous is derived when no authenticated caller context is present
- upstream authorizers must not fabricate anonymous identity values

### Mapping Helper Rule

Caller normalization must happen through shared request/auth parsing logic.

Rules:

- one shared helper normalizes caller context
- the helper must support:
  - native JWT-authorizer upstream context
  - custom Lambda-authorizer upstream context
  - synthetic direct-invocation test context
- handlers must resolve caller context once near the request edge
- downstream business logic must consume only normalized caller values

### Sign-In Behavior (v1)

- sign-in is Cognito-managed
- v1 uses username as the primary sign-in attribute
- email is required
- email verification is Cognito-managed

This does not lock the platform into permanent username-only login behavior.

### Explicit Non-Responsibilities of Business Lambdas

Business Lambda functions must not:

- parse or validate JWTs
- call Cognito to verify identity
- implement authentication flows
- infer identity from headers or request payload
- duplicate ad hoc authorizer parsing logic across handlers

All caller identity used by business Lambdas must come from:

- normalized caller context

### Route Authentication Modes

The platform uses three practical route modes.

#### Public read route

- route is publicly callable
- no authentication is required
- caller context may be anonymous

Current examples:

- `list-events`
- `get-event`

#### Mixed-mode route

- anonymous access is allowed
- authenticated access is also allowed
- authenticated callers must still be recognized as authenticated callers
- this route requires an upstream authorizer strategy that:
  - allows anonymous access
  - preserves authenticated caller identity when present

Current example:

- `rsvp`

#### Authenticated route

- route requires authenticated caller context
- ordinary protected routes use API Gateway native JWT authorization
- business Lambdas consume normalized caller context derived from the JWT
  authorizer input

Current examples:

- `create-event`
- `list-my-events`
- `update-event`
- `cancel-event`
- `get-event-rsvps`

### Ordinary Routed API Shape

The ordinary routed API shape for the currently implemented handlers is locked
as:

- `POST /events`
  - `create-event`
- `GET /events`
  - `list-events`
- `GET /events/mine`
  - `list-my-events`
- `GET /events/{event_id}`
  - `get-event`
- `PATCH /events/{event_id}`
  - `update-event`
- `POST /events/{event_id}/cancel`
  - `cancel-event`
- `GET /events/{event_id}/rsvps`
  - `get-event-rsvps`

The mixed-mode RSVP route is locked as:

- `POST /events/{event_id}/rsvp`
  - `rsvp`

#### Mixed-mode RSVP authorizer constraint

The mixed-mode `rsvp` authorizer must not require anonymous callers to present
an `Authorization` header before the authorizer is invoked.

Rules:

- anonymous public RSVP requests must still reach the authorizer path
- absence of `Authorization` must be interpreted as anonymous access, not as an
  automatic pre-Lambda `401`
- initial implementation should prefer correctness over caching complexity
- any future caching strategy must preserve mixed anonymous/authenticated route
  behavior

Current locked implementation rule for this mixed-mode route:

- request authorizer `identity_sources` must be omitted
- `enable_simple_responses` must remain enabled
- request authorizer result TTL must be `0`

This preserves the required mixed-mode behavior:

- no header -> anonymous allowed path can still reach the Lambda authorizer
- valid header -> authenticated path is preserved
- malformed or invalid presented auth is denied instead of silently downgraded
  to anonymous

The current routed implementation is intentionally locked to the HTTP API
Lambda request-authorizer simple-response path for this route.

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

Routed API shape:

- `POST /events`

#### Access rule

- authenticated users may create public events
- authenticated users may create protected events
- admin users may also create admin-only events

#### Ownership rule

- event ownership must be derived from caller identity
- `creator_id` should come from `caller.user_id`
- request-body `creator_id` must not be trusted as the source of ownership

#### Current implementation note

The deployed `create-event` Lambda now enforces the locked creation contract:

- authenticated-only event creation
- ownership derived from caller identity
- request-body `creator_id` ignored as an ownership source
- admin-only events restricted to admin callers
- new canonical event records must include `status = ACTIVE`
- returned event DTO must include `status`

### `list-events`

Routed API shape:

- `GET /events`

#### Access rule

- all users may use public broad event listing
- this is a public route
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

`list-events` should return a stable public event DTO instead of raw or
half-cleaned DynamoDB storage items.

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

#### Current implementation direction

- broad public listing currently uses a temporary table `Scan`
- pagination is required
- creator-scoped listing behavior no longer belongs to this handler
- the dedicated authenticated creator-scoped listing workload is:
  - `list-my-events`

This is an intentional tradeoff:

- broad listing preserves the current product direction
- long-term scan reduction remains desirable, but broad listing is currently an
  intentional platform behavior

#### Current implementation note

The deployed `list-events` Lambda now validates the currently locked read
contract in `dev`:

- broad public listing returns the current event collection
- returned items use the locked public event DTO
- request validation is intentionally limited to:
  - `limit`
  - `next_cursor`
- the current broad public route filters cancelled events
- due to the temporary scan-based access path, non-public and past events may still appear in this phase

Lifecycle note:

- during the current temporary scan-based phase, `list-events` must filter out
  cancelled events in Lambda
- long-term behavior will rely on index-based access patterns instead of scan
  filtering
- `list-events` must expose `status` in the public DTO

### `list-my-events`

Routed API shape:

- `GET /events/mine`

#### Access rule

- authenticated users may list the events they created
- anonymous caller is not allowed
- missing authenticated caller context must not fall back to public behavior

#### Query direction

This operation is the dedicated creator-scoped listing workload and replaces
the previous creator-scoped behavior that was formerly part of `list-events`.

The route is intentionally split so:

- broad event discovery remains public
- creator-scoped event listing becomes a straightforward authenticated route
- API Gateway can enforce authentication at the route level instead of relying
  on mode-specific business gating for one listing route

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

The returned items use the same locked public event DTO as:

- `list-events`
- `get-event`

#### Current implementation direction

- `list-my-events` now uses the `creator-events` GSI
- pagination is required

#### Lifecycle visibility

Visible in this route:

- `ACTIVE`
- `CANCELLED`
- past events

Past events remain visible unless a later product behavior explicitly changes
that rule.

#### Status direction

`list-my-events` must expose `status` in the public event DTO.

#### Current implementation note

The deployed `list-my-events` Lambda now validates the currently locked
creator-scoped read contract in `dev`:

- anonymous requests are rejected at the API edge for this route
- authenticated creator-scoped listing succeeds through the dedicated routed path
- returned items use the same locked public event DTO as:
  - `list-events`
  - `get-event`
- request validation is limited to:
  - `limit`
  - `next_cursor`
- the current access path uses the `creator-events` GSI
- creator-scoped results include:
  - `ACTIVE`
  - `CANCELLED`
  - past events

### `get-event`

Routed API shape:

- `GET /events/{event_id}`

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
- API Gateway-routed public single-item reads now succeed in `dev`
- API Gateway-style `pathParameters.event_id` is supported
- missing items return `404`
- returned items use the locked public event DTO under `item`

Lifecycle note:

- `get-event` still returns cancelled events by ID
- `get-event` still returns non-public events by ID
- returned items must expose `status` in the public DTO

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

## Post-Commit Async Direction

Write Lambdas should remain easy to extend with post-commit domain event
publication to EventBridge.

This direction applies to write operations such as:

- `create-event`
- `update-event`
- `cancel-event`
- `rsvp`
- future write workloads

Locked rules:

- the primary business write must complete durably first
- any future EventBridge publication must happen only after successful
  business commit
- downstream async publication failure must not retroactively change the
  primary synchronous business result
- adding EventBridge later must not require redesigning the current
  synchronous request/response contract

Implementation direction:

- write handlers should preserve enough internal change classification to
  support future domain-event emission
- write handlers should distinguish actor, affected resource, and resulting
  change type clearly enough for later async publication
- async integration must remain additive to the current synchronous business
  path

---

## Lambda Implementation Status

The currently locked Lambda set and rollout status are:

1. `create-event` ✅
2. `list-events` ✅
3. `list-my-events` ✅
4. `get-event` ✅
5. `update-event` ✅
6. `cancel-event` ✅
7. `rsvp` ✅
8. `get-event-rsvps` ✅
9. `notification-worker`

This sequence remains intentional:

- first create and read basics
- then split broad and creator-scoped event listing clearly
- then ownership-based event management
- then transactional RSVP complexity
- then RSVP read/reporting
- then asynchronous side effects

---

## Current Open Questions

The following behaviors are intentionally not fully locked yet:

- exact account-deletion cleanup semantics

These should be decided in the implementation steps where they become
immediately relevant.
