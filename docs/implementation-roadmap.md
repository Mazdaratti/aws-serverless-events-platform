# Infrastructure Implementation Roadmap

This document records the incremental implementation history and planned
development direction for the AWS Serverless Events Platform.

Completed items document delivered and validated capabilities. Unchecked items
represent planned work and may be refined before implementation.

## Implementation Approach

The platform is implemented incrementally so infrastructure and application
boundaries can be validated in real AWS before the next major capability is
introduced.

Each implementation slice follows the same general progression:

1. define the intended architecture or behavior contract
2. implement the smallest complete capability
3. validate it locally, in CI, and in AWS where applicable
4. tighten reusable modules, documentation, examples, and automation
5. proceed to the next platform layer

This approach keeps review boundaries clear, limits premature abstraction, and
allows cost, security, and operational assumptions to be tested against the
deployed environment.

Reusable Terraform modules may begin as narrow environment-driven building
blocks while a service boundary is being proven. Once validated end to end,
their interfaces and supporting validation are hardened before broader reuse.

Architecture and implementation choices may evolve when real access patterns,
workload characteristics, or operational evidence justify a change. Product
and authorization contracts remain separately documented so roadmap changes do
not silently redefine platform behavior.

## Roadmap

1. Terraform environment foundation ✅
   - local-state-first `envs/dev` baseline ✅
   - provider/version constraints ✅
   - shared naming and tagging structure ✅

2. DynamoDB business data layer ✅
   - `events` table ✅
   - `rsvps` table ✅
   - initial event listing GSIs ✅

3. SQS queues and dead-letter queues ✅
   - notification dispatch queue ✅
   - notification email queue ✅
   - dedicated DLQ wiring for both notification queues ✅

4. IAM roles and policies for workloads ✅
   - least-privilege execution roles ✅
   - workload-specific access profiles ✅
   - DynamoDB and SQS policy wiring ✅
   - split notification planner/sender IAM roles ✅

5. Lambda compute layer ✅
   - ZIP-based Lambda deployment baseline ✅
   - external packaging workflow ✅
   - CloudWatch log group wiring ✅

6. Core synchronous Lambda workload rollout ✅
   - `create-event` ✅
   - `list-events` ✅
   - `list-my-events` ✅
   - `get-event` ✅
   - `update-event` ✅
   - `cancel-event` ✅
   - `rsvp` ✅
   - `get-event-rsvps` ✅

7. Cognito authentication baseline ✅
   - Cognito User Pool ✅
   - public app client ✅
   - admin group ✅

8. Lambda identity normalization across authorizer modes ✅
   - shared caller normalization helper ✅
   - shared helper test coverage ✅
   - shared packaging support for `shared/...` imports ✅
   - `create-event` normalization adoption ✅
   - `update-event` normalization adoption ✅
   - `cancel-event` normalization adoption ✅
   - `get-event-rsvps` normalization adoption ✅
   - `rsvp` normalization adoption ✅
   - `list-events` public-only cleanup ✅

9. `list-my-events` workload split from `list-events` ✅
   - dedicated creator-scoped listing workload ✅
   - JWT-protected routed path ✅

10. Mixed-mode RSVP Lambda authorizer ✅
   - mixed anonymous/authenticated caller projection ✅
   - invalid presented auth denied at API Gateway edge ✅
   - routed downstream shape validated in AWS ✅

11. Routed API rollout and AWS validation ✅
   - `create-event` routed path ✅
   - `update-event` routed path ✅
   - `cancel-event` routed path ✅
   - `get-event-rsvps` routed path ✅
   - `list-events` routed path ✅
   - `list-my-events` routed path ✅
   - `get-event` routed path ✅
   - `rsvp` routed path ✅
   - temporary RSVP probe slice removed after real route validation ✅

12. API Gateway reusable module completion and hardening ✅
   - hardened the module interface ✅
   - tightened variable validation and module assumptions ✅
   - improved descriptions and comments ✅
   - added `examples/basic_usage` ✅
   - added module `README.md` ✅
   - ensured `terraform-docs` injection is correct ✅
   - expanded Terraform validation CI to cover the module and example ✅

