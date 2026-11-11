output "bucket_name" {
  value = aws_s3_bucket.private_assets.id
}

output "bucket_arn" {
  value = aws_s3_bucket.private_assets.arn
}

output "application_iam_policy_json" {
  value     = data.aws_iam_policy_document.application_storage.json
  sensitive = true
}
