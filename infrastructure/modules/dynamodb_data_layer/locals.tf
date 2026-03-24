############################################
# Derived naming and tagging values
############################################

locals {
  # Keep table names predictable and environment-scoped so later env wiring can
  # identify the business data layer clearly without embedding naming logic in
  # the root module.
  events_table_name = "${var.name_prefix}-events"
  rsvps_table_name  = "${var.name_prefix}-rsvps"

  # Extend the environment-provided baseline tags with resource-specific Name
  # tags so each table is easy to identify in AWS.
  events_table_tags = merge(
    var.tags,
    {
      Name = local.events_table_name
    }
  )

  rsvps_table_tags = merge(
    var.tags,
    {
      Name = local.rsvps_table_name
    }
  )
}
