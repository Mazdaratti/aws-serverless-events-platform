# Architecture Overview

The AWS Serverless Events Platform is a fully managed, cloud-native web application built entirely on AWS serverless services.

The architecture follows a **transactional core + event-driven extension model**:

- Business-critical API operations execute synchronously and durably through DynamoDB commit
- Asynchronous services are used for scalability, decoupling, and background processing

This approach preserves immediate correctness guarantees while enabling production-grade system evolution.

---

## Edge Layer (Global Entry Point)

User traffic enters the system through:

- **Amazon CloudFront** for global content delivery
- **AWS WAF** for edge-level protection
- **AWS Shield Standard** for automatic DDoS mitigation

CloudFront serves static frontend assets from:

- **Amazon S3**

WAF applies:

- AWS Managed Rule Sets
- IP-based rate limiting

This design protects the platform at the network edge and reduces load on backend services.

### Edge Delivery Direction

The intended edge-delivery baseline uses one CloudFront distribution as the
public entry point for browser traffic.

That distribution is expected to:

- serve static frontend assets from a private S3 bucket
- forward backend API requests to API Gateway
- attach WAF protection at the edge
- enforce HTTPS-only browser access
- provide CDN caching for static frontend assets

This keeps the platform aligned with a production-style edge model:

- S3 stores static frontend assets
- CloudFront is the public browser-facing layer
- WAF protects public traffic before requests reach platform origins

### Frontend Routing Namespace

The platform separates frontend application routes and backend API routes at
the CloudFront edge layer.

The following namespace split is now locked:

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

### CloudFront Behavior Direction

CloudFront behavior remains intentionally simple while preserving a clean
frontend/API path split at the edge.

The distribution should support:

- one default behavior for static frontend assets from S3
- S3-facing frontend behaviors for `/app` and `/app/*`
- API Gateway-facing backend behaviors for `/events` and `/events/*`
- a CloudFront Function attached only to the S3-facing frontend behaviors for
  SPA deep-link rewrites
- HTTPS redirect at the edge
- compression for static frontend assets
- caching for static frontend assets
- little or no caching for backend API traffic
- WAF association on the distribution

The backend-forwarding behavior should preserve the existing routed backend
contract instead of redefining backend authorization or business behavior at
the edge.

The browser-visible path split is now locked: frontend application routes live
under `/app` and `/app/*`, while backend API routes remain under `/events` and
`/events/*`.

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

### CORS Direction

The reusable API Gateway module supports optional CORS configuration, but the
platform's preferred browser-integration direction is same-origin access
through CloudFront.

That means the long-term preferred browser path is:

- frontend assets delivered through CloudFront
- backend API requests also entering through CloudFront

Because of that, API Gateway CORS is expected to remain disabled unless a
specific environment or integration case genuinely requires cross-origin
browser access.

### Frontend Deployment Direction

Frontend deployment follows this production-shaped flow:

1. read required public frontend configuration from Terraform outputs
2. provide those values to the frontend build as `VITE_*` environment variables
3. build frontend assets
4. upload build artifacts into the private frontend bucket
5. invalidate CloudFront cache as needed
6. serve the new frontend version through CloudFront

This keeps frontend deployment separate from backend Lambda deployment while
still presenting one public product entry point.

The current local/manual deployment path is implemented by:

- `scripts/deploy_frontend.py`

That helper reads the deployed environment outputs and provides only public
frontend values to the Vite production build, such as:

- `VITE_AWS_REGION`
- `VITE_COGNITO_USER_POOL_ID`
- `VITE_COGNITO_USER_POOL_CLIENT_ID`

These values identify public Cognito client resources and are safe to include
in browser JavaScript.

The frontend build must not receive:

- raw API Gateway invoke URLs
- API Gateway stage URLs
- server-side secrets

API calls remain same-origin relative requests through CloudFront, using paths
such as `/events`.

CI/CD automation for frontend deployment is intentionally deferred until the
repository has GitHub OIDC and separate deployment workflows.

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

### Frontend Automated Testing Direction

Frontend automated testing is now established as a layered validation baseline
for the React/Vite frontend.

The current testing baseline is intentionally split into two layers:

