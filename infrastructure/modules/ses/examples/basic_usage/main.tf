############################################
# Example context
############################################

locals {
  name_prefix = "aws-serverless-events-platform-dev"
}

############################################
# SES participant email baseline example
############################################

# Calling the module creates one sender email identity plus the event.updated
# and event.cancelled participant notification templates.
#
# The email address uses example.com so this example is safe for repository
# validation and does not expose a real inbox. Applying the example with a real
# email address sends an SES verification email to that inbox, and the inbox
# owner must click the verification link before SES can send from it.
module "ses" {
  source = "../.."

  name_prefix  = local.name_prefix
  sender_email = "participant-notifications@example.com"
}
