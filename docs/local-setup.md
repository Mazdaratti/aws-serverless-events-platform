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

Authentication uses Cognito through the frontend Amplify Auth SDK.

Token rules:

- Cognito auth tokens must use `sessionStorage`
- Cognito auth tokens must not use `localStorage`
- the frontend must use the JWT type currently validated by API Gateway and the
  RSVP authorizer, expected to be the Cognito ID token
- the anonymous RSVP token may use `localStorage` because it is not an auth
  token
