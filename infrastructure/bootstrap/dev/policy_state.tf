############################################
# GitHub Actions Terraform state permissions
############################################

data "aws_iam_policy_document" "github_actions_state_permissions" {
  statement {
    sid    = "TerraformStateBucketList"
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.terraform_state.arn
    ]
  }

  statement {
    sid    = "TerraformStateObjectAccess"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]

    resources = [
      "${aws_s3_bucket.terraform_state.arn}/${local.tf_backend_key}"
    ]
  }

  statement {
    sid    = "TerraformStateLockfileAccess"
    effect = "Allow"

    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject"
    ]

    resources = [
      "${aws_s3_bucket.terraform_state.arn}/${local.tf_backend_key}.tflock"
    ]
  }
}

resource "aws_iam_policy" "github_actions_state" {
  name        = "gh-oidc-${local.name_prefix}-state"
  description = "S3 backend state access for the GitHub Actions OIDC role."
  policy      = data.aws_iam_policy_document.github_actions_state_permissions.json

  tags = {
    Name = "gh-oidc-${local.name_prefix}-state"
  }
}

resource "aws_iam_role_policy_attachment" "github_actions_state" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_state.arn
}
