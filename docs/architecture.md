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
- Rate limiting
- Optional IP filtering rules

This design protects the platform at the network edge and reduces load on backend services.

---

## Authentication Layer

User authentication is handled by:

- **Amazon Cognito**

Cognito issues JWT tokens that are validated directly by:

- **Amazon API Gateway (JWT Authorizer)**

This ensures:

- No authentication logic inside Lambda functions
- Centralized identity management
- Reduced operational complexity
- Production-grade security posture

Generic authentication is intentionally separated from business authorization:

- API Gateway and Cognito handle JWT validation and route protection
- Lambda functions do not implement login or JWT verification
- Lambda functions still enforce business rules that depend on:
  - event type
  - resource ownership
  - admin versus non-admin caller context

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
- event listing and lookup
- creator-owned event management
- synchronous RSVP business handling

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

Generic JWT validation still stays outside Lambda in API Gateway/Cognito.

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

Early decisions (such as synchronous RSVP writes and minimal DynamoDB indexing)
may evolve as real workload characteristics become known.

Business behavior contracts are tracked separately from this architecture
overview so the system design can stay high-level while endpoint behavior and
authorization rules continue to evolve in a controlled way.
