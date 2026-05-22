############################################
# GitHub Actions infrastructure deploy policies
############################################
#
# These policies are the default Terraform deployment permission set for the
# current serverless dev environment. They are split across multiple managed
# policies so each policy stays within the IAM managed policy size limit.
#
# Design boundaries:
# - Terraform state access stays separate in policy_state.tf.
# - IAM runtime role management is scoped to project/environment names.
# - iam:PassRole is scoped to project roles and Lambda.
# - Bootstrap OIDC resources remain manually managed by this root.
# - This is not an application artifact deployment policy.
############################################

data "aws_iam_policy_document" "github_actions_deploy_core_permissions" {
  ##########################################
  # AWS provider/account discovery
  ##########################################
  statement {
    sid    = "TerraformReadAccountContext"
    effect = "Allow"

    actions = [
      "sts:GetCallerIdentity"
    ]

    resources = ["*"]
  }

  ##########################################
  # DynamoDB event and RSVP tables
  ##########################################
  statement {
    sid    = "TerraformDeployDynamoDB"
    effect = "Allow"

    actions = [
      "dynamodb:CreateTable",
      "dynamodb:DeleteTable",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:DescribeTable",
      "dynamodb:DescribeTimeToLive",
      "dynamodb:ListTagsOfResource",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
      "dynamodb:UpdateContinuousBackups",
      "dynamodb:UpdateTable",
      "dynamodb:UpdateTimeToLive"
    ]

    resources = ["*"]
  }

  ##########################################
  # SQS queues, DLQs, and queue policies
  ##########################################
  statement {
    sid    = "TerraformDeploySQS"
    effect = "Allow"

    actions = [
      "sqs:AddPermission",
      "sqs:CreateQueue",
      "sqs:DeleteQueue",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ListDeadLetterSourceQueues",
      "sqs:ListQueueTags",
      "sqs:ListQueues",
      "sqs:RemovePermission",
      "sqs:SetQueueAttributes",
      "sqs:TagQueue",
      "sqs:UntagQueue"
    ]

    resources = ["*"]
  }

  ##########################################
  # EventBridge bus, rules, and targets
  ##########################################
  statement {
    sid    = "TerraformDeployEventBridge"
    effect = "Allow"

    actions = [
      "events:CreateEventBus",
      "events:DeleteEventBus",
      "events:DeleteRule",
      "events:DescribeEventBus",
      "events:DescribeRule",
      "events:ListTagsForResource",
      "events:ListTargetsByRule",
      "events:PutRule",
      "events:PutTargets",
      "events:RemoveTargets",
      "events:TagResource",
      "events:UntagResource"
    ]

    resources = ["*"]
  }

  ##########################################
  # SNS admin topic, policies, and subscriptions
  ##########################################
  statement {
    sid    = "TerraformDeploySNS"
    effect = "Allow"

    actions = [
      "sns:CreateTopic",
      "sns:DeleteTopic",
      "sns:GetSubscriptionAttributes",
      "sns:GetTopicAttributes",
      "sns:ListSubscriptions",
      "sns:ListSubscriptionsByTopic",
      "sns:ListTagsForResource",
      "sns:SetSubscriptionAttributes",
      "sns:SetTopicAttributes",
      "sns:Subscribe",
      "sns:TagResource",
      "sns:Unsubscribe",
      "sns:UntagResource"
    ]

    resources = ["*"]
  }

  ##########################################
  # SES sender identity and templates
  ##########################################
  statement {
    sid    = "TerraformDeploySES"
    effect = "Allow"

    actions = [
      "ses:CreateTemplate",
      "ses:DeleteIdentity",
      "ses:DeleteTemplate",
      "ses:GetIdentityVerificationAttributes",
      "ses:GetTemplate",
      "ses:ListIdentities",
      "ses:ListTagsForResource",
      "ses:ListTemplates",
      "ses:TagResource",
      "ses:UntagResource",
      "ses:UpdateTemplate",
      "ses:VerifyEmailIdentity"
    ]

    resources = ["*"]
  }

  ##########################################
  # Cognito user pool, app client, and groups
  ##########################################
  statement {
    sid    = "TerraformDeployCognito"
    effect = "Allow"

    actions = [
      "cognito-idp:CreateGroup",
      "cognito-idp:CreateUserPool",
      "cognito-idp:CreateUserPoolClient",
      "cognito-idp:DeleteGroup",
      "cognito-idp:DeleteUserPool",
      "cognito-idp:DeleteUserPoolClient",
      "cognito-idp:DescribeUserPool",
      "cognito-idp:DescribeUserPoolClient",
      "cognito-idp:GetGroup",
      "cognito-idp:ListGroups",
      "cognito-idp:ListTagsForResource",
      "cognito-idp:TagResource",
      "cognito-idp:UntagResource",
      "cognito-idp:UpdateGroup",
      "cognito-idp:UpdateUserPool",
      "cognito-idp:UpdateUserPoolClient"
    ]

    resources = ["*"]
  }
}

