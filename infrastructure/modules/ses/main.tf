############################################
# SES sender email identity
############################################

# This module creates the SES sender identity and reusable participant
# notification templates. Terraform can request the email identity, but SES
# email verification remains a manual inbox action: AWS sends a confirmation
# email to this address, and the inbox owner must click the verification link
# before SES can send from it.
resource "aws_ses_email_identity" "sender" {
  email = var.sender_email
}

############################################
# Participant notification templates
############################################

# SES templates keep the user-facing email wording in AWS-managed reusable
# resources. The later sender worker chooses the template and provides safe
# template data instead of rendering full email bodies itself.
resource "aws_ses_template" "event_updated" {
  name    = "${var.name_prefix}-event-updated"
  subject = "Event updated: {{event_title_text}}"

  text = <<-EOT
    Hi,

    An event you RSVP'd to has been updated.

    Event: {{event_title_text}}

    Changed details:
    {{#each changed_fields_text}}
    - {{this}}
    {{/each}}

    View the event:
    {{event_url}}

    You are receiving this email because you RSVP'd to this event.

    This is an automated notification. Please do not reply to this email.
  EOT

  html = <<-EOT
    <!doctype html>
    <html lang="en">
      <body>
        <h1>Event updated: {{event_title_html}}</h1>
        <p>An event you RSVP'd to has been updated.</p>
        <p><strong>Event:</strong> {{event_title_html}}</p>
        <p><strong>Changed details:</strong></p>
        <ul>
          {{#each changed_fields_html}}
          <li>{{this}}</li>
          {{/each}}
        </ul>
        <p><a href="{{event_url}}">View the event</a></p>
        <p>You are receiving this email because you RSVP'd to this event.</p>
        <p>This is an automated notification. Please do not reply to this email.</p>
      </body>
    </html>
  EOT
}

resource "aws_ses_template" "event_cancelled" {
  name    = "${var.name_prefix}-event-cancelled"
  subject = "Event cancelled: {{event_title_text}}"

  text = <<-EOT
    Hi,

    An event you RSVP'd to has been cancelled.

    Event: {{event_title_text}}

    View the event:
    {{event_url}}

    You are receiving this email because you RSVP'd to this event.

    This is an automated notification. Please do not reply to this email.
  EOT

  html = <<-EOT
    <!doctype html>
    <html lang="en">
      <body>
        <h1>Event cancelled: {{event_title_html}}</h1>
        <p>An event you RSVP'd to has been cancelled.</p>
        <p><strong>Event:</strong> {{event_title_html}}</p>
        <p><a href="{{event_url}}">View the event</a></p>
        <p>You are receiving this email because you RSVP'd to this event.</p>
        <p>This is an automated notification. Please do not reply to this email.</p>
      </body>
    </html>
  EOT
}
