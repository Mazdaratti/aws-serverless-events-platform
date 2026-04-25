############################################
# Normalized distribution configuration
############################################

locals {
  # Keep the rendered distribution identity in one place so resource names,
  # tags, and comments stay aligned without repeating string interpolation.
  distribution_name = "${var.name_prefix}-edge"

  # Extend the caller-supplied baseline tags with the rendered Name tag used by
  # this CloudFront distribution.
  distribution_tags = merge(var.tags, {
    Name = local.distribution_name
  })

  # Keep OAC naming close to the distribution name because this OAC exists only
  # to let this distribution read from the private S3 frontend origin.
  s3_origin_access_control_name = "${local.distribution_name}-s3-oac"

  # Keep the SPA rewrite function name tied to the distribution because the
  # function exists only to support this CloudFront frontend routing model.
  spa_rewrite_function_name = "${local.distribution_name}-spa-rewrite"

  # Normalize caller-supplied origin values once so the CloudFront resource can
  # focus on behavior wiring instead of repeated trimming.
  s3_origin_id           = trimspace(var.s3_origin_id)
  s3_origin_domain_name  = trimspace(var.s3_origin_bucket_regional_domain_name)
  api_origin_id          = trimspace(var.api_origin_id)
  api_origin_domain_name = trimspace(var.api_origin_domain_name)
  api_origin_path        = var.api_origin_path == null ? "" : trimspace(var.api_origin_path)

  # Frontend SPA routes are reserved under /app so browser navigation never
  # collides with the /events API contract. CloudFront needs both patterns so
  # exact /app and child paths match the S3 origin behaviors that run the
  # viewer-request rewrite function.
  frontend_app_path_patterns = [
    "/app",
    "/app/*",
  ]

  # The current backend contract deliberately preserves the deployed API route
  # family directly under /events instead of introducing a new /api/* prefix.
  # CloudFront needs both patterns so exact /events and child paths match the
  # API Gateway origin.
  api_path_patterns = [
    "/events",
    "/events/*",
  ]

  # Use AWS managed policies for the first baseline so the module stays small
  # while still using CloudFront's current policy-based cache behavior model.
  static_cache_policy_name       = "Managed-CachingOptimized"
  api_cache_policy_name          = "Managed-CachingDisabled"
  api_origin_request_policy_name = "Managed-AllViewerExceptHostHeader"
}
