# AnchorAlpha - Multi-Tier Large-Cap Momentum Screener

A serverless momentum screening application that identifies top-performing large-cap US stocks across different market capitalization tiers with AI-powered insights.

## 🚀 Quick Start

### One-Command Setup and Deployment

```bash
# Run the setup wizard
./scripts/setup.sh

# Or deploy directly (if you have API keys ready)
export NOTIFICATION_EMAIL="your-email@example.com"
export FMP_API_KEY="your_fmp_api_key"
export PERPLEXITY_API_KEY="your_perplexity_api_key"
./scripts/deploy-all.sh --environment prod
```

### Prerequisites

- AWS Account with CLI configured
- Docker installed
- Python 3.11+
- [Financial Modeling Prep](https://financialmodelingprep.com/developer/docs) API key
- [Perplexity](https://www.perplexity.ai/settings/api) API key

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│  Lambda Function │───▶│   S3 Bucket     │
│  (Daily Cron)   │    │  (Data Processor)│    │ (JSON Storage)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  External APIs   │    │ Streamlit App   │
                       │ (FMP, Perplexity)│    │ (Lightsail)     │
                       └──────────────────┘    └─────────────────┘
```

**Serverless AWS Architecture:**
- **AWS Lambda**: Daily momentum calculations and AI summary generation
- **Amazon S3**: Stores processed stock data as JSON files
- **EventBridge**: Triggers Lambda function daily at market close
- **AWS Lightsail**: Hosts the Streamlit frontend (~$3.50/month)
- **AWS Secrets Manager**: Securely stores API keys
- **CloudWatch**: Monitoring, logging, and alerting
- **Total Cost**: ~$5-10/month with budget controls

## 📋 Project Structure

```
AnchorAlpha/
├── src/AnchorAlpha/           # Main application code
│   ├── models.py              # Core data models
│   ├── momentum_engine.py     # Momentum calculation engine
│   ├── api/                   # API clients (FMP, Perplexity)
│   ├── lambda_function/       # AWS Lambda handler
│   ├── streamlit_app/         # Streamlit web interface
│   ├── storage/               # S3 data pipeline
│   └── utils/                 # Logging and monitoring
├── infrastructure/            # AWS deployment templates
│   ├── cloudformation/        # CloudFormation templates
│   ├── docker/               # Container configuration
│   └── scripts/              # Deployment scripts
├── config/                   # Configuration templates
├── scripts/                  # Deployment and utility scripts
├── tst/AnchorAlpha/          # Comprehensive test suite
└── requirements.txt          # Python dependencies
```

## 🚀 Deployment

### Option 1: Complete Deployment (Recommended)

```bash
./scripts/deploy-all.sh --environment prod
```

### Option 2: Step-by-Step Deployment

```bash
# 1. Deploy AWS infrastructure
make deploy-infra ENV=prod \
  NOTIFICATION_EMAIL="your-email@example.com" \
  FMP_API_KEY="your_fmp_key" \
  PERPLEXITY_API_KEY="your_perplexity_key"

# 2. Deploy Lambda function
./scripts/deploy-lambda.sh --environment prod

# 3. Deploy Streamlit container
make deploy-container ENV=prod
```

### Option 3: Using Makefile

```bash
make deploy-all ENV=prod \
  NOTIFICATION_EMAIL="your-email@example.com" \
  FMP_API_KEY="your_fmp_key" \
  PERPLEXITY_API_KEY="your_perplexity_key"
```

## 📊 Monitoring

```bash
# Check deployment status
make status ENV=prod

# View Lambda logs
make logs ENV=prod

# Test Lambda function
make test-lambda ENV=prod

# Monitor costs
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text)
```

## 🔧 Development

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp config/environment.template.env .env
# Edit .env with your API keys

# Run tests
pytest tst/ -v
```

### Running Tests

```bash
# All tests
make test

# Specific test categories
pytest tst/AnchorAlpha/test_momentum_engine.py -v
pytest tst/AnchorAlpha/test_fmp_client.py -v
pytest tst/AnchorAlpha/test_streamlit_integration.py -v

# Integration tests
pytest tst/AnchorAlpha/test_end_to_end_integration.py -v
```

### Local Streamlit Development

```bash
# Run Streamlit app locally
streamlit run src/AnchorAlpha/streamlit_app/momentum_dashboard.py

# Or use the demo with mock data
streamlit run src/AnchorAlpha/streamlit_app/demo_interactive_dashboard.py
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FMP_API_KEY` | Financial Modeling Prep API key | Yes | - |
| `PERPLEXITY_API_KEY` | Perplexity API key | Yes | - |
| `NOTIFICATION_EMAIL` | Email for alerts | Yes | - |
| `AWS_REGION` | AWS region | No | us-east-1 |
| `ENVIRONMENT` | Deployment environment | No | prod |

### Market Configuration

- **Market Cap Tiers**: $100B-$200B, $200B-$500B, $500B-$1T, $1T+
- **Momentum Windows**: 7, 30, 60, 90 days
- **Top Performers**: 20 stocks per tier/timeframe
- **Minimum Market Cap**: $10B (large-cap only)

## 🔒 Security

- API keys stored in AWS Secrets Manager
- IAM roles with least-privilege access
- S3 bucket encryption enabled
- VPC endpoints for internal communication
- Regular security audits and updates

## 💰 Cost Management

- **Budget Control**: $10/month limit with alerts
- **Resource Optimization**: Nano Lightsail instances
- **Data Lifecycle**: 90-day S3 retention policy
- **Monitoring**: Real-time cost tracking and alerts

## 🐛 Troubleshooting

For common issues and solutions, see:
- **[Deployment Guide](DEPLOYMENT_README.md)** - Complete setup instructions
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and fixes
- **[Infrastructure Guide](infrastructure/README.md)** - AWS infrastructure details

### Quick Diagnostics

```bash
# Health check
./scripts/health-check.sh prod

# View recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s) - 3600))000

# Check S3 data
aws s3 ls s3://anchor-alpha-momentum-data-prod-$(aws sts get-caller-identity --query Account --output text)/
```

## 📚 Documentation

- **[DEPLOYMENT_README.md](DEPLOYMENT_README.md)** - Comprehensive deployment guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Issue resolution guide
- **[infrastructure/README.md](infrastructure/README.md)** - Infrastructure documentation
- **[scripts/README.md](scripts/README.md)** - Development scripts guide

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `pytest tst/ -v`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues or questions:
1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review CloudWatch logs for error details
3. Verify configuration and API keys
4. Check AWS service status and limits