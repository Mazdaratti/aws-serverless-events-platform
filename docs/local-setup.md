# Local Setup

This document records the current local developer tooling expected for working
in this repository.

It is intentionally practical and lightweight. The root `README.md` stays
focused on platform scope, architecture, and roadmap, while this file captures
the tools needed to run validation and build steps locally.

## Current Tooling Baseline

The current local workflow expects these tools to be available:

- Python
- Docker
- Terraform
- `tflint`
- `terraform-docs`
- AWS CLI
- Node.js
- npm

These tools support the currently implemented backend and infrastructure
workflow:

- Python is used for Lambda source code, tests, and helper scripts
- Docker is used for Lambda-compatible vendored dependency builds where native
  dependencies are involved
- Terraform is used for infrastructure validation, planning, and deployment
- `tflint` is used for Terraform linting
- `terraform-docs` is used to refresh generated module and environment README sections
- AWS CLI is used by local deployment helpers for S3 uploads and CloudFront
  cache invalidation
- Node.js and npm are used for the React/Vite frontend application under
  `frontend/`

## Python

Current project direction:

- use Python `3.13` for deployed Lambda runtime compatibility
- local helper scripts in `scripts/` are also Python-based where practical
- local Python virtual environments such as `.venv` are recommended for tests,
  helper scripts, and local dependency installs

Examples of Python-based local workflow:

- packaging Lambda ZIP artifacts:
  - `scripts/package_lambda.py`
- rebuilding the RSVP authorizer vendor tree:
  - `scripts/build_rsvp_authorizer_vendor.py`
- running focused handler tests

Local test execution now uses the shared pytest bootstrap under:

- `tests/conftest.py`

That bootstrap aligns local import-path behavior with CI so Lambda handlers can
be tested locally using the same `shared/...` import layout expected by the
packaged deployment artifacts.

## Docker

Docker is currently required for the mixed-mode RSVP authorizer packaging flow.

Why:

- the authorizer depends on native libraries such as `cryptography` and `cffi`
- local importability is not the same as Lambda-runtime compatibility
- the repository now uses a Docker-based rebuild step to generate a
  Lambda-compatible vendor tree for:
  - `lambdas/rsvp_authorizer/vendor/`

Docker is not currently required for ordinary Lambda packaging or Terraform
validation. It is specifically required for the RSVP authorizer vendor rebuild
flow.

## Terraform

Terraform is the source of truth for infrastructure in this repository.

The local workflow currently uses Terraform for:

- `fmt`
- `init`
- `validate`
- `plan`
- targeted environment/module verification during implementation

## `tflint`

`tflint` is part of the expected Terraform validation workflow for:

- modules
- examples
- `infrastructure/envs/dev`

## `terraform-docs`

`terraform-docs` is part of the expected documentation maintenance workflow
for:

- Terraform modules
- `infrastructure/envs/dev`

It is used to refresh generated input/output/reference sections in README files
after interface changes.

## AWS CLI

The AWS CLI is required for local application artifact deployment workflows.

For the current frontend deployment helper, the AWS CLI must be able to access
the same AWS account and permissions used for the dev environment.

The helper uses AWS CLI commands for:

- previewing and syncing `frontend/dist/` to the private frontend S3 bucket
- creating a CloudFront cache invalidation after a real frontend upload

## Frontend

Frontend implementation is now an active implementation track.

The frontend foundation uses:

- Node.js
- npm
- React
- Vite
- TypeScript
- React Router

The frontend app lives under:

- `frontend/`

Local frontend validation should run from that directory:

- `npm ci`
- `npm run typecheck`
- `npm run build`
- `npm run dev` (optional for local development)

Use `npm ci` for PR validation because `frontend/package-lock.json` is now
committed and represents the reproducible dependency install plan.

For local browser testing, copy the example environment file and provide the
public Cognito values for the active environment:

- `frontend/.env.example`
- `frontend/.env`

Only public `VITE_*` values belong in the frontend environment file. Do not add
API Gateway invoke URLs or secrets.

The frontend is built as a static SPA for the CloudFront/S3 delivery model.

Runtime routing and API integration rules:

- React Router uses `BrowserRouter` with `/app` as the basename
- Vite must not configure `base: "/app/"`; default base (root) must be used
- static build assets should resolve as root-relative paths such as
  `/assets/...`
- API calls must use same-origin relative paths such as `/events`
- API calls must not use a direct API Gateway URL
- API calls must not use a `/api` prefix

### Frontend Deployment Helper

The local frontend deployment helper is:

- `scripts/deploy_frontend.py`

The helper is the current production-shaped manual deployment path for the
React/Vite frontend. It reads public frontend deployment values from Terraform
outputs in:

- `infrastructure/envs/dev`

Before using the helper, make sure the dev Terraform state is current and
includes the frontend deployment outputs:

- `aws_region`
- `frontend_bucket_name`
- `cloudfront_distribution_id`
- `cloudfront_distribution_domain_name`
- `cognito_user_pool_id`
- `cognito_user_pool_client_id`

Run a safe dry-run first from the repository root:

```bash
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

```bash
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

Do not add an API Gateway URL, secrets, AWS credentials, or non-public
configuration to frontend Vite environment files.

The helper restores any existing `frontend/.env.production.local` file after
the build. If that file did not exist before the helper ran, it is removed.

After a real deployment, validate through CloudFront:

- `https://<cloudfront-domain>/app`
- `https://<cloudfront-domain>/app/events`
- `https://<cloudfront-domain>/app/create-event`
- `https://<cloudfront-domain>/events`

Also refresh a frontend deep link directly in the browser, such as:

- `https://<cloudfront-domain>/app/events`

The refresh should return the SPA entrypoint through CloudFront. API routes
under `/events` should continue to return API responses, not frontend HTML.

Authentication uses Cognito through the frontend Amplify Auth SDK.

Token rules:

- Cognito auth tokens must use `sessionStorage`
- Cognito auth tokens must not use `localStorage`
- the frontend must use the JWT type currently validated by API Gateway and the
  RSVP authorizer, expected to be the Cognito ID token
- the anonymous RSVP token may use `localStorage` because it is not an auth
  token
