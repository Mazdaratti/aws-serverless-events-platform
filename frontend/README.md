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

Frontend deployment follows this flow:

1. read required public frontend configuration from Terraform outputs
2. provide those values to the frontend build as `VITE_*` environment variables
3. build frontend assets
4. upload build artifacts into the private frontend bucket
5. create a CloudFront invalidation when applying a real deployment
6. serve the new frontend version through CloudFront

This keeps frontend deployment separate from Terraform provisioning and backend
Lambda code deployment while still presenting one public product entry point.

The frontend build must not receive:

- raw API Gateway invoke URLs
- API Gateway stage URLs
- server-side secrets

API calls remain same-origin relative requests through CloudFront, using paths
such as `/events`.

## Deployment Helper

The local frontend deployment helper is:

- `scripts/deploy_frontend.py`

Run helper commands from the repository root.

The helper is the shared deployment path for the React/Vite frontend. It is used
for local deployment and by the manual GitHub Actions frontend workflows. It
reads public frontend deployment values from Terraform outputs in:

- `infrastructure/envs/dev`

Before using the helper, make sure the dev Terraform state is current and
includes the frontend deployment outputs:

- `aws_region`
- `frontend_bucket_name`
- `cloudfront_distribution_id`
- `cloudfront_distribution_domain_name`
- `cognito_user_pool_id`
- `cognito_user_pool_client_id`

Run a safe dry-run first:

```powershell
python scripts/deploy_frontend.py --dry-run
```

Dry-run mode:

- reads `terraform output -json`
- writes a temporary `frontend/.env.production.local`
- injects only approved public `VITE_*` values
- runs `npm ci`
- runs `npm run typecheck`
- runs `npm run build`
- verifies `frontend/dist/` exists
- previews the S3 upload with `aws s3 sync --dryrun`
- does not upload files
- does not invalidate CloudFront

For a real frontend deployment, run:

```powershell
python scripts/deploy_frontend.py --apply
```

Apply mode performs the same validation and S3 dry-run first, then:

- syncs `frontend/dist/` to the private frontend S3 bucket with `--delete`
- creates a CloudFront invalidation for `/*`
- prints the CloudFront frontend URLs to validate

The helper writes only these public browser build values:

- `VITE_AWS_REGION`
- `VITE_COGNITO_USER_POOL_ID`
- `VITE_COGNITO_USER_POOL_CLIENT_ID`

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