1. **Vitest + React Testing Library**

   - component and page-level tests running in Node/jsdom
   - focused coverage for form validation, accessible labels, controlled filter
     behavior, loading semantics, and related UI contracts
   - no AWS, Cognito, CloudFront, or backend dependency

2. **Playwright**

   - browser-level Chromium smoke tests running against the local Vite dev
     server
   - current smoke coverage for `/app` shell rendering, public events shell
     rendering, and protected-route prompt behavior for `/app/my-events`
   - local route mocking used where needed to keep the baseline deterministic
     and independent from deployed backend state

Frontend automated tests currently run as validation-only checks. They do not
deploy infrastructure, mutate AWS resources, or replace the manual CloudFront
deployment helper.

The current CI validation workflow now runs:

- `npm ci`
- `npm run typecheck`
- `npm run build`
- `npm run test`
- `npm run test:e2e`

This keeps frontend automated validation in the read-only CI path while
deployment automation remains a separate future milestone tied to GitHub OIDC
and dedicated deployment workflows.

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

The platform's raw identity baseline derives from:

- Cognito `sub` for user identity
- Cognito group membership for admin capability

Business Lambdas consume a normalized internal caller contract rather than
depending directly on one raw API Gateway authorizer shape.

This keeps internal identity:

- stable
- immutable
- independent of username or email changes

### Sign-In Strategy (v1)

Sign-in is Cognito-managed.

The initial identity baseline uses:

- username as the primary sign-in attribute
- required email collection
- Cognito-managed email verification

This does not lock the platform into permanent username-only login. Future
changes such as email-based sign-in can evolve without changing the canonical
internal identity model.

### Admin Model

Administrative capabilities are derived from Cognito group membership.

The initial identity baseline includes one Cognito group:

- `admin`

Lambda functions must not infer admin privileges from request payloads or
handler-specific custom auth logic.

### Initial Cognito Scope

The initial Cognito baseline intentionally includes only:

- one User Pool
- one public User Pool Client
- one `admin` group

The following identity features are intentionally deferred:

- hosted UI
- social identity providers
- MFA
- Lambda triggers
- custom domains
- OAuth scopes and resource servers

This keeps the identity layer minimal while still supporting the platform's
locked authentication and authorization direction.

---

## API Layer

**Amazon API Gateway (HTTP API)** routes requests to individual:

- **AWS Lambda functions**

Each endpoint is implemented as an independent Lambda to provide:

- Fault isolation
- Independent scaling
- Clear ownership boundaries
- Fine-grained IAM permissions

This keeps the compute layer aligned with the platform's business workflow
boundaries, such as:

- event creation
- public event listing and lookup
- creator-scoped event listing
- creator-owned event management
- synchronous RSVP business handling

The routed API intentionally uses a hybrid authorization model:

- public read routes such as broad event listing and single-event lookup remain open
- ordinary protected routes use the native JWT authorizer path
- the RSVP route uses a dedicated custom authorizer path to support mixed anonymous and authenticated access on one operation

---

## Core Business Write Pattern (RSVP)

RSVP submission is implemented as a **synchronous transactional operation**.

Primary flow:

`Client -> CloudFront -> API Gateway -> Lambda -> DynamoDB transaction`

This guarantees the caller immediately receives the final business outcome:

- RSVP created
- RSVP updated
- event at capacity
- access denied
- event not found

This pattern aligns with the existing API contract and improves user experience by avoiding eventual-consistency uncertainty in critical workflows.

The RSVP decision itself remains business-driven inside Lambda:

- public events may allow anonymous RSVP
- protected events require authenticated callers
- admin events require admin callers

JWT validation remains outside the RSVP business Lambda.

For the mixed-mode RSVP route, token validation is performed in the dedicated
custom Lambda authorizer, not in the business handler.

---

## Event-Driven Async Processing

Asynchronous services are used **after durable business state changes**.

Core API outcomes remain synchronous. Notification routing and delivery must
not decide whether the original API request succeeds or fails.

The platform uses:

- **Amazon EventBridge**
  - post-commit domain event router
- **Amazon SNS**
  - admin/platform broadcast notification topic
- **Amazon SQS**
  - durable participant-notification work buffers
- **AWS Lambda**
  - notification planner and sender workers
- **Amazon SES**
  - intended participant email delivery service

