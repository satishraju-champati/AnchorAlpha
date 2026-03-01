# AnchorAlpha Deployment Guide

A comprehensive momentum screening application for large-cap US stocks with AI-powered insights.

## 🏗️ Architecture Overview

AnchorAlpha uses a serverless architecture on AWS designed for cost-effectiveness and reliability:

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

### Components

- **AWS Lambda**: Daily data processing and momentum calculations
- **Amazon S3**: Stores processed stock data as JSON files
- **EventBridge**: Triggers Lambda function daily at market close
- **AWS Lightsail**: Hosts the Streamlit frontend application
- **AWS Secrets Manager**: Securely stores API keys
- **CloudWatch**: Monitoring, logging, and alerting
- **SNS**: Notifications for errors and budget alerts
- **AWS Budgets**: Cost control with $10/month limit

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Docker** installed
4. **Python 3.11+** installed
5. **API Keys**:
   - [Financial Modeling Prep](https://financialmodelingprep.com/developer/docs) API key
   - [Perplexity](https://www.perplexity.ai/settings/api) API key

### One-Command Deployment

```bash
# Set required environment variables
export NOTIFICATION_EMAIL="your-email@example.com"
export FMP_API_KEY="your_fmp_api_key"
export PERPLEXITY_API_KEY="your_perplexity_api_key"

# Deploy everything
./scripts/deploy-all.sh --environment prod
```

## 📋 Detailed Setup Instructions

### Step 1: Clone and Setup

```bash
git clone <repository-url>
cd AnchorAlpha

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy configuration templates
cp config/environment.template.env .env
cp config/aws-credentials.template.sh config/aws-credentials.sh
cp config/deployment-config.template.json config/deployment-config.json

# Edit the files with your actual values
nano .env
nano config/aws-credentials.sh
nano config/deployment-config.json
```

### Step 3: Configure AWS CLI

```bash
# Configure AWS CLI (if not already done)
aws configure

# Or load credentials from file
source config/aws-credentials.sh
```

### Step 4: Deploy Infrastructure

Choose one of the following deployment methods:

#### Option A: Complete Deployment (Recommended)

```bash
./scripts/deploy-all.sh --environment prod
```

#### Option B: Step-by-Step Deployment

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

#### Option C: Using Makefile

```bash
# Deploy everything
make deploy-all ENV=prod \
  NOTIFICATION_EMAIL="your-email@example.com" \
  FMP_API_KEY="your_fmp_key" \
  PERPLEXITY_API_KEY="your_perplexity_key"
```

### Step 5: Verify Deployment

```bash
# Check deployment status
make status ENV=prod

# View Lambda logs
make logs ENV=prod

# Test Lambda function
make test-lambda ENV=prod
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FMP_API_KEY` | Financial Modeling Prep API key | Yes | - |
| `PERPLEXITY_API_KEY` | Perplexity API key | Yes | - |
| `NOTIFICATION_EMAIL` | Email for alerts | Yes | - |
| `AWS_REGION` | AWS region | No | us-east-1 |
| `ENVIRONMENT` | Deployment environment | No | prod |

### Deployment Environments

- **dev**: Development environment with reduced resources
- **staging**: Pre-production testing environment
- **prod**: Production environment with full resources

### Lambda Configuration

| Parameter | Dev | Staging | Prod |
|-----------|-----|---------|------|
| Memory | 256 MB | 512 MB | 512 MB |
| Timeout | 10 min | 15 min | 15 min |
| Schedule | 10:30 PM UTC | 9:30 PM UTC | 9:30 PM UTC |

### Lightsail Configuration

| Parameter | Dev | Staging | Prod |
|-----------|-----|---------|------|
| Power | nano | micro | nano |
| Scale | 1 | 1 | 1 |
| Cost | ~$3.50/month | ~$7/month | ~$3.50/month |

## 📊 Monitoring and Maintenance

### CloudWatch Dashboards

Access monitoring dashboards:
- Lambda execution metrics
- API call success rates
- S3 storage usage
- Cost tracking

### Log Locations

- **Lambda logs**: `/aws/lambda/anchor-alpha-momentum-processor-{env}`
- **Container logs**: Available in Lightsail console
- **API monitoring**: Custom CloudWatch metrics

### Alerts and Notifications

Automatic notifications for:
- Lambda function errors
- Long execution times (>10 minutes)
- Budget threshold breaches (80% and 100%)
- API rate limit violations

### Maintenance Tasks

#### Daily
- Monitor Lambda execution logs
- Check S3 data freshness
- Verify Streamlit app accessibility

#### Weekly
- Review CloudWatch metrics
- Check AWS costs and budget alerts
- Validate API key usage and limits

#### Monthly
- Review and rotate API keys
- Update dependencies and security patches
- Analyze performance metrics and optimize

## 💰 Cost Management

### Budget Breakdown

| Service | Monthly Cost (Prod) |
|---------|-------------------|
| Lambda | ~$0.50 |
| S3 | ~$0.10 |
| Lightsail | ~$3.50 |
| EventBridge | ~$0.01 |
| Secrets Manager | ~$0.80 |
| CloudWatch | ~$0.50 |
| SNS | ~$0.01 |
| **Total** | **~$5.42** |

### Cost Optimization Tips

1. **Use nano Lightsail instances** for production
2. **Enable S3 lifecycle policies** to delete old data
3. **Monitor API usage** to avoid overage charges
4. **Use CloudWatch log retention** to control log costs
5. **Set up budget alerts** at 50%, 80%, and 100%

## 🔒 Security Best Practices

### API Key Management

- Store API keys in AWS Secrets Manager
- Rotate keys regularly (quarterly)
- Use different keys for different environments
- Monitor API usage for anomalies

### AWS Security

- Use IAM roles with least-privilege access
- Enable CloudTrail for audit logging
- Use VPC endpoints where possible
- Enable S3 bucket encryption
- Regularly review IAM policies

### Application Security

- Keep dependencies updated
- Use HTTPS for all external communications
- Implement proper error handling
- Sanitize all user inputs
- Regular security scans

## 🐛 Troubleshooting

### Common Issues

#### Lambda Function Timeout
```bash
# Increase timeout in CloudFormation template
aws lambda update-function-configuration \
  --function-name anchor-alpha-momentum-processor-prod \
  --timeout 900
```

#### API Rate Limits
```bash
# Check API usage in logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "rate limit"
```

#### S3 Permission Errors
```bash
# Verify Lambda execution role permissions
aws iam get-role-policy \
  --role-name anchor-alpha-lambda-execution-role-prod \
  --policy-name S3AccessPolicy
```

#### Container Deployment Fails
```bash
# Check Docker build
docker build -t anchor-alpha-streamlit:latest -f infrastructure/docker/Dockerfile .

# Check AWS credentials
aws sts get-caller-identity

# Check Lightsail service status
aws lightsail get-container-services --service-name anchor-alpha-streamlit-prod
```

### Debugging Commands

```bash
# View recent Lambda logs
aws logs tail /aws/lambda/anchor-alpha-momentum-processor-prod --follow

# Check S3 bucket contents
aws s3 ls s3://anchor-alpha-momentum-data-prod-$(aws sts get-caller-identity --query Account --output text)/

# Test Lambda function manually
aws lambda invoke \
  --function-name anchor-alpha-momentum-processor-prod \
  --payload '{"source":"manual-test"}' \
  response.json && cat response.json

# Check EventBridge rule
aws events describe-rule --name anchor-alpha-daily-trigger-prod

# Monitor container logs
aws lightsail get-container-log \
  --service-name anchor-alpha-streamlit-prod \
  --container-name streamlit-app
```

### Getting Help

1. **Check CloudWatch logs** for detailed error messages
2. **Review AWS service limits** and quotas
3. **Verify API key validity** and rate limits
4. **Check IAM permissions** for all services
5. **Validate network connectivity** and security groups

## 🔄 Updates and Upgrades

### Updating Lambda Code

```bash
# Update Lambda function
./scripts/deploy-lambda.sh --environment prod
```

### Updating Container

```bash
# Rebuild and deploy container
./infrastructure/scripts/deploy-container.sh --environment prod
```

### Updating Infrastructure

```bash
# Update CloudFormation stack
make deploy-infra ENV=prod
```

### Rolling Back

```bash
# Rollback Lambda to previous version
aws lambda update-function-code \
  --function-name anchor-alpha-momentum-processor-prod \
  --zip-file fileb://backup/previous-version.zip

# Rollback container deployment
aws lightsail create-container-service-deployment \
  --service-name anchor-alpha-streamlit-prod \
  --containers file://backup/previous-containers.json
```

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Lightsail Documentation](https://docs.aws.amazon.com/lightsail/)
- [Financial Modeling Prep API](https://financialmodelingprep.com/developer/docs)
- [Perplexity API Documentation](https://docs.perplexity.ai/)
- [Streamlit Documentation](https://docs.streamlit.io/)

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs for error details
3. Verify configuration and credentials
4. Check AWS service status and limits