#!/bin/bash
# Initialize LocalStack S3 bucket for local development

echo "Initializing LocalStack S3..."

# Wait for LocalStack to be ready
sleep 5

# Create S3 bucket
awslocal s3 mb s3://bank-statements-local --region ap-southeast-1

# Enable versioning
awslocal s3api put-bucket-versioning \
  --bucket bank-statements-local \
  --versioning-configuration Status=Enabled

# Set bucket encryption
awslocal s3api put-bucket-encryption \
  --bucket bank-statements-local \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
awslocal s3api put-public-access-block \
  --bucket bank-statements-local \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "LocalStack S3 bucket 'bank-statements-local' created successfully!"
echo "Access via: http://localhost:4566"
echo "Use AWS CLI with --endpoint-url=http://localhost:4566"