After successful event-management writes, compact domain events are published to
EventBridge. These events are emitted only after the primary DynamoDB business
write succeeds.

The v1 event-management domain events are:

- `event.created`
- `event.updated`
- `event.cancelled`

Each successful business change publishes exactly one EventBridge domain event.
Write Lambdas do not publish separate events for separate notification targets.
EventBridge owns fanout.

The locked notification foundation uses separate admin and participant paths.

Admin notification path:

`EventBridge -> SNS admin topic`

The direct admin SNS path uses lightweight EventBridge target formatting for
admin-readable messages. Environment-specific formatting can combine the
published app-relative `event_detail_path` with the deployed frontend domain to
produce a browser URL without changing the Lambda domain event payload.

Participant notification path:

`EventBridge -> notification-dispatch SQS -> notification-planner Lambda -> notification-email SQS -> notification-sender Lambda -> SES`

SQS is used for participant notification durability and retry isolation:

- `notification-dispatch`
  - event-level planning queue for `event.updated` and `event.cancelled`
- `notification-email`
  - recipient-level user-facing email work queue between the future planner and
    sender

The notification worker layer is intentionally split:

- `notification-planner`
  - has a dedicated least-privilege IAM role prepared in `dev`
  - will consume event-level participant notification work
  - queries RSVP records by event
  - will create one recipient-level email job per authenticated RSVP user
  - includes both attending and not-attending RSVP users
  - skips anonymous RSVP subjects in v1
- `notification-sender`
  - has a dedicated least-privilege IAM role prepared in `dev`
  - will consume recipient-level email jobs
  - will resolve the current recipient email through Cognito at send time using
    the canonical Cognito `sub`
  - will render user-facing participant email content through stable templates
  - will send participant email through SES

This keeps EventBridge responsible for fanout, SQS responsible for durable
participant work buffering, and SES responsible for direct participant email
delivery when that layer is implemented.

The planner and sender IAM roles are already prepared in `dev`, but worker
Lambda code, event source mappings, SES permissions, and sender templates are
not implemented yet.

Participant emails are user-facing product emails, not admin/debug messages.
The planner produces safe recipient-level jobs, and the sender owns final
presentation through stable templates. EventBridge does not send directly to
`notification-email`.

Queues are **not used in the primary RSVP write path**, but remain essential
for decoupled notification processing and failure isolation.

---

## Data Layer

Business data is stored in:

- **Amazon DynamoDB**

The initial data model uses an **initial two-table business data design**:

### Events table

Stores canonical event records including:

- event metadata
- visibility flags
- organizer ownership
- aggregate RSVP helper counters

Counters improve read efficiency but are **not the source of truth**.

### RSVPs table

Stores canonical RSVP membership records using:

- event-scoped partition key
- subject-scoped sort key

This design supports:

- efficient per-event RSVP queries
- both authenticated and anonymous RSVP subjects
- transactional capacity enforcement

DynamoDB runs in **on-demand billing mode** for cost efficiency and burst handling.

Global secondary indexes are introduced only for **validated access patterns**, such as:

- public upcoming event discovery
- creator event listing

Those access patterns intentionally support the current Lambda rollout order:

- broad event discovery
- creator-owned event listing
- later transactional RSVP handling

---

## Observability

System monitoring includes:

- **Amazon CloudWatch** for logs and metrics
- **AWS X-Ray** for distributed request tracing

These services provide:

- performance visibility
- operational debugging capability
- production readiness foundations

---

## Architecture Evolution Strategy

The platform is intentionally implemented incrementally.

Infrastructure layers are introduced in a controlled sequence to:

- validate architectural assumptions early
- reduce refactoring risk
- maintain clear review boundaries
- support cost-aware experimentation

Reusable modules are allowed to begin as thin environment-driven building
blocks while behavior is being proven in real AWS.

Once a layer is validated end to end, its reusable module is tightened,
documented, example-backed, and CI-validated before the next major platform
layer is introduced.

Early decisions (such as synchronous RSVP writes and minimal DynamoDB indexing)
may evolve as real workload characteristics become known.

Business behavior contracts are tracked separately from this architecture
overview so the system design can stay high-level while endpoint behavior and
authorization rules continue to evolve in a controlled way.
