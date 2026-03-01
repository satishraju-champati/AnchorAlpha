# AnchorAlpha Production Deployment Plan

**Deployment Date**: [TO BE FILLED]  
**Environment**: Production  
**Estimated Time**: 45-60 minutes  
**Cost**: ~$5-10/month  

## 📋 Pre-Deployment Checklist

### Prerequisites Verification
- [ ] AWS CLI installed and configured
- [ ] Docker installed and running
- [ ] Python 3.11+ with virtual environment activated
- [ ] Git repository up to date (commit: `e081c4c`)
- [ ] API keys obtained (FMP and Perplexity)
- [ ] Notification email configured

### Required Information
```bash
# Fill these out before deployment:
export NOTIFICATION_EMAIL="your-email@example.com"
export FMP_API_KEY="your_fmp_api_key_here"
export PERPLEXITY_API_KEY="your_perplexity_api_key_here"
export AWS_REGION="us-east-1"
export ENVIRONMENT="prod"
```

## 🚀 Deployment Steps

### Step 1: Environment Setup (5 minutes)
```bash
# Navigate to project directory
cd AnchorAlpha

# Activate virtual environment
source venv/bin/activate

# Verify build is ready
ls -la build/lambda-deployment.zip

# Load environment variables
source config/aws-credentials.sh  # After filling it out
```

### Step 2: Pre-Deployment Validation (10 minutes)
```bash
# Validate AWS credentials
aws sts get-caller-identity

# Validate CloudFormation templates
make validate

# Run core tests
python -m pytest tst/AnchorAlpha/test_models.py -v
python -m pytest tst/AnchorAlpha/test_momentum_engine.py -v

# Check Docker
docker info
```

### Step 3: Infrastructure Deployment (15 minutes)
```bash
# Deploy complete infrastructure
./scripts/deploy-all.sh --environment prod

# Alternative: Step-by-step deployment
# make deploy-infra ENV=prod \
#   NOTIFICATION_EMAIL="$NOTIFICATION_EMAIL" \
#   FMP_API_KEY="$FMP_API_KEY" \
#   PERPLEXITY_API_KEY="$PERPLEXITY_API_KEY"
```

### Step 4: Verification and Testing (10 minutes)
```bash
# Check deployment status
make status ENV=prod

# Test Lambda function
make test-lambda ENV=prod

# View logs
make logs ENV=prod

# Get Streamlit URL
aws lightsail get-container-services \
  --service-name anchor-alpha-streamlit-prod \
  --query 'containerServices[0].url' \
  --output text
```

### Step 5: Post-Deployment Configuration (5 minutes)
```bash
# Set up monitoring alerts
./infrastructure/scripts/deploy-monitoring.sh --environment prod

# Verify budget alerts
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text)
```

## 📊 Expected Deployment Outputs

### AWS Resources Created
- **CloudFormation Stack**: `anchor-alpha-infrastructure-prod`
- **Lambda Function**: `anchor-alpha-momentum-processor-prod`
- **S3 Bucket**: `anchor-alpha-momentum-data-prod-{account-id}`
- **Lightsail Container**: `anchor-alpha-streamlit-prod`
- **EventBridge Rule**: Daily trigger at 9:30 PM UTC
- **SNS Topic**: Error and budget notifications
- **Secrets Manager**: API keys storage
- **Budget**: $10/month limit with alerts

### Service URLs
- **Streamlit Dashboard**: `https://{service-name}.{region}.cs.amazonlightsail.com`
- **CloudWatch Logs**: `/aws/lambda/anchor-alpha-momentum-processor-prod`
- **S3 Data**: `s3://anchor-alpha-momentum-data-prod-{account-id}/`

## 🔍 Deployment Verification Checklist

### Infrastructure Verification
- [ ] CloudFormation stack status: `CREATE_COMPLETE`
- [ ] Lambda function state: `Active`
- [ ] S3 bucket created and accessible
- [ ] Lightsail container state: `RUNNING`
- [ ] EventBridge rule enabled
- [ ] SNS topic created with email subscription
- [ ] Budget alerts configured

