#!/bin/bash

# AnchorAlpha Lambda Function Deployment Script
# This script packages and deploys the Lambda function with all dependencies

set -e

# Default values
ENVIRONMENT="prod"
REGION="us-east-1"
FUNCTION_NAME="anchor-alpha-momentum-processor"
TIMEOUT=900  # 15 minutes
MEMORY=512   # MB

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
    -f|--function-name)
      FUNCTION_NAME="$2"
      shift 2
      ;;
    -t|--timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    -m|--memory)
      MEMORY="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -e, --environment    Environment (dev/staging/prod) [default: prod]"
      echo "  -r, --region        AWS region [default: us-east-1]"
      echo "  -f, --function-name Lambda function name [default: anchor-alpha-momentum-processor]"
      echo "  -t, --timeout       Function timeout in seconds [default: 900]"
      echo "  -m, --memory        Function memory in MB [default: 512]"
      echo "  -h, --help          Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying AnchorAlpha Lambda Function"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Function Name: $FUNCTION_NAME-$ENVIRONMENT"
echo "Timeout: ${TIMEOUT}s"
echo "Memory: ${MEMORY}MB"
echo ""

# Check prerequisites
if ! command -v aws &> /dev/null; then
  echo "❌ AWS CLI is not installed. Please install it first."
  exit 1
fi

if ! command -v python3 &> /dev/null; then
  echo "❌ Python 3 is not installed. Please install it first."
  exit 1
fi

if ! command -v pip &> /dev/null; then
  echo "❌ pip is not installed. Please install it first."
  exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
  echo "❌ AWS credentials not configured. Please run 'aws configure' first."
  exit 1
fi

cd "$PROJECT_ROOT"

# Create deployment package
echo "📦 Creating deployment package..."
"$PROJECT_ROOT/infrastructure/scripts/package-lambda.sh" --environment "$ENVIRONMENT"

# Check if function exists
FUNCTION_EXISTS=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'Configuration.FunctionName' \
  --output text 2>/dev/null || echo "")

if [[ -n "$FUNCTION_EXISTS" ]]; then
  echo "🔄 Updating existing Lambda function..."
  
  # Update function code
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME-$ENVIRONMENT" \
    --zip-file fileb://dist/anchor-alpha-lambda-$ENVIRONMENT.zip \
    --region "$REGION"
  
  # Update function configuration
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME-$ENVIRONMENT" \
    --timeout "$TIMEOUT" \
    --memory-size "$MEMORY" \
    --region "$REGION"
  
  echo "✅ Lambda function updated successfully"
else
  echo "❌ Lambda function $FUNCTION_NAME-$ENVIRONMENT does not exist"
  echo "Please deploy the infrastructure first using:"
  echo "  make deploy-infra ENV=$ENVIRONMENT"
  exit 1
fi

# Wait for function to be updated
echo "⏳ Waiting for function update to complete..."
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME-$ENVIRONMENT" \
  --region "$REGION"

# Test the function
echo "🧪 Testing Lambda function..."
TEST_PAYLOAD='{"source":"deployment-test","environment":"'$ENVIRONMENT'"}'

aws lambda invoke \
  --function-name "$FUNCTION_NAME-$ENVIRONMENT" \
  --region "$REGION" \
  --payload "$TEST_PAYLOAD" \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda-test-response.json

echo "📋 Test Response:"
cat /tmp/lambda-test-response.json | python3 -m json.tool
rm -f /tmp/lambda-test-response.json

# Get function info
echo ""
echo "📊 Function Details:"
aws lambda get-function \
  --function-name "$FUNCTION_NAME-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'Configuration.{FunctionName:FunctionName,Runtime:Runtime,Handler:Handler,CodeSize:CodeSize,Timeout:Timeout,MemorySize:MemorySize,LastModified:LastModified}' \
  --output table

echo ""
echo "✅ Lambda deployment complete!"
echo "🔗 Function ARN: $(aws lambda get-function --function-name $FUNCTION_NAME-$ENVIRONMENT --region $REGION --query 'Configuration.FunctionArn' --output text)"
echo ""
echo "📋 Next steps:"
echo "1. Monitor CloudWatch logs: /aws/lambda/$FUNCTION_NAME-$ENVIRONMENT"
echo "2. Test the EventBridge schedule trigger"
echo "3. Verify S3 data output after the next scheduled run"