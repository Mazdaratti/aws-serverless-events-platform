############################################
# Normalized event bus configuration
############################################

locals {
  # Render the custom EventBridge event bus name from the shared prefix unless
  # the caller explicitly provides a bus name. Keeping this in one local makes
  # the resource block and outputs read the same value.
  event_bus_name = coalesce(
    var.event_bus_name,
    "${var.name_prefix}-events"
  )
}
