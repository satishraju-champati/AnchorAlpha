# AnchorAlpha Troubleshooting Guide

This guide covers common issues and their solutions for the AnchorAlpha deployment and operation.

## 🚨 Common Deployment Issues

### 1. AWS CLI Configuration Issues

#### Problem: "Unable to locate credentials"
```
NoCredentialsError: Unable to locate credentials
```

**Solutions:**
```bash
# Option 1: Configure AWS CLI
aws configure

# Option 2: Use environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Option 3: Use AWS profile
export AWS_PROFILE="your-profile-name"

# Verify credentials
aws sts get-caller-identity
```

#### Problem: "Access Denied" errors
```
AccessDenied: User is not authorized to perform action
```

**Required IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "lambda:*",
        "s3:*",
        "iam:*",
        "events:*",
        "secretsmanager:*",
        "sns:*",
        "budgets:*",
        "lightsail:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. CloudFormation Stack Issues

#### Problem: Stack creation fails with "ROLLBACK_COMPLETE"
```bash
# Check stack events for specific error
aws cloudformation describe-stack-events \
  --stack-name anchor-alpha-infrastructure-prod \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'

# Common fixes:
# 1. Check if S3 bucket name is unique globally
# 2. Verify IAM permissions
# 3. Check resource limits in your AWS account
```

#### Problem: "Parameter validation failed"
```bash
# Validate template before deployment
aws cloudformation validate-template \
  --template-body file://infrastructure/cloudformation/anchor-alpha-infrastructure.yaml

# Check parameter values
aws cloudformation describe-stacks \
  --stack-name anchor-alpha-infrastructure-prod \
  --query 'Stacks[0].Parameters'
```

### 3. Lambda Function Issues

#### Problem: Lambda deployment package too large
```
InvalidParameterValueException: Unzipped size must be smaller than 262144000 bytes
```

**Solutions:**
```bash
# Remove unnecessary files from package
find dist/ -name "*.pyc" -delete
find dist/ -name "__pycache__" -type d -exec rm -rf {} +
find dist/ -name "*.egg-info" -type d -exec rm -rf {} +

# Exclude test files and development dependencies
# Edit infrastructure/scripts/package-lambda.sh to remove more files

# Use Lambda layers for large dependencies
aws lambda publish-layer-version \
  --layer-name anchor-alpha-dependencies \
  --zip-file fileb://dependencies.zip \
  --compatible-runtimes python3.11
```

#### Problem: Lambda function timeout
```
Task timed out after 900.00 seconds
```

**Solutions:**
```bash
# Increase timeout (max 15 minutes)
aws lambda update-function-configuration \
  --function-name anchor-alpha-momentum-processor-prod \
  --timeout 900

# Optimize code performance
# - Add pagination for API calls
# - Process stocks in batches
# - Use concurrent processing where possible

# Monitor execution time
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "REPORT RequestId" \
  --start-time $(date -d "1 hour ago" +%s)000
```

#### Problem: Lambda function memory errors
```
Runtime.ExitError: RequestId: xxx-xxx Process exited before completing request
```

**Solutions:**
```bash
# Increase memory allocation
aws lambda update-function-configuration \
  --function-name anchor-alpha-momentum-processor-prod \
  --memory-size 1024

# Monitor memory usage
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "Max Memory Used"
```

### 4. API Integration Issues

#### Problem: FMP API rate limiting
```
HTTP 429: Too Many Requests
```

**Solutions:**
```python
# Implement exponential backoff in code
import time
import random

def api_call_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 429:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)
```

#### Problem: Perplexity API authentication errors
```
HTTP 401: Unauthorized
```

**Solutions:**
```bash
# Verify API key in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id anchor-alpha-perplexity-api-key-prod

# Test API key manually
curl -X POST "https://api.perplexity.ai/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-3.1-sonar-small-128k-online", "messages": [{"role": "user", "content": "test"}]}'
```

### 5. S3 Storage Issues

#### Problem: S3 bucket access denied
```
AccessDenied: Access Denied
```

**Solutions:**
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket anchor-alpha-momentum-data-prod-123456789012

# Verify Lambda execution role permissions
aws iam get-role-policy \
  --role-name anchor-alpha-lambda-execution-role-prod \
  --policy-name S3AccessPolicy

# Test S3 access manually
aws s3 ls s3://anchor-alpha-momentum-data-prod-123456789012/
```

#### Problem: S3 bucket not found
```
NoSuchBucket: The specified bucket does not exist
```

**Solutions:**
```bash
# Check if bucket exists
aws s3api head-bucket --bucket anchor-alpha-momentum-data-prod-123456789012

# Create bucket if missing (should be done by CloudFormation)
aws s3 mb s3://anchor-alpha-momentum-data-prod-123456789012 --region us-east-1