13. Edge delivery layer (S3 + CloudFront + WAF)
   - `s3_frontend_bucket` reusable module baseline ✅
   - `infrastructure/envs/dev` wiring for the private frontend origin bucket ✅
   - `waf` reusable module ✅
   - `infrastructure/envs/dev` wiring for the WAF baseline ✅
   - `cloudfront` reusable module ✅
   - `infrastructure/envs/dev` wiring for the CloudFront baseline ✅
   - `/app` SPA routing namespace and CloudFront Function rewrite ✅

14. Frontend Foundation ✅
15. Frontend Product Functionality Layer ✅
16. Frontend Deployment Integration ✅
   - local/manual frontend deployment path ✅
   - read required public frontend values from Terraform outputs ✅
   - build the React/Vite frontend with public `VITE_*` values only ✅
   - sync `frontend/dist/` to the private S3 frontend bucket ✅
   - invalidate CloudFront after frontend artifact upload ✅
   - keep CloudFront as the only browser-facing entry point ✅
   - no backend, Lambda, API Gateway, or routing behavior changes ✅

17. Frontend UX + Performance Hardening ✅
   - Tailwind CSS v4 baseline ✅
   - reusable layout primitives ✅
   - responsive page and shared component migration ✅
   - shared event list controls with public vs owner option sets ✅
   - accessibility pass for skip links, forms, status feedback, lists, and
     destructive confirmation ✅
   - route-level lazy loading ✅
   - production bundle output review ✅
   - CloudFront deployment and manual browser validation ✅
   - no backend, API route, Terraform, or deployment-helper behavior changes ✅

18. Frontend Automated Testing Baseline
   - Vitest + React Testing Library baseline ✅
   - Playwright browser smoke baseline ✅
   - CI frontend test integration / coverage expansion ✅

19. EventBridge, SNS admin notifications, and SQS fanout
   - add reusable EventBridge module baseline ✅
   - add SNS admin notification topic baseline ✅
   - wire EventBridge bus and SNS admin notification topic for `dev` ✅
   - wire EventBridge routing for `dev` ✅
   - route `event.created`, `event.updated`, and `event.cancelled` to the SNS
     admin topic ✅
   - route `event.updated` and `event.cancelled` to the existing
     `notification-dispatch` SQS queue ✅
   - add SNS and SQS resource policies scoped to concrete EventBridge rule
     ARNs ✅
   - add `aws:SourceAccount` hardening to EventBridge-to-SNS and
     EventBridge-to-SQS resource policies ✅
   - add least-privilege EventBridge publishing permissions for write Lambdas ✅
   - wire EventBridge bus-name environment variable for write Lambdas ✅
   - publish `event.cancelled` from `cancel-event` after successful durable
     cancellation, with tests and validation ✅
   - publish `event.created` from `create-event` after successful durable
     creation, with tests and validation ✅
   - publish `event.updated` from `update-event` after successful durable
     update, with tests and validation ✅
   - add configurable dev admin SNS email subscription without hardcoded
     personal email addresses ✅
   - confirm the admin SNS email subscription ✅
   - add admin SNS message formatting through EventBridge input transformers ✅
   - validate end-to-end admin email delivery for `event.created`,
     `event.updated`, and `event.cancelled` ✅
   - keep synchronous API outcomes independent from async notification results

