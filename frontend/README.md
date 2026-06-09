# Frontend Operations

This directory contains the React/Vite frontend application served through the
CloudFront/S3 delivery path.

The application uses React, TypeScript, Vite, React Router, Tailwind CSS, and
the AWS Amplify Auth SDK.

Local frontend tooling requires:

- Node.js `20.19.0` or newer
- npm `10.0.0` or newer

## Local Development and Validation

Run frontend commands from this directory.

Install the locked dependency set:

```powershell
npm ci
```

Start the local Vite development server:

```powershell
npm run dev
```

Run the complete validation suite:

```powershell
npm run typecheck
npm run build
npm run test
npm run test:e2e
```

Install the Playwright Chromium runtime before the first browser-test run:

```powershell
npx playwright install chromium
```

Testing is split into:

- Vitest, React Testing Library, `jest-dom`, and `jsdom` for component and
  page-level behavior
- Playwright for Chromium browser smoke tests against the local Vite server

The Playwright smoke suite covers:

- app-shell rendering under `/app`
- public events route shell rendering
- protected-route prompt rendering for `/app/my-events`

Frontend tests use local mocks where needed and do not require AWS credentials,
Cognito, CloudFront, or a deployed backend. They do not deploy or mutate
resources.

## Runtime and Environment Rules

### Public Frontend Configuration

For local development, copy the example environment file from `frontend/`:

```powershell
Copy-Item .env.example .env
```

Provide these public Cognito identifiers:

- `VITE_AWS_REGION`
- `VITE_COGNITO_USER_POOL_ID`
- `VITE_COGNITO_USER_POOL_CLIENT_ID`

Only public `VITE_*` values belong in frontend environment files. Do not add API
Gateway invoke URLs, API Gateway stage URLs, secrets, AWS credentials, or
non-public configuration.

### Routing and API Integration

| Concern | Contract |
|---|---|
| Browser routes | React Router uses `BrowserRouter` with `basename="/app"` |
| Build assets | Vite keeps its default base so assets use root-relative `/assets/...` paths |
| API requests | Use same-origin relative `/events` paths |
| Disallowed API targets | Direct API Gateway URLs, `/api` prefixes, and `/app/events` |

Local Vite development intentionally keeps the same-origin `/events` API model
and does not add a development proxy.

### Authentication and Token Storage

Authentication uses Cognito through the Amplify Auth SDK. The frontend:

- stores Cognito tokens in `sessionStorage`, not `localStorage`
- sends the Cognito ID token as the bearer token validated by API Gateway and
  the mixed-mode RSVP authorizer
- treats a Cognito user session without an ID token as expired

The anonymous RSVP token may use `localStorage` because it is a browser-local
subject identifier rather than an authentication credential.

## Deployment Model

Frontend deployment reads public configuration from the remote-backed Terraform
outputs, builds the application, uploads `frontend/dist/` to the private S3
bucket, and invalidates CloudFront in apply mode.

This lane is separate from Terraform provisioning and Lambda code deployment.
It does not change the same-origin `/events` API contract defined in
[Routing and API Integration](#routing-and-api-integration).

### Deployment Helper

`scripts/deploy_frontend.py` is the shared local and GitHub Actions deployment
path. Run it from the repository root after the `dev` Terraform state exposes:

- `aws_region`
- `frontend_bucket_name`
- `cloudfront_distribution_id`
- `cloudfront_distribution_domain_name`
- `cognito_user_pool_id`
- `cognito_user_pool_client_id`

Preview the deployment:

```powershell
python scripts/deploy_frontend.py --dry-run
```

Apply the deployment:

```powershell
python scripts/deploy_frontend.py --apply
```

Both modes:

- read and validate the required Terraform outputs
- reject unapproved `VITE_*` keys in frontend environment files
- temporarily write the approved public build configuration
- run `npm ci`, typechecking, and the production build
- verify `frontend/dist/`
- preview `aws s3 sync --delete`

Dry-run is the default and does not mutate AWS. Apply mode performs the S3 sync,
creates a CloudFront invalidation for `/*`, and prints the frontend URLs.

The helper restores any existing `frontend/.env.production.local` file after
the build. If that file did not exist before the helper ran, it is removed.

## GitHub Actions Workflows

Frontend deployment workflows are manual-only and run from `main`.

Files:

- `.github/workflows/frontend-deploy-dry-run.yml`
- `.github/workflows/frontend-deploy-apply.yml`

```powershell
gh workflow run frontend-deploy-dry-run.yml --ref main
gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
```

Both workflows validate the required Terraform outputs and delegate frontend
build and deployment behavior to `scripts/deploy_frontend.py`.

- Dry run: validates and builds the frontend, then previews the S3 sync without
  uploading assets or invalidating CloudFront.
- Apply: requires `confirm_deploy=deploy-dev`, uploads `frontend/dist/`, and
  creates a CloudFront invalidation.

Neither workflow runs Terraform plan/apply, provisions infrastructure, packages
Lambda artifacts, or deploys Lambda code.

Shared OIDC, backend, and repository-input prerequisites are documented in
[project-setup.md](../docs/project-setup.md#github-actions-workflows).

## Post-Deployment Validation

Use the CloudFront domain printed by the deployment helper.

### Edge Routing Checks

| Check | URL | Expected result |
|---|---|---|
| App entry point | `https://<cloudfront-domain>/app` | React application loads |
| Public frontend route | `https://<cloudfront-domain>/app/events` | Event-list page loads |
| Protected frontend route | `https://<cloudfront-domain>/app/my-events` | Page loads or prompts for authentication |
| Frontend deep link | `https://<cloudfront-domain>/app/events/<event-id>` | Event-detail page loads |
| API route | `https://<cloudfront-domain>/events` | API response is returned instead of frontend HTML |

Refresh the frontend deep link directly in the browser. CloudFront should return
the SPA entry point, allowing React Router to restore the requested route.

### Product Smoke Checks

Verify:

- public event listing and event-detail loading
- registration, confirmation, sign-in, and sign-out
- redirect back to the requested protected route after sign-in
- event creation, editing, cancellation confirmation, and owned-event listing
- authenticated and anonymous RSVP behavior
- creator/admin RSVP-list access
- keyboard access to the skip link, navigation, filters, forms, and
  confirmation controls
