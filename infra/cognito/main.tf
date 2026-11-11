resource "aws_cognito_user_pool" "groundsops" {
  name                     = "groundsops-${var.environment}"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                   = false
    name                      = "organization_id"
    required                  = false

    string_attribute_constraints {
      min_length = 36
      max_length = 36
    }
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "groundsops-web-${var.environment}"
  user_pool_id = aws_cognito_user_pool.groundsops.id

  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  explicit_auth_flows                  = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  access_token_validity                = 60
  id_token_validity                    = 60
  refresh_token_validity               = 30
  auth_session_validity                = 3
  supported_identity_providers         = ["COGNITO"]

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

# Members of this group see Platform admin in the app and can create customer workspaces.
resource "aws_cognito_user_group" "platform_admins" {
  name         = "groundsops-platform-admins"
  user_pool_id = aws_cognito_user_pool.groundsops.id
  description  = "GroundsOps operators who can create and manage customer workspaces"
}