20. Notification planner/sender workers and SES participant notifications
   - add `notification-email` SQS queue and DLQ ✅
   - harden `notification-dispatch` queue timing for future Lambda SQS
     consumption ✅
   - add least-privilege IAM for `notification-planner` ✅
   - add least-privilege IAM for `notification-sender` ✅
   - implement `notification-planner` to consume `notification-dispatch`
     messages ✅
   - query RSVP records by event and enqueue one recipient-level email job per
     authenticated RSVP user ✅
   - include both attending and not-attending RSVP users ✅
   - skip anonymous RSVP subjects in v1 ✅
   - wire `notification-planner` into `infrastructure/envs/dev` with an SQS
     event source mapping and partial batch responses ✅
   - add reusable SES sender identity and participant template module ✅
   - add reusable SES module example and CI validation coverage ✅
   - wire SES sender identity and templates into `infrastructure/envs/dev` ✅
   - configure the dedicated project sender inbox through local untracked
     tfvars ✅
   - manually verify the dedicated project sender inbox in SES ✅
   - split notification Lambda deployment composition so sender can use the
     CloudFront distribution domain without introducing a dependency cycle ✅
   - implement `notification-sender` to consume `notification-email` messages ✅
   - wire `notification-sender` into `infrastructure/envs/dev` with an SQS
     event source mapping and partial batch responses ✅
   - resolve current recipient email at send time through Cognito `ListUsers`
     by canonical `sub` ✅
   - select SES templates and provide safe text/HTML template data ✅
   - scope sender IAM to `notification-email`, Cognito user lookup, and SES
     templated sending from the project sender identity ✅
   - send templated participant emails through SES ✅
   - add notification sender unit tests and CI compile coverage ✅
   - keep user-facing API responses independent from notification delivery ✅

21. CloudWatch observability and X-Ray tracing
   - Lambda X-Ray active tracing baseline ✅
     - add optional Lambda `tracing_mode` support in the reusable Lambda module ✅
     - enable `tracing_mode = "Active"` for all deployed `dev` Lambda workloads ✅
     - add minimal X-Ray write permissions to Lambda execution policies ✅
     - validate representative trace generation in AWS X-Ray ✅
   - CloudWatch alarm baseline ✅
     - add reusable observability module ✅
     - add high-signal Lambda errors and throttles alarms ✅
     - add SQS source queue depth, DLQ depth, and oldest-message-age alarms ✅
     - add API Gateway 5xx alarm ✅
     - add EventBridge failed-invocation alarms ✅
     - wire alarms into `infrastructure/envs/dev` with alert actions disabled ✅
     - validate 32 deployed CloudWatch metric alarms in AWS ✅
   - compact CloudWatch dashboard ✅
     - include Lambda, API Gateway, SQS, and EventBridge panels ✅
     - wire the dashboard into `infrastructure/envs/dev` ✅
     - validate the deployed dashboard in AWS ✅
   - alert delivery and advanced telemetry deferred ✅
     - no SNS alert topic creation in the first alarm baseline ✅
     - no log metric filters in the first alarm baseline ✅
     - no SES, CloudFront, WAF, cost, or X-Ray dashboard widgets in this slice ✅
     - no ADOT/OpenTelemetry or Powertools tracing instrumentation yet ✅

22. Remote Terraform backend and GitHub OIDC
   - add reusable remote Terraform backend module baseline ✅
   - add teardown-friendly `infrastructure/bootstrap/dev` root ✅
   - generate ignored `infrastructure/envs/dev/backend.tf` for the S3 backend ✅
   - configure S3 native lockfile state locking with `use_lockfile = true` ✅
   - create the dev backend bucket with versioning, SSE-S3 encryption, public
     access block, and `BucketOwnerEnforced` ✅
   - create GitHub Actions OIDC provider and branch-scoped IAM role ✅
   - attach separate state access and split deploy policies to the OIDC role ✅
   - add a repo-aligned permissions boundary for the OIDC role ✅
   - validate the bootstrap resources in AWS ✅
   - migrate `infrastructure/envs/dev` to remote state ✅
   - validate a clean remote-backed `dev` Terraform plan ✅
   - add unified repository variable and secret sync helper for GitHub Actions
     provisioning inputs ✅
   - support syncing GitHub repository variables and secrets from bootstrap
     outputs and local dev Terraform inputs ✅
   - add manual GitHub Actions OIDC smoke workflow ✅
   - validate GitHub Actions OIDC smoke workflow from `main` ✅
   - keep application deployment workflows separate from this infrastructure
     bootstrap

23. CI validation workflow hardening
   - keep CI read-only and validation-focused ✅
   - add frontend validation to CI:
     - `npm ci` ✅
     - `npm run typecheck` ✅
     - `npm run build` ✅
     - `npm run test` ✅
     - `npm run test:e2e` ✅
   - add workflow concurrency to cancel stale branch and PR runs ✅
   - add job timeouts for Terraform, Lambda, frontend, and Terraform matrix
     validation ✅
   - compile repository helper scripts in CI ✅
   - keep Terraform validation detached from real AWS state ✅
   - do not deploy from CI validation jobs ✅
   - validate hardened CI workflow successfully ✅

