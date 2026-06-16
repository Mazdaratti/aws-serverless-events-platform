# Architecture Overview

The AWS Serverless Events Platform is a fully managed, cloud-native web
application built on AWS serverless services.

This document owns the detailed platform architecture, service responsibilities,
and system boundaries. Product and authorization contracts are documented in
[platform-behavior.md](platform-behavior.md); operational setup and deployment
procedures are documented in [project-setup.md](project-setup.md); concrete
`dev` Terraform composition is documented in the
[development environment README](../infrastructure/envs/dev/README.md).

The deployed architecture follows a **transactional core with event-driven
extensions**:

- business-critical API operations execute synchronously and commit durably to
  DynamoDB
- asynchronous services provide post-commit fanout, buffering, retries, and
  notification delivery

This preserves immediate business outcomes while isolating downstream work from
the synchronous request path.

## Edge Layer (Global Entry Point)

User traffic enters the system through:

- **Amazon CloudFront** for global content delivery
- **AWS Shield Standard** for automatic DDoS mitigation
- optional **AWS WAF** protection when enabled for the environment

CloudFront serves static frontend assets from a private:

- **Amazon S3**

When enabled, WAF applies:

- AWS Managed Rule Sets
- IP-based rate limiting

WAF is disabled by default in `dev` to avoid steady non-production cost.
CloudFront remains the public browser entry point regardless of the WAF setting.

### Edge Delivery Model

The deployed edge layer uses one CloudFront distribution as the public entry
point for browser traffic.

The distribution:

- serves static frontend assets from a private S3 bucket
- forwards backend API requests to API Gateway
- attaches WAF protection when enabled
- enforces HTTPS-only browser access
- provides CDN caching for static frontend assets

This keeps the platform aligned with a production-style edge model:

- S3 stores static frontend assets
- CloudFront is the public browser-facing layer
- WAF protects public traffic before requests reach platform origins

### Frontend Routing Namespace

The platform separates frontend application routes and backend API routes at
the CloudFront edge layer.

The deployed namespace split is:

- `/app` and `/app/*`
  - reserved for the frontend application
  - served from the private S3 frontend origin
  - handled as a single-page application (SPA)
- `/events` and `/events/*`
  - reserved for backend API routes
  - forwarded to API Gateway
  - no frontend routing logic applies

This separation ensures that:

- browser navigation does not collide with API routes
- frontend routing remains independent of backend path design
- API contracts remain stable and unchanged

### SPA Deep-Link Handling

The frontend application uses client-side routing.

To support browser refresh and direct navigation for SPA routes under `/app`,
CloudFront rewrites eligible browser navigation requests to `/index.html`.

This is implemented using a CloudFront Function attached only to the S3-facing
frontend behaviors.

Rewrite conditions:

- request path is `/app` or starts with `/app/`
- request method is `GET` or `HEAD`
- request represents a browser navigation that expects HTML

Rewrite target:

- `/index.html`

Important constraints:

- API routes under `/events` must not be affected
- static asset requests must not be rewritten
- missing static assets must still return real `403` or `404` responses

This keeps SPA routing isolated while preserving correct behavior for API and
assets.

### Frontend Origin Strategy

The frontend bucket is intentionally private.

It is not intended to expose:

- public bucket access
- S3 website hosting endpoints
- direct browser access to bucket objects

Instead, the bucket exists only as a private CloudFront origin.

This preserves a cleaner production-shaped boundary:

- S3 stores frontend artifacts
- CloudFront delivers those artifacts publicly
- origin access stays controlled at the edge layer

### CloudFront Behavior Model

CloudFront uses separate origin and cache behavior families for frontend and
API traffic.

The deployed distribution includes:

- one default behavior for static frontend assets from S3
- S3-facing frontend behaviors for `/app` and `/app/*`
- API Gateway-facing backend behaviors for `/events` and `/events/*`
- a CloudFront Function attached only to the S3-facing frontend behaviors for
  SPA deep-link rewrites
- HTTP-to-HTTPS redirection for every behavior
- compression for frontend and API responses
- AWS managed `CachingOptimized` policy for frontend assets
- AWS managed `CachingDisabled` policy for API traffic
- AWS managed `AllViewerExceptHostHeader` origin request policy for API
  forwarding
- optional WAF association when enabled by the environment

The API behaviors forward the methods and request details required by the
routed backend without moving authentication, authorization, or business
decisions into CloudFront.

Frontend application routes remain under `/app` and `/app/*`; backend API
routes remain under `/events` and `/events/*`.

### API Gateway Relationship

CloudFront does not replace API Gateway.

API Gateway remains responsible for:

- route matching
- JWT validation
- Lambda request authorizers
- normalized caller context
- backend authorization boundaries
- Lambda proxy integration behavior

CloudFront changes the public entry path and request-routing layer, but the
backend authorization model remains unchanged.

### Same-Origin and CORS Model

Browser traffic uses the same CloudFront origin for frontend assets and API
requests:

- `/app` and static assets are served from S3
- `/events` and `/events/*` are forwarded to API Gateway

