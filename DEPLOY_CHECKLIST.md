# 🚀 AnchorAlpha Deployment Checklist

**Quick reference for tomorrow's deployment**

## Before You Start

### 1. Required Information
```bash
# Fill these out:
NOTIFICATION_EMAIL="your-email@example.com"
FMP_API_KEY="your_fmp_api_key_here"  
PERPLEXITY_API_KEY="your_perplexity_api_key_here"
```

### 2. Prerequisites Check
- [ ] AWS CLI configured (`aws sts get-caller-identity`)
- [ ] Docker running (`docker info`)
- [ ] In AnchorAlpha directory
- [ ] Virtual environment activated (`source venv/bin/activate`)

## Deployment Commands

### Option 1: One-Command Deployment (Recommended)
```bash
export NOTIFICATION_EMAIL="your-email@example.com"
export FMP_API_KEY="your_fmp_api_key"
export PERPLEXITY_API_KEY="your_perplexity_api_key"
./scripts/deploy-all.sh --environment prod
```

### Option 2: Step-by-Step
```bash
# 1. Infrastructure
make deploy-infra ENV=prod \
  NOTIFICATION_EMAIL="$NOTIFICATION_EMAIL" \
  FMP_API_KEY="$FMP_API_KEY" \
  PERPLEXITY_API_KEY="$PERPLEXITY_API_KEY"

# 2. Lambda
./scripts/deploy-lambda.sh --environment prod

# 3. Container
make deploy-container ENV=prod
```

## Verification

```bash
# Check status
make status ENV=prod

# Test Lambda
make test-lambda ENV=prod

# Get dashboard URL
aws lightsail get-container-services \
  --service-name anchor-alpha-streamlit-prod \
  --query 'containerServices[0].url' \
  --output text
```

## Expected Results
- ✅ CloudFormation stack created
- ✅ Lambda function deployed and tested
- ✅ Streamlit dashboard accessible
- ✅ Budget alerts configured ($10/month)
- ✅ Daily processing scheduled (9:30 PM UTC)

## If Something Goes Wrong
```bash
# Check logs
make logs ENV=prod

# Health check
./scripts/health-check.sh prod

# Emergency stop
aws events disable-rule --name anchor-alpha-daily-trigger-prod
```

## Cost Estimate
**~$5-10/month** with budget alerts at $8 (80%) and $10 (100%)

---
**Total Time**: ~45-60 minutes  
**Difficulty**: Easy (automated scripts handle everything)  
**Documentation**: See `DEPLOYMENT_PLAN.md` for detailed steps