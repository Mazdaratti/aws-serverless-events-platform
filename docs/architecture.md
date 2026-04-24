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

CloudFront behavior is expected to remain intentionally simple in the first
edge-delivery milestone.

The initial distribution should support:

- one default behavior for static frontend assets from S3
- one separate behavior for backend API traffic to API Gateway
- HTTPS redirect at the edge
- compression for static frontend assets
- caching for static frontend assets
- little or no caching for backend API traffic
- WAF association on the distribution

The backend-forwarding behavior should preserve the existing routed backend
contract instead of redefining backend authorization or business behavior at
the edge.

The exact browser-visible API path shape is intentionally not locked here yet.
That detail should be finalized during the CloudFront implementation step so it
can align cleanly with the deployed API Gateway stage strategy and routed
backend contract already in use.

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

### Future Frontend Deployment Direction

Frontend deployment is expected to follow this flow:

1. build frontend assets
2. upload build artifacts into the private frontend bucket
3. invalidate CloudFront cache as needed
4. serve the new frontend version through CloudFront

This keeps frontend deployment separate from backend Lambda deployment while
still presenting one public product entry point.

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

`Client -> API Gateway -> Lambda -> DynamoDB transaction`

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

## Asynchronous Processing Layer

Asynchronous services are used **after durable business state changes**.

The platform uses:

- **Amazon EventBridge**
- **Amazon SNS**
- **Amazon SQS**

Typical asynchronous workloads include:

- notification buffering
- background enrichment tasks
- reconciliation or repair jobs
- batch imports
- scheduled backfills
- retryable downstream integrations

Queues are **not used in the primary RSVP write path**, but remain essential for decoupled processing and failure isolation.

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

## Event-Driven Extensions

After successful writes, domain events are published to:

- **Amazon EventBridge**

These events are emitted only after the primary business write succeeds.

EventBridge routes events to:

- **Amazon SNS**
- future analytics pipelines
- integration services

This enables:

- loose coupling
- extensibility
- independent feature evolution

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
