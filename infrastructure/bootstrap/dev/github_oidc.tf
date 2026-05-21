############################################
# GitHub Actions OIDC provider
############################################

resource "aws_iam_openid_connect_provider" "github" {
  url = local.oidc_url

  client_id_list = [
    "sts.amazonaws.com"
  ]

  # IAM requires a thumbprint list for OIDC providers. This value is the
  # documented GitHub Actions OIDC provider thumbprint commonly used for
  # token.actions.githubusercontent.com.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1"
  ]

  tags = {
    Name = "${local.name_prefix}-github-oidc-provider"
  }
}

############################################
# GitHub Actions OIDC role trust
############################################

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    sid     = "GitHubActionsAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Keep trust branch-scoped until a GitHub Actions workflow needs a
    # GitHub Environment subject such as `environment: dev`.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.github_branch_subject]
    }
  }
}

############################################
# GitHub Actions OIDC role
############################################

resource "aws_iam_role" "github_actions" {
  name               = "gh-oidc-${local.name_prefix}"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json

  permissions_boundary = var.create_permissions_boundary ? aws_iam_policy.github_actions_boundary[0].arn : null

  tags = {
    Name = "${local.name_prefix}-github-actions"
  }
}
