############################################
# Dev Terraform state bucket
############################################

resource "random_id" "bucket_suffix" {
  # S3 bucket names are globally unique. The suffix is only used when operators
  # do not provide an explicit state_bucket_name for the dev bootstrap root.
  byte_length = 4
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = local.state_bucket_name

  # Dev bootstrap is intentionally teardown-friendly. The persistent
  # remote_backend module uses prevent_destroy, but this root must be easy to
  # recreate while the project validates the remote-state lifecycle.
  force_destroy = true

  tags = {
    Name = local.state_bucket_name
  }
}

############################################
# Dev Terraform state bucket protections
############################################

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
