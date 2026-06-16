############################################
# Private frontend origin bucket
############################################

resource "aws_s3_bucket" "this" {
  # This private bucket stores frontend assets served through CloudFront.
  # CloudFront access policy wiring remains caller-owned because it depends on
  # the consuming distribution ARN.
  bucket        = local.bucket_name
  force_destroy = var.force_destroy

  tags = local.bucket_tags
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  # CloudFront is the public entry point, so direct public-access paths remain
  # blocked at the bucket level.
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "this" {
  # Attach public-access blocking first so the bucket's protection is
  # already in place before additional bucket-side controls are applied.
  depends_on = [aws_s3_bucket_public_access_block.this]

  bucket = aws_s3_bucket.this.id

  rule {
    # BucketOwnerEnforced disables ACL-based ownership behavior entirely, which
    # keeps this private origin bucket on the simpler modern ownership model.
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      # SSE-S3 encrypts objects at rest without introducing caller-managed KMS
      # key ownership or additional key-management requirements.
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    # Versioning lets callers choose between rollback-friendly object history
    # and suspended versioning.
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}
