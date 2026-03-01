#!/bin/bash

# AnchorAlpha Configuration Validation Script
# Validates that all required configuration is in place before deployment

set -e

echo "🔍 AnchorAlpha Configuration Validation"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed"
    echo "   Install it from: https://aws.amazon.com/cli/"
    exit 1
else
    echo "✅ AWS CLI is installed"
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
    exit 1
else
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    REGION=$(aws configure get region)
    echo "✅ AWS credentials configured"
    echo "   Account ID: $ACCOUNT_ID"
    echo "   Region: $REGION"
fi

# Check Docker (for container deployment)
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed (required for container deployment)"
    echo "   Install it from: https://docker.com/"
else
    echo "✅ Docker is installed"
fi

# Check required environment variables
echo ""
echo "📋 Environment Variables Check:"

if [[ -z "${NOTIFICATION_EMAIL:-}" ]]; then
    echo "❌ NOTIFICATION_EMAIL not set"
    echo "   export NOTIFICATION_EMAIL=your-email@example.com"
else
    echo "✅ NOTIFICATION_EMAIL: $NOTIFICATION_EMAIL"
fi

if [[ -z "${FMP_API_KEY:-}" ]]; then
    echo "❌ FMP_API_KEY not set"
    echo "   export FMP_API_KEY=your_fmp_api_key"
else
    echo "✅ FMP_API_KEY: ${FMP_API_KEY:0:10}..."
fi

if [[ -z "${PERPLEXITY_API_KEY:-}" ]]; then
    echo "❌ PERPLEXITY_API_KEY not set"
    echo "   export PERPLEXITY_API_KEY=your_perplexity_api_key"
else
    echo "✅ PERPLEXITY_API_KEY: ${PERPLEXITY_API_KEY:0:10}..."
fi

# Check AWS permissions
echo ""
echo "🔐 AWS Permissions Check:"

# Check CloudFormation permissions
if aws cloudformation list-stacks --max-items 1 &> /dev/null; then
    echo "✅ CloudFormation permissions"
else
    echo "❌ CloudFormation permissions missing"
fi

# Check Lambda permissions
if aws lambda list-functions --max-items 1 &> /dev/null; then
    echo "✅ Lambda permissions"
else
    echo "❌ Lambda permissions missing"
fi

# Check S3 permissions
if aws s3 ls &> /dev/null; then
    echo "✅ S3 permissions"
else
    echo "❌ S3 permissions missing"
fi

# Check Lightsail permissions
if aws lightsail get-regions &> /dev/null; then
    echo "✅ Lightsail permissions"
else
    echo "❌ Lightsail permissions missing"
fi

# Check Secrets Manager permissions
if aws secretsmanager list-secrets --max-results 1 &> /dev/null; then
    echo "✅ Secrets Manager permissions"
else
    echo "❌ Secrets Manager permissions missing"
fi

# Validate CloudFormation templates
echo ""
echo "📋 Template Validation:"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(dirname "$SCRIPT_DIR")/cloudformation"

if aws cloudformation validate-template --template-body file://"$TEMPLATE_DIR/anchor-alpha-infrastructure.yaml" &> /dev/null; then
    echo "✅ Infrastructure template is valid"
else
    echo "❌ Infrastructure template validation failed"
fi

if aws cloudformation validate-template --template-body file://"$TEMPLATE_DIR/lightsail-container.yaml" &> /dev/null; then
    echo "✅ Container template is valid"
else
    echo "❌ Container template validation failed"
fi

echo ""
echo "🎯 Configuration Summary:"
echo "   Ready for deployment: $(if [[ -n "${NOTIFICATION_EMAIL:-}" && -n "${FMP_API_KEY:-}" && -n "${PERPLEXITY_API_KEY:-}" ]]; then echo "✅ YES"; else echo "❌ NO"; fi)"
echo ""

if [[ -n "${NOTIFICATION_EMAIL:-}" && -n "${FMP_API_KEY:-}" && -n "${PERPLEXITY_API_KEY:-}" ]]; then
    echo "🚀 You're ready to deploy! Run:"
    echo "   make deploy-all ENV=prod NOTIFICATION_EMAIL=$NOTIFICATION_EMAIL FMP_API_KEY=\$FMP_API_KEY PERPLEXITY_API_KEY=\$PERPLEXITY_API_KEY"
else
    echo "⚠️  Please set the missing environment variables before deployment"
fi