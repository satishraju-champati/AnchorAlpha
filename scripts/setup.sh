#!/bin/bash

# AnchorAlpha Setup Script
# This script helps users set up the AnchorAlpha application for deployment

set -e

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

print_header() {
  echo ""
  echo "=============================================="
  echo "$1"
  echo "=============================================="
}

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header "🚀 AnchorAlpha Setup Wizard"

print_status "Welcome to the AnchorAlpha setup wizard!"
print_status "This script will help you configure and deploy the AnchorAlpha momentum screening application."
echo ""

# Step 1: Check prerequisites
print_header "📋 Step 1: Checking Prerequisites"

# Check Python
if command -v python3 &> /dev/null; then
  PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
  print_success "Python 3 found: $PYTHON_VERSION"
else
  print_error "Python 3 is not installed. Please install Python 3.11 or later."
  exit 1
fi

# Check pip
if command -v pip &> /dev/null; then
  print_success "pip found"
else
  print_error "pip is not installed. Please install pip."
  exit 1
fi

# Check AWS CLI
if command -v aws &> /dev/null; then
  AWS_VERSION=$(aws --version | cut -d' ' -f1)
  print_success "AWS CLI found: $AWS_VERSION"
else
  print_error "AWS CLI is not installed. Please install AWS CLI v2."
  print_status "Installation guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
  exit 1
fi

# Check Docker
if command -v docker &> /dev/null; then
  DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,//')
  print_success "Docker found: $DOCKER_VERSION"
  
  # Check if Docker daemon is running
  if docker info &> /dev/null; then
    print_success "Docker daemon is running"
  else
    print_warning "Docker daemon is not running. Please start Docker."
  fi
else
  print_error "Docker is not installed. Please install Docker."
  print_status "Installation guide: https://docs.docker.com/get-docker/"
  exit 1
fi

# Check AWS credentials
if aws sts get-caller-identity &> /dev/null; then
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  AWS_USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
  print_success "AWS credentials configured"
  print_status "Account ID: $AWS_ACCOUNT_ID"
  print_status "User/Role: $AWS_USER_ARN"
else
  print_error "AWS credentials not configured. Please run 'aws configure' first."
  exit 1
fi

print_success "All prerequisites met!"

# Step 2: Environment setup
print_header "🔧 Step 2: Environment Configuration"

cd "$PROJECT_ROOT"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
  print_status "Creating Python virtual environment..."
  python3 -m venv venv
  print_success "Virtual environment created"
else
  print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Dependencies installed"

# Step 3: Configuration files
print_header "⚙️ Step 3: Configuration Setup"

# Create config directory if it doesn't exist
mkdir -p config

# Copy configuration templates
if [[ ! -f ".env" ]]; then
  print_status "Creating .env file from template..."
  cp config/environment.template.env .env
  print_success ".env file created"
else
  print_status ".env file already exists"
fi

if [[ ! -f "config/aws-credentials.sh" ]]; then
  print_status "Creating AWS credentials template..."
  cp config/aws-credentials.template.sh config/aws-credentials.sh
  # Replace placeholder with actual account ID
  sed -i.bak "s/123456789012/$AWS_ACCOUNT_ID/g" config/aws-credentials.sh
  rm config/aws-credentials.sh.bak
  print_success "AWS credentials template created"
else
  print_status "AWS credentials file already exists"
fi

if [[ ! -f "config/deployment-config.json" ]]; then
  print_status "Creating deployment configuration..."
  cp config/deployment-config.template.json config/deployment-config.json
  # Replace placeholder with actual account ID
  sed -i.bak "s/YOUR_AWS_ACCOUNT_ID/$AWS_ACCOUNT_ID/g" config/deployment-config.json
  rm config/deployment-config.json.bak
  print_success "Deployment configuration created"
else
  print_status "Deployment configuration already exists"
fi

# Step 4: API Keys Configuration
print_header "🔑 Step 4: API Keys Configuration"

print_status "You need to configure API keys for the following services:"
echo ""
echo "1. Financial Modeling Prep (FMP) API"
echo "   - Sign up at: https://financialmodelingprep.com/developer/docs"
echo "   - Get your API key from the dashboard"
echo ""
echo "2. Perplexity API"
echo "   - Sign up at: https://www.perplexity.ai/settings/api"
echo "   - Get your API key from the settings"
echo ""

read -p "Do you have both API keys ready? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  # Get FMP API key
  read -p "Enter your FMP API key: " FMP_API_KEY
  if [[ -n "$FMP_API_KEY" ]]; then
    # Update .env file
    sed -i.bak "s/your_fmp_api_key_here/$FMP_API_KEY/g" .env
    print_success "FMP API key configured"
  fi
  
  # Get Perplexity API key
  read -p "Enter your Perplexity API key: " PERPLEXITY_API_KEY
  if [[ -n "$PERPLEXITY_API_KEY" ]]; then
    # Update .env file
    sed -i.bak "s/your_perplexity_api_key_here/$PERPLEXITY_API_KEY/g" .env
    print_success "Perplexity API key configured"
  fi
  
  # Clean up backup file
  rm -f .env.bak
  
  # Get notification email
  read -p "Enter your notification email: " NOTIFICATION_EMAIL
  if [[ -n "$NOTIFICATION_EMAIL" ]]; then
    # Update AWS credentials file
    sed -i.bak "s/your-email@example.com/$NOTIFICATION_EMAIL/g" config/aws-credentials.sh
    rm -f config/aws-credentials.sh.bak
    print_success "Notification email configured"
  fi