data "aws_iam_policy_document" "github_actions_deploy_compute_observability_permissions" {

  ##########################################
  # Lambda functions, permissions, and SQS mappings
  ##########################################
  statement {
    sid    = "TerraformDeployLambda"
    effect = "Allow"

    actions = [
      "lambda:AddPermission",
      "lambda:CreateEventSourceMapping",
      "lambda:CreateFunction",
      "lambda:DeleteEventSourceMapping",
      "lambda:DeleteFunction",
      "lambda:GetEventSourceMapping",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionUrlConfig",
      "lambda:GetPolicy",
      "lambda:GetRuntimeManagementConfig",
      "lambda:ListEventSourceMappings",
      "lambda:ListFunctions",
      "lambda:ListTags",
      "lambda:ListVersionsByFunction",
      "lambda:RemovePermission",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:UpdateEventSourceMapping",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration"
    ]

    resources = ["*"]
  }

  ##########################################
  # CloudWatch Logs and observability resources
  ##########################################
  statement {
    sid    = "TerraformDeployCloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:DeleteRetentionPolicy",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:ListTagsForResource",
      "logs:PutRetentionPolicy",
      "logs:TagResource",
      "logs:UntagResource"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "TerraformDeployCloudWatchObservability"
    effect = "Allow"

    actions = [
      "cloudwatch:DeleteAlarms",
      "cloudwatch:DeleteDashboards",
      "cloudwatch:DescribeAlarms",
      "cloudwatch:GetDashboard",
      "cloudwatch:ListDashboards",
      "cloudwatch:ListTagsForResource",
      "cloudwatch:PutDashboard",
      "cloudwatch:PutMetricAlarm",
      "cloudwatch:TagResource",
      "cloudwatch:UntagResource"
    ]

    resources = ["*"]
  }

  ##########################################
  # API Gateway HTTP API
  ##########################################
  statement {
    sid    = "TerraformDeployApiGateway"
    effect = "Allow"

    actions = [
      "apigateway:DELETE",
      "apigateway:GET",
      "apigateway:PATCH",
      "apigateway:POST",
      "apigateway:PUT"
    ]

    resources = ["*"]
  }
}

data "aws_iam_policy_document" "github_actions_deploy_edge_storage_permissions" {

  ##########################################
  # S3 frontend origin bucket and bucket policy
  ##########################################
  statement {
    sid    = "TerraformDeployS3"
    effect = "Allow"

    actions = [
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:DeleteBucketEncryption",
      "s3:DeleteBucketOwnershipControls",
      "s3:DeleteBucketPolicy",
      "s3:DeleteBucketPublicAccessBlock",
      "s3:DeleteBucketTagging",
      "s3:GetBucketAcl",
      "s3:GetBucketCORS",
      "s3:GetBucketLocation",
      "s3:GetBucketLogging",
      "s3:GetBucketOwnershipControls",
      "s3:GetBucketPolicy",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetBucketTagging",
      "s3:GetBucketVersioning",
      "s3:GetEncryptionConfiguration",
      "s3:ListAllMyBuckets",
      "s3:ListBucket",
      "s3:PutBucketOwnershipControls",
      "s3:PutBucketPolicy",
      "s3:PutBucketPublicAccessBlock",
      "s3:PutBucketTagging",
      "s3:PutBucketVersioning",
      "s3:PutEncryptionConfiguration"
    ]

    resources = ["*"]
  }

  ##########################################
  # CloudFront distribution, OAC, and function
  ##########################################
  statement {
    sid    = "TerraformDeployCloudFront"
    effect = "Allow"

    actions = [
      "cloudfront:CreateDistribution",
      "cloudfront:CreateFunction",
      "cloudfront:CreateOriginAccessControl",
      "cloudfront:DeleteDistribution",
      "cloudfront:DeleteFunction",
      "cloudfront:DeleteOriginAccessControl",
      "cloudfront:DescribeFunction",
      "cloudfront:GetCachePolicy",
      "cloudfront:GetDistribution",
      "cloudfront:GetDistributionConfig",
      "cloudfront:GetFunction",
      "cloudfront:GetOriginAccessControl",
      "cloudfront:GetOriginAccessControlConfig",
      "cloudfront:GetOriginRequestPolicy",
      "cloudfront:ListCachePolicies",
      "cloudfront:ListDistributions",
      "cloudfront:ListFunctions",
      "cloudfront:ListOriginAccessControls",
      "cloudfront:ListOriginRequestPolicies",
      "cloudfront:ListTagsForResource",
      "cloudfront:PublishFunction",
      "cloudfront:TagResource",
      "cloudfront:UntagResource",
      "cloudfront:UpdateDistribution",
      "cloudfront:UpdateFunction",
      "cloudfront:UpdateOriginAccessControl"
    ]

    resources = ["*"]
  }

  ##########################################
  # Optional CloudFront-scoped WAF baseline
  ##########################################
  statement {
    sid    = "TerraformDeployWAFv2"
    effect = "Allow"

    actions = [
      "wafv2:CheckCapacity",
      "wafv2:CreateWebACL",
      "wafv2:DeleteWebACL",
      "wafv2:GetWebACL",
      "wafv2:ListAvailableManagedRuleGroups",
      "wafv2:ListTagsForResource",
      "wafv2:ListWebACLs",
      "wafv2:TagResource",
      "wafv2:UntagResource",
      "wafv2:UpdateWebACL"
    ]

    resources = ["*"]
  }
}

