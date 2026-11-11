terraform {
  required_version = ">= 1.8.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

resource "aws_s3_bucket" "private_assets" {
  bucket_prefix = "${var.project_name}-${var.environment}-private-"
  force_destroy = var.force_destroy

  tags = {
    Application = var.project_name
    Environment = var.environment
    DataClass   = "customer-private"
  }
}

resource "aws_s3_bucket_public_access_block" "private_assets" {
  bucket = aws_s3_bucket.private_assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "private_assets" {
  bucket = aws_s3_bucket.private_assets.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "private_assets" {
  bucket = aws_s3_bucket.private_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "private_assets" {
  bucket = aws_s3_bucket.private_assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_cors_configuration" "private_assets" {
  count  = length(var.allowed_origins) > 0 ? 1 : 0
  bucket = aws_s3_bucket.private_assets.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag", "Content-Length", "Content-Type"]
    max_age_seconds = 300
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "private_assets" {
  bucket = aws_s3_bucket.private_assets.id

  rule {
    id     = "expire-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "expire-database-backups"
    status = "Enabled"

    filter {
      prefix = "database-backups/"
    }

    expiration {
      days = 30
    }
  }
}

data "aws_iam_policy_document" "application_storage" {
  statement {
    sid = "TenantObjectAccess"
    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.private_assets.arn}/organizations/*"]
  }

  statement {
    sid = "DatabaseBackupAccess"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.private_assets.arn}/database-backups/*"]
  }

  statement {
    sid       = "BucketReadiness"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.private_assets.arn]
  }
}
