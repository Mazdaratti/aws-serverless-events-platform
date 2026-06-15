# Cognito Identity Module

This module creates the Cognito identity resources for the serverless
events platform.

It is intentionally platform-specific rather than a generic identity
abstraction. The module owns one User Pool, one public application client, and
one administrative group.

Each environment root composes these resources with frontend authentication,
API authorization, and workload permissions. The platform-wide identity and
authorization contracts are documented in the
[architecture guide](../../../docs/architecture.md) and
[platform behavior contract](../../../docs/platform-behavior.md).

---

## What This Module Creates

This module creates:

- one Cognito User Pool
- one public Cognito User Pool Client
- one Cognito User Group: `admin`

It exposes:

- User Pool identifiers
- the public client identifier
- the JWT issuer value
- the rendered admin group name

The caller controls naming overrides, password length, self-sign-up, username
case sensitivity, required email collection, and deletion protection.

---

## Module Boundary

The module owns:

- Cognito User Pool configuration
- one public User Pool Client without a client secret
- one configurable administrative group
- password, sign-up, verification, and recovery settings
- identity resource outputs

It does not own:

- API Gateway authorizers or route authorization
- frontend session and token handling
- Lambda authorizers or Cognito triggers
- hosted UI or custom domains
- social identity providers
- MFA configuration
- OAuth scopes or resource servers
- user creation or group membership assignments

Those responsibilities belong to callers and the application layers that
consume the identity resources.

---

## Identity Contract

The platform identity contract uses:

- canonical internal user identity = Cognito user `sub`
- administrative membership source = the configured Cognito group

The module provides the identity source but does not project claims or group
membership into an API or Lambda caller context.

This keeps internal identity:

- stable
- immutable
- independent of username or email changes

---

## Sign-In Strategy

Sign-in is Cognito-managed.

The module configures:

- username as the primary sign-in attribute
- required email collection
- Cognito-managed email verification
- password, refresh-token, and SRP authentication flows
- token revocation and user-existence error protection

The application client is public and does not generate a client secret.

---

## Deliberately Excluded Features

The module intentionally excludes:

- hosted UI
- social login
- MFA
- Lambda triggers
- custom domains
- OAuth scopes and resource servers
- user seeding

Adding one of these features should be an explicit module-contract change
rather than an environment-specific workaround.

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

This keeps the module reusable across project environments without modeling
unneeded Cognito features.

---

## Outputs

The module exposes:

- `user_pool_id`
- `user_pool_arn`
- `user_pool_client_id`
- `issuer`
- `admin_group_name`

It also exposes:

- `user_pool_endpoint`

Callers can use the issuer and client ID for JWT validation and frontend
authentication without requiring this module to own those integrations.

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

Applying the example creates real Cognito resources and should be reviewed
before use in an AWS account.

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.37 |



## Resources

| Name | Type |
|------|------|
| [aws_cognito_user_group.admin](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_group) | resource |
| [aws_cognito_user_pool.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool) | resource |
| [aws_cognito_user_pool_client.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_client) | resource |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive Cognito resource names. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_admin_group_name"></a> [admin\_group\_name](#input\_admin\_group\_name) | Name of the Cognito group used to identify administrative membership in platform authorization context. | `string` | `"admin"` | no |
| <a name="input_allow_self_signup"></a> [allow\_self\_signup](#input\_allow\_self\_signup) | Whether Cognito allows end users to sign themselves up instead of requiring admin-created users only. | `bool` | `true` | no |
| <a name="input_deletion_protection_enabled"></a> [deletion\_protection\_enabled](#input\_deletion\_protection\_enabled) | Whether Cognito deletion protection is enabled for the User Pool. Environment roots can set this explicitly per environment. | `bool` | `false` | no |
| <a name="input_password_minimum_length"></a> [password\_minimum\_length](#input\_password\_minimum\_length) | Minimum password length for the Cognito password policy. | `number` | `8` | no |
| <a name="input_require_email"></a> [require\_email](#input\_require\_email) | Whether the identity model requires email as a standard user attribute. | `bool` | `true` | no |
| <a name="input_user_pool_client_name_override"></a> [user\_pool\_client\_name\_override](#input\_user\_pool\_client\_name\_override) | Optional explicit Cognito User Pool Client name. When omitted, the module derives the name from name\_prefix. | `string` | `null` | no |
| <a name="input_user_pool_name_override"></a> [user\_pool\_name\_override](#input\_user\_pool\_name\_override) | Optional explicit Cognito User Pool name. When omitted, the module derives the name from name\_prefix. | `string` | `null` | no |
| <a name="input_username_case_sensitive"></a> [username\_case\_sensitive](#input\_username\_case\_sensitive) | Whether Cognito usernames are case-sensitive. The platform default keeps usernames case-insensitive. | `bool` | `false` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_admin_group_name"></a> [admin\_group\_name](#output\_admin\_group\_name) | Name of the Cognito group that backs the future is\_admin caller-context projection. |
| <a name="output_issuer"></a> [issuer](#output\_issuer) | JWT issuer URL derived from the Cognito User Pool for later API Gateway JWT validation wiring. |
| <a name="output_user_pool_arn"></a> [user\_pool\_arn](#output\_user\_pool\_arn) | ARN of the Cognito User Pool used by the platform identity baseline. |
| <a name="output_user_pool_client_id"></a> [user\_pool\_client\_id](#output\_user\_pool\_client\_id) | ID of the public Cognito User Pool Client that later API and frontend layers can use. |
| <a name="output_user_pool_endpoint"></a> [user\_pool\_endpoint](#output\_user\_pool\_endpoint) | Endpoint of the Cognito User Pool. This is optional but can be useful for later integration and documentation. |
| <a name="output_user_pool_id"></a> [user\_pool\_id](#output\_user\_pool\_id) | ID of the Cognito User Pool that acts as the platform's managed identity provider. |
<!-- END_TF_DOCS -->
