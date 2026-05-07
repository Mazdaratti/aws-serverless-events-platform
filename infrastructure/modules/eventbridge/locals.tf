############################################
# Normalized EventBridge configuration
############################################

locals {
  # Render the custom EventBridge event bus name from the shared prefix unless
  # the caller explicitly provides a bus name. Keeping this in one local makes
  # the resource block and outputs read the same value.
  event_bus_name = coalesce(
    var.event_bus_name,
    "${var.name_prefix}-events"
  )

  # Keep the event bus Name tag close to the rendered name so the resource
  # block can stay focused on the EventBridge resource itself.
  event_bus_tags = merge(var.tags, {
    Name = local.event_bus_name
  })

  # Normalize rule names once. By default the logical rule key becomes the AWS
  # rule name, but callers can provide a shorter or more explicit name when
  # needed.
  normalized_rules = {
    for rule_key, rule in var.rules :
    rule_key => {
      name          = coalesce(rule.name, rule_key)
      description   = try(rule.description, null)
      event_pattern = rule.event_pattern
      targets       = rule.targets
    }
  }

  event_rule_tags = {
    for rule_key, rule in local.normalized_rules :
    rule_key => merge(var.tags, {
      Name = rule.name
    })
  }

  # EventBridge targets are nested under rules in the input because that is the
  # beginner-friendly shape. Flatten them here so the target resource can use a
  # simple for_each map while still preserving the parent rule relationship.
  event_targets = {
    for target in flatten([
      for rule_key, rule in local.normalized_rules : [
        for target_key, target in rule.targets : {
          map_key    = "${rule_key}.${target_key}"
          rule_key   = rule_key
          target_key = target_key
          arn        = target.arn
          role_arn   = try(target.role_arn, null)
        }
      ]
    ]) :
    target.map_key => target
  }
}
