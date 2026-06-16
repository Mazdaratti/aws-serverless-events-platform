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

  # Normalize only the per-route throttling settings owned by this module.
  # Other API Gateway route-setting concerns remain outside its public
  # configuration contract.
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
