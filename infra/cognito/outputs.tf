output "user_pool_id" {
  value = aws_cognito_user_pool.groundsops.id
}

output "web_client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "issuer" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.groundsops.id}"
}

output "jwks_url" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.groundsops.id}/.well-known/jwks.json"
}

output "platform_admin_group" {
  value = aws_cognito_user_group.platform_admins.name
}