24. Frontend deployment workflows
   - establish manual GitHub Actions deployment workflows after OIDC exists ✅
   - keep CI validation separate from deployment workflows ✅
   - add manual frontend deployment dry-run workflow ✅
   - validate frontend deployment dry-run workflow from `main` ✅
   - add frontend deployment apply workflow for S3 sync and CloudFront
     invalidation ✅
   - validate frontend deployment apply workflow from `main` ✅
   - keep Terraform provisioning, Lambda packaging, and Lambda code deployment
     outside frontend deployment workflows ✅

25. Lambda provisioning and code deployment separation
   - define the ownership boundary between Terraform and deployment automation ✅
     - Terraform owns Lambda infrastructure, runtime, handler, memory, timeout,
       tracing, IAM, environment variables, log groups, API Gateway
       integrations, Lambda permissions, SQS event source mappings, and related
       AWS service wiring
     - automation owns Lambda ZIP artifact packaging for provisioning and code
       deployment workflows
     - Lambda code deployment automation owns existing-function code updates
     - Terraform plans must still detect real infrastructure/configuration drift
     - external code-only Lambda updates must not cause Terraform to plan a code
       rollback ✅
   - establish reusable Lambda packaging for both automation lanes ✅
     - package all deployed Lambda workloads into `artifacts/lambda/`
     - reuse the same packaging path for provisioning and future code deployment
     - handle the RSVP authorizer vendor build requirement
   - add provisioning automation for Terraform validation ✅
     - sync required GitHub repository variables and secrets for provisioning
     - package Lambda ZIP artifacts before Terraform planning
     - run Terraform init, validate, and plan from GitHub Actions
     - validate the provisioning dry-run workflow from `main` with a clean
       Terraform plan
   - add provisioning apply automation ✅
     - run Terraform plan/apply manually from GitHub Actions ✅
     - require explicit confirmation before applying infrastructure changes ✅
     - apply the saved Terraform plan ✅
     - validate provisioning apply workflow from `main` ✅
     - do not deploy Lambda code directly through `update-function-code` ✅
     - do not deploy frontend assets ✅
   - add Lambda code deployment automation
     - add reusable Lambda deployment helper with dry-run/apply modes ✅
     - add manual Lambda deployment dry-run workflow ✅
     - package Lambda ZIP artifacts ✅
     - map workload keys to deployed Lambda function names ✅
     - validate Lambda deployment dry-run workflow from `main` ✅
     - add manual Lambda deployment apply workflow ✅
     - update existing Lambda function code with
       `aws lambda update-function-code`
     - validate Lambda deployment apply workflow from `main` ✅
     - do not run Terraform apply for code-only deployments
     - do not deploy frontend assets
26. Account lifecycle and Cognito account-management UX
   - docs-first account lifecycle contract
     - lock self-service account lifecycle semantics before implementation
     - decide how account deletion affects owned events, RSVP records,
       notifications, and future audit/history behavior
     - decide whether v1 should support deletion, disablement, anonymization,
       or a staged workflow
     - keep Cognito as the identity provider while platform-specific data
       cleanup remains an application responsibility
   - Cognito self-service account UI
     - add or harden frontend account-management screens
     - support user-facing Cognito flows such as password reset, password
       change, email verification, and session cleanup where appropriate
     - keep frontend identity behavior aligned with Cognito and the existing
       sessionStorage token rule
   - platform-controlled account deletion workflow
     - add backend API support only after the account lifecycle contract is
       locked
     - handle app-owned data consistently according to the chosen retention and
       cleanup policy
     - avoid treating Cognito user deletion as the whole product workflow
   - admin account-management workflow
     - defer admin user-management UI until backend admin account APIs exist
     - keep Cognito group membership as the source of admin capability
     - avoid frontend-only admin account management without backend authority
