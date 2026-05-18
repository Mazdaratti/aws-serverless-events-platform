# SES Participant Email Baseline

This module creates the reusable Amazon SES participant email baseline for the
serverless events platform.

It is intentionally platform-specific. The goal is not to provide a generic SES
factory or broad email-delivery abstraction. Instead, this module defines the
sender identity and reusable participant notification templates that the
notification sender worker composes around.

This module manages SES identity and template infrastructure only.

---

## What This Module Creates

This module currently creates:

- one SES email identity for the participant notification sender
- one SES template for `event.updated`
- one SES template for `event.cancelled`

It also exposes the core outputs later platform layers need, including:

- sender email
- sender identity ARN
- template names
- template ARNs

This keeps the first SES implementation small, reviewable, and aligned with the
locked participant notification delivery contract.

---

## Sender Identity Strategy

The development baseline uses a dedicated project inbox as the SES sender
identity.

That inbox is the visible participant email `From` address. It must not be a
private personal email address.

Terraform creates the SES email identity, but verification remains manual. SES
sends a verification email to the configured inbox, and the inbox owner must
click the verification link before SES can send from that address.

Do not commit real sender email addresses in reusable module code, examples, or
environment documentation. Environment wiring should pass the real sender email
through local untracked configuration such as `terraform.tfvars`.

---

## Participant Notification Templates

SES templates own the stable user-facing email wording for participant
notifications.

This module creates templates for:

- `event.updated`
- `event.cancelled`

Each template includes:

- subject
- plain-text body
- HTML body

The notification sender worker chooses the template and provides safe template
data. It does not send raw EventBridge payloads or DynamoDB storage fields to
participants.

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

## SES Sandbox Boundary

This module does not request SES production access.

In SES sandbox mode, AWS requires both:

- a verified sender identity
- verified recipient email addresses

That means development validation must use recipient addresses that are verified
in SES, unless the account has already been moved out of the sandbox.

---

## Module Boundary

This module does not create:

- IAM permissions
- Lambda functions
- Lambda event source mappings
- Cognito resources
- SQS resources
- SES domain identities
- SES production access requests
- MAIL FROM configuration
- actual email sending behavior

Those concerns belong to environment wiring and notification sender
implementation outside this module.

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