data "aws_iam_policy_document" "github_actions_deploy_iam_permissions" {

  ##########################################
  # Runtime IAM roles and policies managed by envs/dev
  ##########################################
  statement {
    sid    = "TerraformDeployRuntimeIAM"
    effect = "Allow"

    actions = [
      "iam:AttachRolePolicy",
      "iam:CreatePolicy",
      "iam:CreatePolicyVersion",
      "iam:CreateRole",
      "iam:DeletePolicy",
      "iam:DeletePolicyVersion",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:DetachRolePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListEntitiesForPolicy",
      "iam:ListInstanceProfilesForRole",
      "iam:ListPolicyVersions",
      "iam:ListRolePolicies",
      "iam:ListRoleTags",
      "iam:PutRolePolicy",
      "iam:SetDefaultPolicyVersion",
      "iam:TagPolicy",
      "iam:TagRole",
      "iam:UntagPolicy",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:UpdateRole"
    ]

    resources = [
      "arn:aws:iam::*:role/${local.name_prefix}-*",
      "arn:aws:iam::*:policy/${local.name_prefix}-*"
    ]
  }

  statement {
    sid    = "TerraformPassRuntimeRolesToLambda"
    effect = "Allow"

    actions = [
      "iam:PassRole"
    ]

    resources = [
      "arn:aws:iam::*:role/${local.name_prefix}-*"
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }

  statement {
    sid    = "TerraformReadIAMContext"
    effect = "Allow"

    actions = [
      "iam:GetPolicy",
      "iam:GetRole",
      "iam:ListPolicies",
      "iam:ListRoles"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "github_actions_deploy" {
  name        = "gh-oidc-${local.name_prefix}-deploy"
  description = "Core infrastructure deployment permissions for the dev serverless platform."
  policy      = data.aws_iam_policy_document.github_actions_deploy_core_permissions.json

  tags = {
    Name = "gh-oidc-${local.name_prefix}-deploy"
  }
}

resource "aws_iam_role_policy_attachment" "github_actions_deploy" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_deploy.arn
}

resource "aws_iam_policy" "github_actions_deploy_compute_observability" {
  name        = "gh-oidc-${local.name_prefix}-deploy-compute-observability"
  description = "Lambda, API Gateway, CloudWatch Logs, and CloudWatch observability deployment permissions for the dev serverless platform."
  policy      = data.aws_iam_policy_document.github_actions_deploy_compute_observability_permissions.json

  tags = {
    Name = "gh-oidc-${local.name_prefix}-deploy-compute-observability"
  }
}

resource "aws_iam_role_policy_attachment" "github_actions_deploy_compute_observability" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_deploy_compute_observability.arn
}

resource "aws_iam_policy" "github_actions_deploy_edge_storage" {
  name        = "gh-oidc-${local.name_prefix}-deploy-edge-storage"
  description = "S3, CloudFront, and WAF deployment permissions for the dev serverless platform."
  policy      = data.aws_iam_policy_document.github_actions_deploy_edge_storage_permissions.json

  tags = {
    Name = "gh-oidc-${local.name_prefix}-deploy-edge-storage"
  }
}

resource "aws_iam_role_policy_attachment" "github_actions_deploy_edge_storage" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_deploy_edge_storage.arn
}

resource "aws_iam_policy" "github_actions_deploy_iam" {
  name        = "gh-oidc-${local.name_prefix}-deploy-iam"
  description = "Runtime IAM deployment permissions for the dev serverless platform."
  policy      = data.aws_iam_policy_document.github_actions_deploy_iam_permissions.json

  tags = {
    Name = "gh-oidc-${local.name_prefix}-deploy-iam"
  }
}

resource "aws_iam_role_policy_attachment" "github_actions_deploy_iam" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_deploy_iam.arn
}
