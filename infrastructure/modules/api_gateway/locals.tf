############################################
# Normalized module models
############################################

locals {
  # Parse each route key once so the rest of the module can consume a stable
  # route model instead of repeating string-splitting logic inline across
  # integrations, routes, and Lambda invoke permissions.
  route_integrations = {
    for route_name, route in var.routes :
    route_name => merge(route, {
      method = split(" ", route.route_key)[0]
      path   = split(" ", route.route_key)[1]
    })
  }

  # Keep stage route settings intentionally narrow in this PR.
  #
  # This module hardening step adds only throttling controls here, because
  # those are the HTTP API route settings the platform currently needs next.
  # More advanced API Gateway route-setting concerns are intentionally left out
  # so the reusable module stays aligned with the approved platform scope.
  route_settings = {
    for route_name, route in var.routes :
    route.route_key => {
      throttling_burst_limit = route.throttling_burst_limit
      throttling_rate_limit  = route.throttling_rate_limit
    }
    if(
      try(route.throttling_burst_limit, null) != null ||
      try(route.throttling_rate_limit, null) != null
    )
  }
}
