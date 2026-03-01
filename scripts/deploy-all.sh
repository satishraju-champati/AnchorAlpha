#!/bin/bash

# AnchorAlpha Complete Deployment Script
# This script deploys the entire AnchorAlpha infrastructure and applications

set -e

# Default values
ENVIRONMENT="prod"
REGION="us-east-1"
SKIP_INFRA=false
SKIP_LAMBDA=false
SKIP_CONTAINER=false
CONFIG_FILE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

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
    -c|--config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    --skip-infra)
      SKIP_INFRA=true
      shift
      ;;
    --skip-lambda)
      SKIP_LAMBDA=true
      shift
      ;;
    --skip-container)
      SKIP_CONTAINER=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Complete deployment script for AnchorAlpha"
      echo ""
      echo "Options:"
      echo "  -e, --environment    Environment (dev/staging/prod) [default: prod]"
      echo "  -r, --region        AWS region [default: us-east-1]"
      echo "  -c, --config        Configuration file path"
      echo "  --skip-infra        Skip infrastructure deployment"
      echo "  --skip-lambda       Skip Lambda function deployment"
      echo "  --skip-container    Skip container deployment"
      echo "  -h, --help          Show this help message"
      echo ""
      echo "Prerequisites:"
      echo "  1. AWS CLI installed and configured"
      echo "  2. Docker installed"
      echo "  3. API keys configured (FMP and Perplexity)"
      echo "  4. Notification email configured"
      echo ""
      echo "Examples:"
      echo "  $0 --environment prod"
      echo "  $0 --environment dev --skip-infra"
      echo "  $0 --config config/deployment-config.json"
      exit 0
      ;;
    *)
      print_error "Unknown option $1"
      exit 1
      ;;
  esac
done

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_status "🚀 Starting AnchorAlpha Complete Deployment"
print_status "Environment: $ENVIRONMENT"
print_status "Region: $REGION"
print_status "Skip Infrastructure: $SKIP_INFRA"
print_status "Skip Lambda: $SKIP_LAMBDA"
print_status "Skip Container: $SKIP_CONTAINER"
echo ""

# Load configuration if provided
if [[ -n "$CONFIG_FILE" ]]; then
  if [[ -f "$CONFIG_FILE" ]]; then
    print_status "📋 Loading configuration from $CONFIG_FILE"
    # Extract values from JSON config file
    NOTIFICATION_EMAIL=$(python3 -c "import json; config=json.load(open('$CONFIG_FILE')); print(config['environments']['$ENVIRONMENT']['notifications']['email'])" 2>/dev/null || echo "")
    FMP_API_KEY=$(python3 -c "import json; config=json.load(open('$CONFIG_FILE')); print(config['environments']['$ENVIRONMENT']['api_keys']['fmp_api_key'])" 2>/dev/null || echo "")
    PERPLEXITY_API_KEY=$(python3 -c "import json; config=json.load(open('$CONFIG_FILE')); print(config['environments']['$ENVIRONMENT']['api_keys']['perplexity_api_key'])" 2>/dev/null || echo "")
  else
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
  fi
fi

# Check for required environment variables
if [[ -z "$NOTIFICATION_EMAIL" ]]; then
  NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-$EMAIL}"
fi

if [[ -z "$FMP_API_KEY" ]]; then
  FMP_API_KEY="${FMP_API_KEY:-}"
fi

if [[ -z "$PERPLEXITY_API_KEY" ]]; then
  PERPLEXITY_API_KEY="${PERPLEXITY_API_KEY:-}"
fi

# Validate prerequisites
print_status "🔍 Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
  print_error "AWS CLI is not installed. Please install it first."
  exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
  print_error "Docker is not installed. Please install it first."
  exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
  print_error "AWS credentials not configured. Please run 'aws configure' first."
  exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_status "AWS Account ID: $AWS_ACCOUNT_ID"

# Validate required parameters for infrastructure deployment
if [[ "$SKIP_INFRA" == false ]]; then
  if [[ -z "$NOTIFICATION_EMAIL" ]]; then
    print_error "NOTIFICATION_EMAIL is required for infrastructure deployment"
    print_status "Set it as an environment variable or use --config option"
    exit 1
  fi

  if [[ -z "$FMP_API_KEY" ]]; then
    print_error "FMP_API_KEY is required for infrastructure deployment"
    print_status "Set it as an environment variable or use --config option"
    exit 1
  fi

  if [[ -z "$PERPLEXITY_API_KEY" ]]; then
    print_error "PERPLEXITY_API_KEY is required for infrastructure deployment"
    print_status "Set it as an environment variable or use --config option"
    exit 1
  fi
