############################################
# Normalized bucket configuration
############################################

locals {
  # Keep naming logic in one place so resource blocks and outputs can reuse the
  # same rendered bucket identity without repeating string interpolation.
  bucket_name = "${var.name_prefix}-${var.bucket_name_suffix}"

  # Extend the caller-supplied baseline tags with the rendered Name tag used by
  # this private frontend origin bucket.
  bucket_tags = merge(var.tags, {
    Name = local.bucket_name
  })
}
