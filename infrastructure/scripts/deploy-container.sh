#!/bin/bash

# AnchorAlpha Lightsail Container Deployment Script
# This script builds and deploys the Streamlit app to AWS Lightsail

set -e

# Default values
ENVIRONMENT="prod"
REGION="us-east-1"
SERVICE_NAME="anchor-alpha-streamlit"
SERVICE_POWER="nano"
SERVICE_SCALE=1

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
    -n|--service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    -p|--power)
      SERVICE_POWER="$2"
      shift 2
      ;;
    -s|--scale)
      SERVICE_SCALE="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -e, --environment    Environment (dev/staging/prod) [default: prod]"
      echo "  -r, --region        AWS region [default: us-east-1]"
      echo "  -n, --service-name  Lightsail service name [default: anchor-alpha-streamlit]"
      echo "  -p, --power         Service power (nano/micro/small/medium/large/xlarge) [default: nano]"
      echo "  -s, --scale         Number of instances [default: 1]"
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
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "🚀 Deploying AnchorAlpha Streamlit Container"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME-$ENVIRONMENT"
echo "Power: $SERVICE_POWER"
echo "Scale: $SERVICE_SCALE"
echo ""

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
  echo "❌ AWS CLI is not installed. Please install it first."
  exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo "❌ Docker is not installed. Please install it first."
  exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
  echo "❌ AWS credentials not configured. Please run 'aws configure' first."
  exit 1
fi

# Build Docker image
echo "🐳 Building Docker image..."
cd "$PROJECT_ROOT"

docker build -t anchor-alpha-streamlit:latest -f infrastructure/docker/Dockerfile .

if [[ $? -ne 0 ]]; then
  echo "❌ Docker build failed"
  exit 1
fi

echo "✅ Docker image built successfully"

# Create or update Lightsail container service
echo "☁️  Creating/updating Lightsail container service..."

# Check if service exists
SERVICE_EXISTS=$(aws lightsail get-container-services \
  --region "$REGION" \
  --query "containerServices[?serviceName=='$SERVICE_NAME-$ENVIRONMENT'].serviceName" \
  --output text 2>/dev/null || echo "")

if [[ -z "$SERVICE_EXISTS" ]]; then
  echo "📦 Creating new container service..."
  aws lightsail create-container-service \
    --service-name "$SERVICE_NAME-$ENVIRONMENT" \
    --power "$SERVICE_POWER" \
    --scale "$SERVICE_SCALE" \
    --region "$REGION" \
    --tags key=Project,value=AnchorAlpha key=Environment,value="$ENVIRONMENT" key=Component,value=Frontend
  
  echo "⏳ Waiting for container service to be ready..."
  aws lightsail wait container-service-deployed \
    --service-name "$SERVICE_NAME-$ENVIRONMENT" \
    --region "$REGION"
else
  echo "📦 Container service already exists, will update deployment..."
fi

# Push image to Lightsail
echo "📤 Pushing image to Lightsail..."
aws lightsail push-container-image \
  --service-name "$SERVICE_NAME-$ENVIRONMENT" \
  --label streamlit-app \
  --image anchor-alpha-streamlit:latest \
  --region "$REGION"

# Get the pushed image name
IMAGE_NAME=$(aws lightsail get-container-images \
  --service-name "$SERVICE_NAME-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'containerImages[0].image' \
  --output text)

echo "✅ Image pushed: $IMAGE_NAME"

# Create deployment configuration
echo "🚀 Creating deployment configuration..."
cat > /tmp/containers.json << EOF
{
  "streamlit-app": {
    "image": "$IMAGE_NAME",
    "environment": {
      "ENVIRONMENT": "$ENVIRONMENT",
      "S3_BUCKET": "anchor-alpha-momentum-data-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)"
    },
    "ports": {
      "8501": "HTTP"
    }
  }
}
EOF

cat > /tmp/public-endpoint.json << EOF
{
  "containerName": "streamlit-app",
  "containerPort": 8501,
  "healthCheck": {
    "healthyThreshold": 2,
    "unhealthyThreshold": 2,
    "timeoutSeconds": 5,
    "intervalSeconds": 30,
    "path": "/",
    "successCodes": "200-499"
  }
}
EOF

# Deploy the container
echo "🚀 Deploying container..."
aws lightsail create-container-service-deployment \
  --service-name "$SERVICE_NAME-$ENVIRONMENT" \
  --containers file:///tmp/containers.json \
  --public-endpoint file:///tmp/public-endpoint.json \
  --region "$REGION"

# Clean up temporary files
rm -f /tmp/containers.json /tmp/public-endpoint.json

echo "⏳ Waiting for deployment to complete..."
aws lightsail wait container-service-deployed \
  --service-name "$SERVICE_NAME-$ENVIRONMENT" \
  --region "$REGION"

# Get the service URL
SERVICE_URL=$(aws lightsail get-container-services \
  --service-name "$SERVICE_NAME-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'containerServices[0].url' \
  --output text)

echo ""
echo "✅ Deployment successful!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📊 Service Details:"
aws lightsail get-container-services \
  --service-name "$SERVICE_NAME-$ENVIRONMENT" \
  --region "$REGION" \
  --query 'containerServices[0].{Name:serviceName,State:state,Power:power,Scale:scale,URL:url}' \
  --output table

echo ""
echo "🎉 Container deployment complete!"
echo "Your Streamlit app should be available at: $SERVICE_URL"