The `dev` environment therefore leaves API Gateway CORS disabled with
`cors_configuration = null`. The reusable API Gateway module still supports
optional CORS for a future environment or integration that genuinely requires
cross-origin browser access.

### Frontend Application Structure

The frontend is a React + Vite + TypeScript single-page application delivered
as static assets through the CloudFront/S3 edge layer.

The application shell remains small and eagerly loaded:

- React Router owns browser routing under the `/app` basename
- the shared layout/header/navigation shell loads before route pages
- route page components are lazy-loaded behind a shared loading fallback

This keeps browser route behavior stable while allowing Vite to split page code
into route-level chunks. Route-level lazy loading must not change:

- `/app` browser route behavior
- same-origin `/events` API calls
- auth/session behavior
- RSVP, cancellation, or pagination behavior

The frontend visual system is implemented with:

- Tailwind CSS v4
- shared layout primitives for page, panel, action, and list composition
- shared UI class constants for buttons, links, form controls, and headings

This keeps the frontend styling local to the React app instead of relying on
broad global element styling.

The frontend also owns user-experience behavior that does not belong in backend
business logic:

- accessible skip-link, status, form, list, and confirmation semantics
- client-side filtering and sorting over already loaded event DTOs
- preserving the user's intended in-app destination when login is required by
  a protected UI prompt

---

## Authentication Layer

The platform uses **Amazon Cognito User Pools** as its managed identity
provider.

This creates a strict separation of concerns between identity, route
protection, and authorization decisions.

**Amazon Cognito** is responsible for:

- user registration
- user login
- token issuance
- email verification
- password reset and recovery
- user group membership such as admin

**Amazon API Gateway** is responsible for:

- native JWT validation on ordinary protected routes
- invoking a dedicated custom Lambda authorizer for the mixed-mode RSVP route
- route-level authentication enforcement

**Shared request/auth normalization** is responsible for:

- accepting multiple upstream authorizer context shapes
- mapping caller identity into one normalized internal caller contract

**Business AWS Lambda** functions are responsible only for resource- and
workflow-specific authorization:

- ownership checks
- event-type-dependent access rules
- admin versus non-admin business decisions

Business Lambda functions do not implement:

- login
- session management
- JWT verification
- generic authentication logic

This keeps authentication centralized while allowing business decisions to stay
close to the resource workflows that depend on them.

The dedicated custom RSVP authorizer remains part of the platform auth layer,
not part of business workflow logic.

### Identity Model

The platform's canonical internal user identifier is the Cognito user `sub`.

The deployed identity model derives:

- Cognito `sub` for user identity
- Cognito group membership for admin capability

Business Lambdas consume a normalized internal caller contract rather than
depending directly on one raw API Gateway authorizer shape.

This keeps internal identity:

- stable
- immutable
- independent of username or email changes

### Sign-In Model

Sign-in is Cognito-managed.

The deployed User Pool uses:

- username as the primary sign-in attribute
- case-insensitive usernames
- self-service registration
- required email collection
- Cognito-managed email verification
- verified email for account recovery

The public User Pool Client supports password, SRP, and refresh-token
authentication without a client secret. Future sign-in changes can preserve the
canonical internal identity model because application ownership is based on
Cognito `sub`, not username or email.

### Admin Model

Administrative capabilities are derived from Cognito group membership.

The deployed User Pool includes one administrative group:

- `admin`

API Gateway authorizers project group membership into normalized caller
context. Business Lambdas must not infer admin privileges from request payloads
or handler-specific authentication logic.

### Cognito Scope

The deployed identity layer includes:

- one User Pool
- one public User Pool Client
- one `admin` group

It intentionally does not include:

- hosted UI
- social identity providers
- MFA
- Lambda triggers
- custom domains
- OAuth scopes and resource servers

This keeps the identity layer focused on the authentication and authorization
requirements currently used by the application. Detailed account-lifecycle,
route-authentication, and authorization behavior is documented in
[platform-behavior.md](platform-behavior.md).

---

## API Layer

**Amazon API Gateway HTTP API** routes each operation to a dedicated **AWS
Lambda** workload.

This provides:

- fault isolation
- independent scaling
- clear workload ownership
- workload-specific IAM permissions

The deployed route families cover:

- event creation
- public event listing and lookup
- creator-scoped event listing
- creator-owned event management
- RSVP submission and RSVP administration

The API uses three route-authentication modes:

- `NONE` for public event listing and lookup
- `JWT` for authenticated event-management and owner/admin routes
- `CUSTOM` for mixed anonymous and authenticated RSVP access

---

## Synchronous RSVP Write Pattern

RSVP submission is implemented as a **synchronous transactional operation**.

Request path:

```text
Client -> CloudFront -> API Gateway -> Lambda -> DynamoDB transaction
```

The transaction returns the final business outcome to the caller:

- RSVP created
- RSVP updated
- event at capacity
- access denied
- event not found

SQS and EventBridge are intentionally excluded from this primary write path so
notification processing cannot delay or redefine the RSVP result.

Business authorization remains inside the RSVP Lambda:

