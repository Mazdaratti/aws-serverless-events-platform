# Cognito Identity Baseline

This module creates the initial Cognito identity baseline for the serverless
events platform.

It is intentionally platform-specific. The goal is not to provide a generic
identity abstraction or a fully-featured authentication product surface.
Instead, this module defines the concrete Cognito baseline that later API
Gateway wiring and environment composition will depend on.

This module manages identity-provider infrastructure only.

---

## What This Module Creates

This module currently creates:

- one Cognito User Pool
- one public Cognito User Pool Client
- one Cognito User Group: `admin`

It also exposes the core identity outputs later layers will need, including:

- User Pool identifiers
- the public client identifier
- the JWT issuer value
- the rendered admin group name

This keeps the first Cognito implementation small, reviewable, and aligned with
the platform's locked authentication boundary.

---

## Why This Module Stays Identity-Focused

This step is focused on the managed identity primitives the platform clearly
needs next:

- Cognito User Pool infrastructure
- a public app client for later API and frontend integration
- admin group membership as the future source of admin caller context

The module does not create API Gateway authorizers, route wiring, hosted UI
configuration, social identity providers, Lambda triggers, MFA flows, custom
domains, OAuth scopes, resource servers, or seeded users. Those concerns may
become relevant later, but they are intentionally outside the scope of this
first Cognito layer.

Keeping the module limited to identity-provider infrastructure makes the design
easier to understand and avoids bleeding API and frontend work into the module.

---

## Identity Direction

This module is aligned with the platform's locked identity direction:

- canonical internal user identity = Cognito user `sub`
- future `requestContext.authorizer.user_id` projection = Cognito `sub`
- future `requestContext.authorizer.is_admin` projection = Cognito `admin`
  group membership

The module does not implement API Gateway claim mapping yet, but it establishes
the Cognito resources that later API-layer auth wiring will project into the
Lambda caller context.

This keeps internal identity:

- stable
- immutable
- independent of username or email changes

---

## Sign-In Strategy

Sign-in is Cognito-managed.

The initial identity baseline uses:

- username as the primary sign-in attribute
- required email collection
- Cognito-managed email verification

This does not permanently lock the platform into username-only login behavior.
Later sign-in changes can evolve without changing the canonical internal
identity model based on Cognito `sub`.

---

## Why The Module Stays Minimal

The first Cognito baseline is intentionally small but future-safe.

It includes:

- one User Pool
- one public User Pool Client
- one `admin` group
- a small password-policy baseline
- Cognito-managed sign-up, verification, and recovery direction

It intentionally excludes:

- hosted UI
- social login
- MFA
- Lambda triggers
- custom domains
- OAuth scopes and resource servers
- user seeding

That keeps the identity layer aligned with the current platform phase:

- Cognito owns identity
- API Gateway will later validate JWTs
- Lambda handlers stay focused on resource- and workflow-specific authorization

---

## Inputs

This module keeps its public input surface intentionally small:

- `name_prefix`
- `tags`
- optional name overrides
- a few baseline identity-policy toggles such as:
  - self sign-up
  - case sensitivity
  - required email
  - deletion protection

This keeps the module reusable without prematurely modeling every Cognito
feature.

---

## Outputs

The module exposes the identity values later layers are most likely to need:

- `user_pool_id`
- `user_pool_arn`
- `user_pool_client_id`
- `issuer`
- `admin_group_name`

It also exposes:

- `user_pool_endpoint`

The issuer output is especially important because later API Gateway JWT
validation wiring will depend on that exact value.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- build the shared `name_prefix`
- define the baseline tag map
- configure the AWS provider for `eu-central-1`
- call the module with the minimal input surface
- inspect the resulting Cognito identity outputs

The example intentionally does not create users, hosted UI configuration, API
Gateway resources, or Lambda resources.

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.37 |



## Resources

| Name | Type |
| ---- | ---- |
| [aws_cognito_user_group.admin](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_group) | resource |
| [aws_cognito_user_pool.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool) | resource |
| [aws_cognito_user_pool_client.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_client) | resource |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive Cognito resource names. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_admin_group_name"></a> [admin\_group\_name](#input\_admin\_group\_name) | Name of the Cognito group that represents future admin membership for platform authorization context. | `string` | `"admin"` | no |
| <a name="input_allow_self_signup"></a> [allow\_self\_signup](#input\_allow\_self\_signup) | Whether Cognito allows end users to sign themselves up instead of requiring admin-created users only. | `bool` | `true` | no |
| <a name="input_deletion_protection_enabled"></a> [deletion\_protection\_enabled](#input\_deletion\_protection\_enabled) | Whether Cognito deletion protection is enabled for the User Pool. Environment roots can set this explicitly per environment. | `bool` | `false` | no |
| <a name="input_password_minimum_length"></a> [password\_minimum\_length](#input\_password\_minimum\_length) | Minimum password length for the Cognito password policy. | `number` | `8` | no |
| <a name="input_require_email"></a> [require\_email](#input\_require\_email) | Whether the baseline identity model requires email as a standard user attribute. | `bool` | `true` | no |
| <a name="input_user_pool_client_name_override"></a> [user\_pool\_client\_name\_override](#input\_user\_pool\_client\_name\_override) | Optional explicit Cognito User Pool Client name. When omitted, the module derives the name from name\_prefix. | `string` | `null` | no |
| <a name="input_user_pool_name_override"></a> [user\_pool\_name\_override](#input\_user\_pool\_name\_override) | Optional explicit Cognito User Pool name. When omitted, the module derives the name from name\_prefix. | `string` | `null` | no |
| <a name="input_username_case_sensitive"></a> [username\_case\_sensitive](#input\_username\_case\_sensitive) | Whether Cognito usernames are case-sensitive. The platform default keeps usernames case-insensitive. | `bool` | `false` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_admin_group_name"></a> [admin\_group\_name](#output\_admin\_group\_name) | Name of the Cognito group that backs the future is\_admin caller-context projection. |
| <a name="output_issuer"></a> [issuer](#output\_issuer) | JWT issuer URL derived from the Cognito User Pool for later API Gateway JWT validation wiring. |
| <a name="output_user_pool_arn"></a> [user\_pool\_arn](#output\_user\_pool\_arn) | ARN of the Cognito User Pool used by the platform identity baseline. |
| <a name="output_user_pool_client_id"></a> [user\_pool\_client\_id](#output\_user\_pool\_client\_id) | ID of the public Cognito User Pool Client that later API and frontend layers can use. |
| <a name="output_user_pool_endpoint"></a> [user\_pool\_endpoint](#output\_user\_pool\_endpoint) | Endpoint of the Cognito User Pool. This is optional but can be useful for later integration and documentation. |
| <a name="output_user_pool_id"></a> [user\_pool\_id](#output\_user\_pool\_id) | ID of the Cognito User Pool that acts as the platform's managed identity provider. |
<!-- END_TF_DOCS -->
