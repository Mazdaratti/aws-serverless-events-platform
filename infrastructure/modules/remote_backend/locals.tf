############################################
# Normalized backend configuration
############################################

locals {
  # Keep the rendered backend bucket name in one place so the S3 resources and
  # outputs all use the same value. Callers can provide an explicit globally
  # unique bucket name, or let the module derive one from the environment
  # prefix plus a short random suffix.
  state_bucket_name = coalesce(
    var.state_bucket_name,
    "${var.name_prefix}-tf-state-${random_id.bucket_suffix.hex}"
  )

  # Extend the caller-supplied baseline tags with the rendered Name tag used by
  # the Terraform state bucket.
  state_bucket_tags = merge(var.tags, {
    Name = local.state_bucket_name
  })
}