else
  print_warning "Please obtain your API keys and update the configuration files manually:"
  print_status "1. Edit .env file with your API keys"
  print_status "2. Edit config/aws-credentials.sh with your notification email"
fi

# Step 5: Test configuration
print_header "🧪 Step 5: Testing Configuration"

print_status "Testing API connectivity..."

# Test FMP API
if [[ -n "$FMP_API_KEY" ]]; then
  print_status "Testing FMP API..."
  if curl -s "https://financialmodelingprep.com/api/v3/profile/AAPL?apikey=$FMP_API_KEY" | grep -q "AAPL"; then
    print_success "FMP API connection successful"
  else
    print_warning "FMP API test failed. Please check your API key."
  fi
fi

# Test Perplexity API
if [[ -n "$PERPLEXITY_API_KEY" ]]; then
  print_status "Testing Perplexity API..."
  if curl -s -X POST "https://api.perplexity.ai/chat/completions" \
    -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model": "llama-3.1-sonar-small-128k-online", "messages": [{"role": "user", "content": "test"}]}' | grep -q "choices"; then
    print_success "Perplexity API connection successful"
  else
    print_warning "Perplexity API test failed. Please check your API key."
  fi
fi

# Step 6: Deployment options
print_header "🚀 Step 6: Deployment Options"

print_status "Choose your deployment option:"
echo ""
echo "1. Complete deployment (Infrastructure + Lambda + Container)"
echo "2. Infrastructure only"
echo "3. Skip deployment (configure only)"
echo ""

read -p "Enter your choice (1-3): " -n 1 -r
echo

case $REPLY in
  1)
    print_status "Starting complete deployment..."
    if [[ -n "$FMP_API_KEY" && -n "$PERPLEXITY_API_KEY" && -n "$NOTIFICATION_EMAIL" ]]; then
      export FMP_API_KEY="$FMP_API_KEY"
      export PERPLEXITY_API_KEY="$PERPLEXITY_API_KEY"
      export NOTIFICATION_EMAIL="$NOTIFICATION_EMAIL"
      
      ./scripts/deploy-all.sh --environment prod
    else
      print_error "Missing required configuration. Please update your configuration files and run:"
      print_status "./scripts/deploy-all.sh --environment prod"
    fi
    ;;
  2)
    print_status "Starting infrastructure deployment..."
    if [[ -n "$FMP_API_KEY" && -n "$PERPLEXITY_API_KEY" && -n "$NOTIFICATION_EMAIL" ]]; then
      make deploy-infra ENV=prod \
        NOTIFICATION_EMAIL="$NOTIFICATION_EMAIL" \
        FMP_API_KEY="$FMP_API_KEY" \
        PERPLEXITY_API_KEY="$PERPLEXITY_API_KEY"
    else
      print_error "Missing required configuration. Please update your configuration files and run:"
      print_status "make deploy-infra ENV=prod"
    fi
    ;;
  3)
    print_status "Skipping deployment"
    ;;
  *)
    print_warning "Invalid choice. Skipping deployment."
    ;;
esac

# Step 7: Final instructions
print_header "✅ Setup Complete!"

print_success "AnchorAlpha setup is complete!"
echo ""
print_status "📋 Next Steps:"
echo ""

if [[ $REPLY == "3" || (-z "$FMP_API_KEY" || -z "$PERPLEXITY_API_KEY" || -z "$NOTIFICATION_EMAIL") ]]; then
  echo "1. Update your configuration files:"
  echo "   - .env (API keys)"
  echo "   - config/aws-credentials.sh (notification email)"
  echo ""
  echo "2. Deploy the application:"
  echo "   ./scripts/deploy-all.sh --environment prod"
  echo ""
fi

echo "3. Monitor your deployment:"
echo "   make status ENV=prod"
echo ""
echo "4. View logs:"
echo "   make logs ENV=prod"
echo ""
echo "5. Test the Lambda function:"
echo "   make test-lambda ENV=prod"
echo ""

print_status "📚 Documentation:"
echo "   - Deployment Guide: DEPLOYMENT_README.md"
echo "   - Troubleshooting: TROUBLESHOOTING.md"
echo "   - Infrastructure Guide: infrastructure/README.md"
echo ""

print_status "💰 Cost Estimate:"
echo "   - Monthly cost: ~$5-10 USD"
echo "   - Budget alerts configured at $10/month"
echo ""

print_success "🎉 Happy momentum screening!"

# Deactivate virtual environment
deactivate