# Verify bucket name format: anchor-alpha-momentum-data-{env}-{account-id}
```

### 6. Container Deployment Issues

#### Problem: Docker build fails
```
ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully
```

**Solutions:**
```bash
# Check Docker daemon is running
docker info

# Build with verbose output
docker build -t anchor-alpha-streamlit:latest -f infrastructure/docker/Dockerfile . --progress=plain

# Check requirements.txt exists and is valid
cat requirements.txt

# Try building with no cache
docker build --no-cache -t anchor-alpha-streamlit:latest -f infrastructure/docker/Dockerfile .
```

#### Problem: Lightsail container service creation fails
```
InvalidInputException: Service name already exists
```

**Solutions:**
```bash
# Check existing services
aws lightsail get-container-services

# Delete existing service if needed
aws lightsail delete-container-service \
  --service-name anchor-alpha-streamlit-prod

# Wait for deletion to complete before recreating
aws lightsail get-container-services \
  --service-name anchor-alpha-streamlit-prod
```

#### Problem: Container health check failures
```
Container failed health check
```

**Solutions:**
```bash
# Check container logs
aws lightsail get-container-log \
  --service-name anchor-alpha-streamlit-prod \
  --container-name streamlit-app

# Test health check endpoint locally
docker run -p 8501:8501 anchor-alpha-streamlit:latest
curl http://localhost:8501/_stcore/health

# Adjust health check settings in deploy-container.sh
```

## 🔍 Runtime Issues

### 1. Data Processing Issues

#### Problem: No stock data retrieved
```bash
# Check FMP API response
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "FMP API"

# Verify API key and endpoint
curl "https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=10000000000&apikey=YOUR_API_KEY"
```

#### Problem: Momentum calculations returning NaN
```bash
# Check for missing historical data
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "historical data"

# Verify date ranges and market holidays
# Check if weekends/holidays are being handled correctly
```

### 2. Streamlit App Issues

#### Problem: App shows "No data available"
```bash
# Check S3 data exists
aws s3 ls s3://anchor-alpha-momentum-data-prod-123456789012/momentum-data/

# Verify data format
aws s3 cp s3://anchor-alpha-momentum-data-prod-123456789012/momentum-data/latest.json - | jq .

# Check app logs
aws lightsail get-container-log \
  --service-name anchor-alpha-streamlit-prod \
  --container-name streamlit-app
```

#### Problem: App loading slowly
```bash
# Check container resources
aws lightsail get-container-services \
  --service-name anchor-alpha-streamlit-prod

# Consider upgrading to micro or small instance
aws lightsail update-container-service \
  --service-name anchor-alpha-streamlit-prod \
  --power micro
```

### 3. Scheduling Issues

#### Problem: Lambda not triggering on schedule
```bash
# Check EventBridge rule
aws events describe-rule --name anchor-alpha-daily-trigger-prod

# Check rule targets
aws events list-targets-by-rule --rule anchor-alpha-daily-trigger-prod

# Check Lambda permissions for EventBridge
aws lambda get-policy --function-name anchor-alpha-momentum-processor-prod
```

#### Problem: Multiple Lambda executions running simultaneously
```bash
# Check concurrent executions
aws lambda get-function-concurrency \
  --function-name anchor-alpha-momentum-processor-prod

# Set reserved concurrency to 1
aws lambda put-provisioned-concurrency-config \
  --function-name anchor-alpha-momentum-processor-prod \
  --provisioned-concurrency-config ProvisionedConcurrencyConfig=1
