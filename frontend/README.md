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

The frontend deployment dry-run workflow is:

- `Frontend Deployment Dry Run`
- `.github/workflows/frontend-deploy-dry-run.yml`

Run it from `main` with:

```powershell
gh workflow run frontend-deploy-dry-run.yml --ref main
```

The frontend deployment apply workflow is:

- `Frontend Deployment Apply`
- `.github/workflows/frontend-deploy-apply.yml`

Run it from `main` with the required confirmation input:

```powershell
gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
```

Both workflows use GitHub OIDC, generate the dev backend configuration from
repository variables, initialize the remote Terraform backend, check required
frontend deployment outputs, and then run the frontend deployment helper.

The manual apply workflow uploads frontend assets and creates the CloudFront
invalidation, but it does not run `terraform plan`, run `terraform apply`,
provision infrastructure, package Lambda artifacts, or deploy Lambda code.

## Post-Deployment Validation

After a real deployment, validate through CloudFront:

- `https://<cloudfront-domain>/app`
- `https://<cloudfront-domain>/app/events`
- `https://<cloudfront-domain>/app/my-events`
- `https://<cloudfront-domain>/app/create-event`
- `https://<cloudfront-domain>/app/events/<event-id>`
- `https://<cloudfront-domain>/app/events/<event-id>/rsvps`
- `https://<cloudfront-domain>/events`

Also refresh a frontend deep link directly in the browser, such as:

- `https://<cloudfront-domain>/app/events`

The refresh should return the SPA entrypoint through CloudFront. API routes
under `/events` should continue to return API responses, not frontend HTML.

For a quick frontend smoke test after deployment, also verify:

- keyboard access to the skip link, navigation, filters, forms, and destructive
  confirmation flows
- sign-in redirects back to protected frontend destinations such as
  `/app/my-events`, event detail pages, and RSVP list pages