### Functional Verification
- [ ] Lambda function executes without errors
- [ ] API keys accessible from Secrets Manager
- [ ] S3 write permissions working
- [ ] Streamlit app loads successfully
- [ ] Dashboard displays placeholder data
- [ ] Email notifications configured

### Security Verification
- [ ] IAM roles have minimal required permissions
- [ ] S3 bucket has public access blocked
- [ ] API keys stored securely in Secrets Manager
- [ ] All resources properly tagged

## 🚨 Rollback Plan

If deployment fails or issues arise:

### Quick Rollback
```bash
# Stop Lambda executions
aws events disable-rule --name anchor-alpha-daily-trigger-prod

# Delete Lightsail container (optional)
aws lightsail delete-container-service \
  --service-name anchor-alpha-streamlit-prod

# Delete CloudFormation stack (nuclear option)
aws cloudformation delete-stack \
  --stack-name anchor-alpha-infrastructure-prod
```

### Partial Rollback
```bash
# Rollback Lambda code only
aws lambda update-function-code \
  --function-name anchor-alpha-momentum-processor-prod \
  --zip-file fileb://backup/previous-version.zip

# Rollback container only
aws lightsail create-container-service-deployment \
  --service-name anchor-alpha-streamlit-prod \
  --containers file://backup/previous-containers.json
```

## 💰 Cost Monitoring

### Expected Monthly Costs
- **Lambda**: ~$0.50 (daily executions)
- **S3**: ~$0.10 (data storage)
- **Lightsail**: ~$3.50 (nano container)
- **EventBridge**: ~$0.01 (scheduled rules)
- **Secrets Manager**: ~$0.80 (2 secrets)
- **CloudWatch**: ~$0.50 (logs and metrics)
- **SNS**: ~$0.01 (notifications)
- **Total**: ~$5.42/month

### Budget Alerts
- **80% Alert**: $8.00 spent
- **100% Alert**: $10.00 forecasted
- **Email**: Configured notification email

## 🔧 Troubleshooting Quick Reference

### Common Issues
1. **Lambda timeout**: Increase timeout in CloudFormation
2. **API rate limits**: Check API usage in logs
3. **S3 permissions**: Verify Lambda execution role
4. **Container fails**: Check Docker build and logs
5. **Budget exceeded**: Review resource usage

### Useful Commands
```bash
# Health check
./scripts/health-check.sh prod

# View recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "ERROR"

# Check API usage
python -c "
from src.AnchorAlpha.utils.api_monitoring import get_api_monitor
monitor = get_api_monitor()
print(monitor.generate_usage_report())
"
```

## 📞 Support Contacts

### Documentation
- **Deployment Guide**: `DEPLOYMENT_README.md`
- **Troubleshooting**: `TROUBLESHOOTING.md`
- **Architecture**: `infrastructure/README.md`

### Emergency Procedures
- **Stop all processing**: Disable EventBridge rule
- **Cost emergency**: Delete Lightsail container
- **Complete rollback**: Delete CloudFormation stack

## ✅ Post-Deployment Tasks

### Immediate (Day 1)
- [ ] Verify first scheduled Lambda execution
- [ ] Check S3 data generation
- [ ] Test Streamlit dashboard functionality
- [ ] Confirm email notifications working

### Short-term (Week 1)
- [ ] Monitor daily costs and usage
- [ ] Review CloudWatch logs for errors
- [ ] Validate API rate limit handling
- [ ] Test error scenarios and recovery

### Long-term (Month 1)
- [ ] Analyze cost trends and optimize
- [ ] Review performance metrics
- [ ] Update API keys if needed
- [ ] Plan feature enhancements

---

## 🎯 Deployment Command Summary

**One-Command Deployment:**
```bash
export NOTIFICATION_EMAIL="your-email@example.com"
export FMP_API_KEY="your_fmp_api_key"
export PERPLEXITY_API_KEY="your_perplexity_api_key"
./scripts/deploy-all.sh --environment prod
```

**Verification:**
```bash
make status ENV=prod
```

**Get Dashboard URL:**
```bash
aws lightsail get-container-services \
  --service-name anchor-alpha-streamlit-prod \
  --query 'containerServices[0].url' \
  --output text
```

---

**Ready for deployment!** 🚀

All scripts, configurations, and documentation are in place for a smooth production deployment tomorrow.