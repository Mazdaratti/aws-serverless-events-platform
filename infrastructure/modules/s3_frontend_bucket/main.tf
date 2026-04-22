############################################
# Private frontend origin bucket baseline
############################################

resource "aws_s3_bucket" "this" {
  # This is the private bucket that will later act as the CloudFront origin
  # for frontend assets. The module intentionally creates only the bucket
  # baseline here and leaves CloudFront-specific access policy wiring for a
  # later step.
  bucket        = local.bucket_name
  force_destroy = var.force_destroy

  tags = local.bucket_tags
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  # The frontend bucket must not be directly public. CloudFront will become the
  # intended public entry point later, so all direct public-access paths are
  # blocked at the bucket level now.
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "this" {
  # Attach public-access blocking first so the bucket's baseline protection is
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
      # SSE-S3 keeps the baseline encrypted at rest without introducing KMS key
      # management or extra cost/complexity in this first origin-bucket step.
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    # Versioning is exposed as a small module input so environments can decide
    # whether they want rollback-friendly object history or the leaner
    # non-versioned baseline.
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}
