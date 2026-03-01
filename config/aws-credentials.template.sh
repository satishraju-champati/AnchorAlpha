#!/bin/bash

# AnchorAlpha AWS Credentials Configuration Template
# Copy this file to aws-credentials.sh and fill in your actual values
# DO NOT commit the actual credentials file to version control

# AWS Account Configuration
export AWS_ACCOUNT_ID="123456789012"  # Replace with your AWS account ID
export AWS_DEFAULT_REGION="us-east-1"
export AWS_REGION="us-east-1"

# AWS CLI Profile (optional - use if you have multiple AWS profiles)
# export AWS_PROFILE="anchoralpha"

# API Keys (store these in AWS Secrets Manager for production)
export FMP_API_KEY="your_fmp_api_key_here"
export PERPLEXITY_API_KEY="your_perplexity_api_key_here"

# Notification Email
export NOTIFICATION_EMAIL="your-email@example.com"

# Environment-specific S3 bucket names
export S3_BUCKET_DEV="anchor-alpha-momentum-data-dev-${AWS_ACCOUNT_ID}"
export S3_BUCKET_STAGING="anchor-alpha-momentum-data-staging-${AWS_ACCOUNT_ID}"
export S3_BUCKET_PROD="anchor-alpha-momentum-data-prod-${AWS_ACCOUNT_ID}"

# Lambda Configuration
export LAMBDA_TIMEOUT="900"  # 15 minutes
export LAMBDA_MEMORY="512"   # MB

# Lightsail Configuration
export LIGHTSAIL_POWER="nano"  # nano, micro, small, medium, large, xlarge
export LIGHTSAIL_SCALE="1"     # Number of instances

echo "✅ AWS credentials and configuration loaded"
echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Notification Email: $NOTIFICATION_EMAIL"