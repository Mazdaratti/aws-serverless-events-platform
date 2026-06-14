# SES Participant Email Module

This module creates the Amazon SES resources used for participant email
notifications in the serverless events platform.

It is intentionally platform-specific rather than a generic email-delivery
factory. The module owns one sender identity and the approved participant
notification templates.

Each environment root supplies its sender address and composes the templates
with IAM, queues, and email-delivery workloads. The platform-wide notification
model is documented in the [architecture guide](../../../docs/architecture.md).

---

## What This Module Creates

This module creates:

- one SES email identity for the participant notification sender
- one SES template for `event.updated`
- one SES template for `event.cancelled`

It exposes:

- sender email
- sender identity ARN
- template names
- template ARNs

The template names are derived from the caller's shared name prefix.

---

## Sender Identity Strategy

Callers provide a dedicated project inbox as the SES sender identity.

That inbox is the visible participant email `From` address. It must not be a
private personal email address.

Terraform creates the SES email identity, but verification remains manual. SES
sends a verification email to the configured inbox, and the inbox owner must
click the verification link before SES can send from that address.

Do not commit real sender email addresses in reusable module code, examples, or
tracked configuration. Environment roots should receive the real sender address
through an appropriate private input mechanism.

---

## Participant Notification Templates

The SES templates own the stable user-facing wording for participant
notifications.

This module creates templates for:

- `event.updated`
- `event.cancelled`

Each template includes:

- subject
- plain-text body
- HTML body

The calling email-delivery workload chooses a template and provides its template
data. Message production, recipient lookup, and email sending remain outside
this module.

SES template rendering does not make dynamic HTML-safe content safe by itself.
Any dynamic values provided by the sender must be validated and escaped before
being passed to SES.

The templates use separate text and HTML placeholders for dynamic participant
content:

- `event_title_text` for subjects and plain-text bodies
- `event_title_html` for HTML bodies
- `changed_fields_text` for plain-text update details
- `changed_fields_html` for HTML update details

The sender keeps text placeholders readable and escapes HTML placeholders before
calling SES.

---

## SES Account Boundary

This module does not request SES production access.

When the target AWS account remains in the SES sandbox, sending is restricted
to verified identities. Operational verification and production-access requests
remain account-level responsibilities outside Terraform module composition.

The module creates the sender identity resource, but successful email delivery
still depends on the identity verification state and the account's SES sending
status.

---

## Module Boundary

The module owns:

- one SES email identity
- the `event.updated` and `event.cancelled` templates
- sender and template outputs

It does not own:

- IAM permissions
- Lambda functions
- Lambda event source mappings
- Cognito resources
- SQS resources
- SES domain identities
- SES production access requests
- MAIL FROM configuration
- actual email sending behavior

Those concerns belong to callers, account operations, and the email-delivery
implementation.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example uses `participant-notifications@example.com` so repository
validation does not expose a real inbox.

Do not apply the example as-is against AWS. Applying with a real email address
sends an SES verification email to that inbox, and the inbox owner must click
the verification link before SES can send from it.

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
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.45.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_ses_email_identity.sender](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_email_identity) | resource |
| [aws_ses_template.event_cancelled](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_template) | resource |
| [aws_ses_template.event_updated](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_template) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared name prefix used to derive SES participant notification template names. | `string` | n/a | yes |
| <a name="input_sender_email"></a> [sender\_email](#input\_sender\_email) | Dedicated project inbox email address to verify as the SES sender identity. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_sender_email"></a> [sender\_email](#output\_sender\_email) | SES sender email identity configured for participant notifications. |
| <a name="output_sender_identity_arn"></a> [sender\_identity\_arn](#output\_sender\_identity\_arn) | ARN of the SES sender email identity. |
| <a name="output_template_arns"></a> [template\_arns](#output\_template\_arns) | Map of participant notification type to SES template ARN. |
| <a name="output_template_names"></a> [template\_names](#output\_template\_names) | Map of participant notification type to SES template name. |
<!-- END_TF_DOCS -->