fi

print_success "Prerequisites check passed"

cd "$PROJECT_ROOT"

# Step 1: Deploy Infrastructure
if [[ "$SKIP_INFRA" == false ]]; then
  print_status "🏗️  Step 1: Deploying AWS Infrastructure..."
  
  ./infrastructure/scripts/deploy-infrastructure.sh \
    --environment "$ENVIRONMENT" \
    --region "$REGION" \
    --notification-email "$NOTIFICATION_EMAIL" \
    --fmp-api-key "$FMP_API_KEY" \
    --perplexity-api-key "$PERPLEXITY_API_KEY"
  
  if [[ $? -eq 0 ]]; then
    print_success "Infrastructure deployment completed"
  else
    print_error "Infrastructure deployment failed"
    exit 1
  fi
else
  print_warning "Skipping infrastructure deployment"
fi

# Step 2: Deploy Lambda Function
if [[ "$SKIP_LAMBDA" == false ]]; then
  print_status "⚡ Step 2: Deploying Lambda Function..."
  
  ./scripts/deploy-lambda.sh \
    --environment "$ENVIRONMENT" \
    --region "$REGION"
  
  if [[ $? -eq 0 ]]; then
    print_success "Lambda deployment completed"
  else
    print_error "Lambda deployment failed"
    exit 1
  fi
else
  print_warning "Skipping Lambda deployment"
fi

# Step 3: Deploy Streamlit Container
if [[ "$SKIP_CONTAINER" == false ]]; then
  print_status "🐳 Step 3: Deploying Streamlit Container..."
  
  ./infrastructure/scripts/deploy-container.sh \
    --environment "$ENVIRONMENT" \
    --region "$REGION" \
    --power nano \
    --scale 1
  
  if [[ $? -eq 0 ]]; then
    print_success "Container deployment completed"
  else
    print_error "Container deployment failed"
    exit 1
  fi
else
  print_warning "Skipping container deployment"
fi

# Step 4: Deployment Summary
print_status "📊 Deployment Summary"
echo ""

# Get deployment status
print_status "CloudFormation Stack:"
aws cloudformation describe-stacks \
  --stack-name "anchor-alpha-infrastructure-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'Stacks[0].{StackName:StackName,Status:StackStatus,CreationTime:CreationTime}' \
  --output table 2>/dev/null || print_warning "Stack not found"

echo ""
print_status "Lambda Function:"
aws lambda get-function \
  --function-name "anchor-alpha-momentum-processor-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'Configuration.{FunctionName:FunctionName,Runtime:Runtime,LastModified:LastModified,State:State}' \
  --output table 2>/dev/null || print_warning "Function not found"

echo ""
print_status "Lightsail Container:"
CONTAINER_URL=$(aws lightsail get-container-services \
  --service-name "anchor-alpha-streamlit-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'containerServices[0].url' \
  --output text 2>/dev/null || echo "")

if [[ -n "$CONTAINER_URL" && "$CONTAINER_URL" != "None" ]]; then
  aws lightsail get-container-services \
    --service-name "anchor-alpha-streamlit-$ENVIRONMENT" \
    --region "$REGION" \
    --query 'containerServices[0].{Name:serviceName,State:state,Power:power,Scale:scale,URL:url}' \
    --output table
else
  print_warning "Container service not found"
fi

echo ""
print_success "🎉 Deployment Complete!"

if [[ -n "$CONTAINER_URL" && "$CONTAINER_URL" != "None" ]]; then
  print_success "🌐 Streamlit App URL: $CONTAINER_URL"
fi

print_status "📋 Next Steps:"
echo "  1. Monitor CloudWatch logs for Lambda execution"
echo "  2. Verify EventBridge schedule is triggering correctly"
echo "  3. Check S3 bucket for processed data files"
echo "  4. Test the Streamlit application"
echo "  5. Set up monitoring alerts and dashboards"

echo ""
print_status "📚 Useful Commands:"
echo "  View Lambda logs: aws logs tail /aws/lambda/anchor-alpha-momentum-processor-$ENVIRONMENT --follow"
echo "  Test Lambda: aws lambda invoke --function-name anchor-alpha-momentum-processor-$ENVIRONMENT --payload '{}' response.json"
echo "  Check S3 data: aws s3 ls s3://anchor-alpha-momentum-data-$ENVIRONMENT-$AWS_ACCOUNT_ID/"
echo "  Monitor costs: aws budgets describe-budgets --account-id $AWS_ACCOUNT_ID"