- public events may allow anonymous RSVP
- protected events require authenticated callers
- admin events require admin callers

Token validation remains in the dedicated mixed-mode Lambda authorizer. The
business handler consumes normalized caller context and owns event access,
capacity, and RSVP state decisions.

Detailed route, request, response, and authorization contracts are documented
in [platform-behavior.md](platform-behavior.md).

---

## Event-Driven Notification Architecture

Asynchronous services are used **after durable business state changes**.

Core API outcomes remain synchronous. Notification publication or delivery
failures do not change the result of an already committed business operation.

### Post-Commit Fanout

After a successful event-management write, the responsible Lambda publishes one
compact domain event to EventBridge:

- `event.created`
- `event.updated`
- `event.cancelled`

Write Lambdas do not publish target-specific notification messages.
EventBridge owns downstream routing and fanout.

The notification architecture separates admin broadcasts from participant
email delivery.

### Admin Notification Path

```text
EventBridge -> SNS admin topic
```

Admin notifications cover event creation, update, and cancellation. EventBridge
input transformers produce lightweight admin-readable SNS messages without
requiring a notification Lambda.

### Participant Notification Path

Participant notifications for event updates and cancellations follow this
pipeline:

| Stage | Component | Responsibility |
|---|---|---|
| 1 | EventBridge | Routes committed domain events |
| 2 | SQS `notification-dispatch` | Buffers event-level planning work |
| 3 | Lambda `notification-planner` | Expands RSVP records into recipient-level jobs |
| 4 | SQS `notification-email` | Buffers recipient-level email work |
| 5 | Lambda `notification-sender` | Resolves the current Cognito email and selects the SES template |
| 6 | Amazon SES | Delivers the participant email |

Both workers use partial SQS batch responses so one failed record does not
force successful records to be retried.

### Delivery Boundary

Terraform manages the `dev` SES sender identity and participant templates.
The environment remains in the SES sandbox and therefore requires verified
sender and recipient identities.

Queues remain outside the synchronous RSVP write path. They are used only for
post-commit notification buffering, retries, and failure isolation.

Detailed recipient selection, message contracts, and worker behavior are
documented in [platform-behavior.md](platform-behavior.md). Concrete deployed
wiring, SES configuration, and validation evidence are documented in the
[development environment README](../infrastructure/envs/dev/README.md).

---

## Data Layer

Amazon DynamoDB stores business data in two canonical tables:

| Table | Primary key | Responsibility |
|---|---|---|
| `events` | Partition key: `event_pk` | Event metadata, lifecycle state, visibility, creator ownership, and aggregate RSVP helper counters |
| `rsvps` | Partition key: `event_pk`; sort key: `subject_sk` | Canonical event membership for authenticated and anonymous RSVP subjects |

Canonical key values use:

- `event_pk = EVENT#<event_id>`
- `subject_sk = USER#<user_id>` for authenticated RSVP subjects
- `subject_sk = ANON#<anonymous_token>` for anonymous RSVP subjects

RSVP records are the source of truth for attendance membership. Event-level
counters support efficient reads but are maintained as derived helper values.

RSVP writes use DynamoDB transactions across both tables to keep membership,
counters, and capacity enforcement consistent under concurrent requests.

The `events` table includes indexes only for established query patterns:

- `public-upcoming-events` for public event discovery
- `creator-events` for creator-owned event listing

The tables use on-demand capacity. Environment-specific durability and cost
choices, including the `dev` point-in-time recovery setting, are documented in
the [development environment README](../infrastructure/envs/dev/README.md).
Detailed keys, lifecycle behavior, capacity rules, pagination, and public DTO
boundaries are documented in
[platform-behavior.md](platform-behavior.md).

---

## Observability Layer

The deployed observability baseline uses AWS-native logs, metrics, alarms,
dashboards, and traces:

| Signal | Implementation | Coverage |
|---|---|---|
| Logs | Amazon CloudWatch Logs | Terraform-managed Lambda log groups and a dedicated API Gateway access-log group |
| Alarms | Amazon CloudWatch metric alarms | Lambda errors and throttles, API Gateway 5xx responses, SQS backlog and message age, DLQ messages, and EventBridge failed target invocations |
| Dashboard | Amazon CloudWatch dashboard | Lambda, API Gateway, SQS, and EventBridge service health and performance |
| Traces | AWS X-Ray | Active tracing for API/business, authorizer, and notification-worker Lambdas |

The CloudWatch baseline uses native AWS service metrics. It does not create
custom application metrics or log metric filters.

Alert delivery remains separate from detection. The `dev` alarms have no alarm
or OK actions, so they expose operational conditions without routing
notifications to an incident channel.

API Gateway active tracing is not enabled because the platform uses HTTP API;
API Gateway X-Ray tracing supports REST APIs. Lambda tracing remains active
across the deployed workloads.

Concrete alarm definitions, dashboard coverage, log retention, and validation
evidence are documented in the
[development environment README](../infrastructure/envs/dev/README.md).
Reusable alarm and dashboard behavior is documented in the
[observability module README](../infrastructure/modules/observability/README.md).
