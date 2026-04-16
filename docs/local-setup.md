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

These tools support the currently implemented backend and infrastructure
workflow:

- Python is used for Lambda source code, tests, and helper scripts
- Docker is used for Lambda-compatible vendored dependency builds where native
  dependencies are involved
- Terraform is used for infrastructure validation, planning, and deployment
- `tflint` is used for Terraform linting

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

## Frontend Tooling Direction

Frontend implementation is not yet the active focus, so frontend tooling is not
yet a hard local baseline.

Expected later additions:

- Node.js
- npm

Those should be added here once frontend work becomes an active implementation
track rather than a placeholder direction.
