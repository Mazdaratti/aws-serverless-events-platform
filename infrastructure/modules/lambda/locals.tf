############################################
# Normalized function configuration
############################################

locals {
  # These defaults keep the module input small while still making the deployed
  # Lambda shape explicit and easy to reason about.
  function_defaults = {
    memory_size           = 128
    timeout               = 3
    environment_variables = {}
    log_retention_in_days = 14
  }

  # Normalize the caller input once so the rest of the module can work with a
  # fully-populated function map.
  normalized_functions = {
    for function_key, function in var.functions :
    function_key => {
      description           = function.description
      role_arn              = function.role_arn
      runtime               = function.runtime
      handler               = function.handler
      package_path          = function.package_path
      memory_size           = coalesce(function.memory_size, local.function_defaults.memory_size)
      timeout               = coalesce(function.timeout, local.function_defaults.timeout)
      environment_variables = coalesce(function.environment_variables, local.function_defaults.environment_variables)
      log_retention_in_days = coalesce(function.log_retention_in_days, local.function_defaults.log_retention_in_days)
    }
  }

  # Render stable Lambda and CloudWatch Logs names from the shared prefix and
  # logical function key.
  rendered_function_names = {
    for function_key in keys(local.normalized_functions) :
    function_key => "${var.name_prefix}-${function_key}"
  }

  rendered_log_group_names = {
    for function_key in keys(local.normalized_functions) :
    function_key => "/aws/lambda/${local.rendered_function_names[function_key]}"
  }

  # Enrich each normalized function with its rendered names and package hash so
  # resource blocks can stay concise.
  resolved_functions = {
    for function_key, function in local.normalized_functions :
    function_key => merge(function, {
      function_name    = local.rendered_function_names[function_key]
      log_group_name   = local.rendered_log_group_names[function_key]
      source_code_hash = filebase64sha256(function.package_path)
    })
  }
}
