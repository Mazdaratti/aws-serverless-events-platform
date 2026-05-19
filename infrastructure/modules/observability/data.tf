############################################
# Current AWS provider context
############################################

# CloudWatch dashboard metric widgets require an explicit region. Read the
# region from the active AWS provider configuration so callers do not need to
# pass a duplicate dashboard-specific region input.
data "aws_region" "current" {}
