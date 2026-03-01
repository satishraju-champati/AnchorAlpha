#!/bin/bash

# AnchorAlpha Infrastructure Deployment Script
# This script deploys the AWS infrastructure using CloudFormation

set -e

# Default values
ENVIRONMENT="prod"
REGION="us-east-1"
STACK_NAME="anchor-alpha-infrastructure"
NOTIFICATION_EMAIL=""
FMP_API_KEY=""
PERPLEXITY_API_KEY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -r|--region)
      REGION="$2"
      shift 2
      ;;
    -s|--stack-name)
      STACK_NAME="$2"
      shift 2
      ;;
    --notification-email)
      NOTIFICATION_EMAIL="$2"
      shift 2
      ;;
    --fmp-api-key)
      FMP_API_KEY="$2"
      shift 2
      ;;
    --perplexity-api-key)
      PERPLEXITY_API_KEY="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -e, --environment        Environment (dev/staging/prod) [default: prod]"
      echo "  -r, --region            AWS region [default: us-east-1]"
      echo "  -s, --stack-name        CloudFormation stack name [default: anchor-alpha-infrastructure]"
      echo "  --notification-email    Email for notifications (required)"
      echo "  --fmp-api-key          Financial Modeling Prep API key (required)"
      echo "  --perplexity-api-key   Perplexity API key (required)"
      echo "  -h, --help             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Validate required parameters
if [[ -z "$NOTIFICATION_EMAIL" ]]; then
  echo "Error: --notification-email is required"
  exit 1
fi

if [[ -z "$FMP_API_KEY" ]]; then
  echo "Error: --fmp-api-key is required"
  exit 1
fi

if [[ -z "$PERPLEXITY_API_KEY" ]]; then
  echo "Error: --perplexity-api-key is required"
  exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(dirname "$SCRIPT_DIR")/cloudformation"

echo "🚀 Deploying AnchorAlpha Infrastructure"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Stack Name: $STACK_NAME"
echo "Notification Email: $NOTIFICATION_EMAIL"
echo ""

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
  echo "❌ AWS CLI is not installed. Please install it first."
  exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
  echo "❌ AWS credentials not configured. Please run 'aws configure' first."
  exit 1
fi

# Validate CloudFormation template
echo "📋 Validating CloudFormation template..."
aws cloudformation validate-template \
  --template-body file://"$TEMPLATE_DIR/anchor-alpha-infrastructure.yaml" \
  --region "$REGION"

if [[ $? -ne 0 ]]; then
  echo "❌ Template validation failed"
  exit 1
fi

echo "✅ Template validation successful"

# Deploy the stack
echo "🏗️  Deploying infrastructure stack..."
aws cloudformation deploy \
  --template-file "$TEMPLATE_DIR/anchor-alpha-infrastructure.yaml" \
  --stack-name "$STACK_NAME-$ENVIRONMENT" \
  --parameter-overrides \
    Environment="$ENVIRONMENT" \
    FMPApiKey="$FMP_API_KEY" \
    PerplexityApiKey="$PERPLEXITY_API_KEY" \
    NotificationEmail="$NOTIFICATION_EMAIL" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --tags \
    Project=AnchorAlpha \
    Environment="$ENVIRONMENT" \
    ManagedBy=CloudFormation

if [[ $? -eq 0 ]]; then
  echo "✅ Infrastructure deployment successful!"
  
  # Get stack outputs
  echo ""
  echo "📊 Stack Outputs:"
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME-$ENVIRONMENT" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table
else
  echo "❌ Infrastructure deployment failed"
  exit 1
fi

echo ""
echo "🎉 Deployment complete! Next steps:"
echo "1. Build and push your Lambda deployment package"
echo "2. Update the Lambda function code using the AWS CLI or console"
echo "3. Deploy the Streamlit container using deploy-container.sh"
echo "4. Test the EventBridge schedule and monitor CloudWatch logs"