```

## 📊 Monitoring and Debugging

### CloudWatch Queries

#### Find Lambda errors:
```sql
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20
```

#### Monitor API call success rates:
```sql
fields @timestamp, @message
| filter @message like /API call/
| stats count() by bin(5m)
```

#### Track execution duration:
```sql
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), min(@duration) by bin(5m)
```

### Performance Monitoring

```bash
# Lambda performance metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=anchor-alpha-momentum-processor-prod \
  --start-time $(date -d "24 hours ago" -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average,Maximum

# S3 request metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name NumberOfObjects \
  --dimensions Name=BucketName,Value=anchor-alpha-momentum-data-prod-123456789012 \
  --start-time $(date -d "24 hours ago" -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average
```

## 🛠️ Diagnostic Tools

### Health Check Script

```bash
#!/bin/bash
# health-check.sh - Comprehensive system health check

ENVIRONMENT=${1:-prod}
REGION=${2:-us-east-1}

echo "🏥 AnchorAlpha Health Check - Environment: $ENVIRONMENT"
echo "=================================================="

# Check CloudFormation stack
echo "📋 CloudFormation Stack Status:"
aws cloudformation describe-stacks \
  --stack-name anchor-alpha-infrastructure-$ENVIRONMENT \
  --region $REGION \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null || echo "❌ Stack not found"

# Check Lambda function
echo "⚡ Lambda Function Status:"
aws lambda get-function \
  --function-name anchor-alpha-momentum-processor-$ENVIRONMENT \
  --region $REGION \
  --query 'Configuration.State' \
  --output text 2>/dev/null || echo "❌ Function not found"

# Check S3 bucket
echo "🪣 S3 Bucket Status:"
aws s3api head-bucket \
  --bucket anchor-alpha-momentum-data-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text) \
  2>/dev/null && echo "✅ Bucket accessible" || echo "❌ Bucket not accessible"

# Check latest data
echo "📊 Latest Data:"
aws s3 ls s3://anchor-alpha-momentum-data-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)/momentum-data/ \
  --recursive --human-readable | tail -5

# Check Lightsail container
echo "🐳 Container Service Status:"
aws lightsail get-container-services \
  --service-name anchor-alpha-streamlit-$ENVIRONMENT \
  --region $REGION \
  --query 'containerServices[0].state' \
  --output text 2>/dev/null || echo "❌ Container service not found"

echo "=================================================="
echo "✅ Health check complete"
```

### Log Analysis Script

```bash
#!/bin/bash
# analyze-logs.sh - Analyze Lambda logs for issues

ENVIRONMENT=${1:-prod}
HOURS=${2:-24}

echo "📋 Analyzing Lambda logs for last $HOURS hours"

# Get recent errors
echo "🚨 Recent Errors:"
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-$ENVIRONMENT \
  --start-time $(($(date +%s) - $HOURS * 3600))000 \
  --filter-pattern "ERROR" \
  --query 'events[*].[timestamp,message]' \
  --output table

# Get execution summary
echo "📊 Execution Summary:"
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-$ENVIRONMENT \
  --start-time $(($(date +%s) - $HOURS * 3600))000 \
  --filter-pattern "REPORT" \
  --query 'events[*].message' \
  --output text | grep -o 'Duration: [0-9.]*' | awk '{sum+=$2; count++} END {print "Average Duration:", sum/count "ms"}'
```

## 🆘 Emergency Procedures

### Complete System Recovery

```bash
#!/bin/bash
# emergency-recovery.sh - Complete system recovery

ENVIRONMENT=${1:-prod}

echo "🚨 Starting emergency recovery for environment: $ENVIRONMENT"

# 1. Stop all scheduled executions
aws events disable-rule --name anchor-alpha-daily-trigger-$ENVIRONMENT

# 2. Check for running Lambda executions
aws lambda list-functions --query "Functions[?FunctionName=='anchor-alpha-momentum-processor-$ENVIRONMENT']"

# 3. Redeploy infrastructure if needed
echo "🏗️ Redeploying infrastructure..."
./infrastructure/scripts/deploy-infrastructure.sh --environment $ENVIRONMENT

# 4. Redeploy Lambda function
echo "⚡ Redeploying Lambda function..."
./scripts/deploy-lambda.sh --environment $ENVIRONMENT

# 5. Redeploy container
echo "🐳 Redeploying container..."
./infrastructure/scripts/deploy-container.sh --environment $ENVIRONMENT

# 6. Re-enable scheduled executions
aws events enable-rule --name anchor-alpha-daily-trigger-$ENVIRONMENT

echo "✅ Emergency recovery complete"
```

### Data Recovery

```bash
#!/bin/bash
# data-recovery.sh - Recover from data corruption

ENVIRONMENT=${1:-prod}
BACKUP_DATE=${2:-$(date -d "1 day ago" +%Y-%m-%d)}

echo "📊 Recovering data for $BACKUP_DATE"

# Check for backup data
aws s3 ls s3://anchor-alpha-momentum-data-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)/backups/$BACKUP_DATE/

# Restore from backup if available
aws s3 cp s3://anchor-alpha-momentum-data-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)/backups/$BACKUP_DATE/momentum-data.json \
  s3://anchor-alpha-momentum-data-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)/momentum-data/latest.json

# Trigger manual Lambda execution to regenerate data
aws lambda invoke \
  --function-name anchor-alpha-momentum-processor-$ENVIRONMENT \
  --payload '{"source":"manual-recovery","date":"'$BACKUP_DATE'"}' \
  recovery-response.json

echo "✅ Data recovery initiated"
```

## 📞 Getting Help

### Before Seeking Help

1. **Check this troubleshooting guide** for your specific issue
2. **Review CloudWatch logs** for detailed error messages
3. **Verify configuration** and environment variables
4. **Test individual components** to isolate the problem
5. **Check AWS service status** at https://status.aws.amazon.com/

### Information to Provide

When seeking help, include:
- Environment (dev/staging/prod)
- AWS region
- Error messages from CloudWatch logs
- Steps to reproduce the issue
- Recent changes or deployments
- Output from health check script

### Useful Commands for Support

```bash
# Generate support bundle
./scripts/generate-support-bundle.sh --environment prod

# This creates a zip file with:
# - CloudFormation template and parameters
# - Recent CloudWatch logs
# - Configuration files (sanitized)
# - System health check results
# - AWS resource status
```