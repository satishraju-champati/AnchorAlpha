#!/bin/bash

# AnchorAlpha Production Deployment Script
# Simplified deployment using configuration file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/deployment-config.prod.json"

print_status "🚀 AnchorAlpha Production Deployment"
echo ""

# Check if config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
  print_error "Configuration file not found: $CONFIG_FILE"
  print_status "Please copy and fill out the configuration template:"
  print_status "cp config/deployment-config.template.json config/deployment-config.prod.json"
  exit 1
fi

# Extract configuration values
print_status "📋 Loading configuration from $CONFIG_FILE"

NOTIFICATION_EMAIL=$(python3 -c "import json; config=json.load(open('$CONFIG_FILE')); print(config['notifications']['email'])")
FMP_API_KEY=$(python3 -c "import json; config=json.load(open('$CONFIG_FILE')); print(config['api_keys']['fmp_api_key'])")
PERPLEXITY_API_KEY=$(python3 -c "import json; config=json.load(open('$CONFIG_FILE')); print(config['api_keys']['perplexity_api_key'])")

# Validate configuration
if [[ "$NOTIFICATION_EMAIL" == "your-email@example.com" ]]; then
  print_error "Please update the notification email in $CONFIG_FILE"
  exit 1
fi

if [[ "$FMP_API_KEY" == "YOUR_FMP_API_KEY_HERE" ]]; then
  print_error "Please update the FMP API key in $CONFIG_FILE"
  exit 1
fi

if [[ "$PERPLEXITY_API_KEY" == "YOUR_PERPLEXITY_API_KEY_HERE" ]]; then
  print_error "Please update the Perplexity API key in $CONFIG_FILE"
  exit 1
fi

print_success "Configuration loaded successfully"
print_status "Email: $NOTIFICATION_EMAIL"
print_status "FMP API Key: ${FMP_API_KEY:0:10}..."
print_status "Perplexity API Key: ${PERPLEXITY_API_KEY:0:10}..."
echo ""

# Change to project directory
cd "$PROJECT_ROOT"

# Check prerequisites
print_status "🔍 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
  print_error "AWS CLI not found. Please install it first."
  exit 1
fi

if ! command -v docker &> /dev/null; then
  print_error "Docker not found. Please install it first."
  exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
  print_error "AWS credentials not configured. Please run 'aws configure' first."
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "Prerequisites check passed"
print_status "AWS Account ID: $AWS_ACCOUNT_ID"
echo ""

# Export environment variables
export NOTIFICATION_EMAIL="$NOTIFICATION_EMAIL"
export FMP_API_KEY="$FMP_API_KEY"
export PERPLEXITY_API_KEY="$PERPLEXITY_API_KEY"

# Run deployment
print_status "🚀 Starting deployment..."
./scripts/deploy-all.sh --environment prod

# Check deployment status
print_status "📊 Checking deployment status..."
make status ENV=prod

# Get Streamlit URL
print_status "🌐 Getting Streamlit dashboard URL..."
STREAMLIT_URL=$(aws lightsail get-container-services \
  --service-name anchor-alpha-streamlit-prod \
  --query 'containerServices[0].url' \
  --output text 2>/dev/null || echo "")

echo ""
print_success "🎉 Deployment Complete!"
echo ""
print_status "📋 Deployment Summary:"
echo "  • Environment: prod"
echo "  • AWS Account: $AWS_ACCOUNT_ID"
echo "  • Budget Limit: $10/month"
echo "  • Notification Email: $NOTIFICATION_EMAIL"

if [[ -n "$STREAMLIT_URL" && "$STREAMLIT_URL" != "None" ]]; then
  echo "  • Dashboard URL: $STREAMLIT_URL"
else
  echo "  • Dashboard: Deploying (check status in a few minutes)"
fi

echo ""
print_status "📚 Next Steps:"
echo "  1. Wait 5-10 minutes for container deployment to complete"
echo "  2. Visit the dashboard URL above"
echo "  3. Check email for budget alert confirmation"
echo "  4. Monitor first Lambda execution tonight at 9:30 PM UTC"
echo ""
print_status "📊 Monitoring Commands:"
echo "  • Check status: make status ENV=prod"
echo "  • View logs: make logs ENV=prod"
echo "  • Test Lambda: make test-lambda ENV=prod"
echo ""
print_success "Happy momentum screening! 📈"