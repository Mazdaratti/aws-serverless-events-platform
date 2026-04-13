############################################
# Normalized route model
############################################

locals {
  # Parse each route key once so the rest of the module can consume a stable
  # route model instead of repeating string-splitting logic inline.
  routes = {
    for route_name, route in var.routes :
    route_name => merge(route, {
      method = split(" ", route.route_key)[0]
      path   = split(" ", route.route_key)[1]
    })
  }
}
