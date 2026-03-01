# AnchorAlpha Infrastructure Deployment Guide

This directory contains all the necessary infrastructure-as-code templates and deployment scripts for the AnchorAlpha momentum screening application.

## Architecture Overview

The AnchorAlpha system uses a serverless architecture on AWS:

- **AWS Lambda**: Processes momentum calculations daily
- **Amazon S3**: Stores processed data as JSON files
- **EventBridge**: Triggers Lambda function on a daily schedule
- **AWS Lightsail**: Hosts the Streamlit frontend application
- **AWS Secrets Manager**: Securely stores API keys
- **CloudWatch**: Monitoring and logging
- **SNS**: Notifications for errors and budget alerts
- **AWS Budgets**: Cost control with $10/month limit

## Prerequisites

Before deploying, ensure you have:

1. **AWS CLI** installed and configured with appropriate permissions
2. **Docker** installed (for container deployment)
3. **API Keys**:
   - Financial Modeling Prep API key
   - Perplexity API key
4. **Email address** for notifications

## Directory Structure

```
infrastructure/
├── cloudformation/
│   ├── anchor-alpha-infrastructure.yaml    # Main infrastructure template
│   └── lightsail-container.yaml           # Lightsail container template
├── docker/
│   └── Dockerfile                         # Streamlit app container
├── scripts/
│   ├── deploy-infrastructure.sh           # Deploy AWS infrastructure
│   ├── deploy-container.sh               # Deploy Streamlit container
│   └── package-lambda.sh                 # Create Lambda deployment package
└── README.md                             # This file
```

## Deployment Steps

### 1. Deploy Core Infrastructure

Deploy the main AWS infrastructure (Lambda, S3, EventBridge, etc.):

```bash
./infrastructure/scripts/deploy-infrastructure.sh \
  --environment prod \
  --region us-east-1 \
  --notification-email your-email@example.com \
  --fmp-api-key YOUR_FMP_API_KEY \
  --perplexity-api-key YOUR_PERPLEXITY_API_KEY
```

**Parameters:**
- `--environment`: Environment name (dev/staging/prod)
- `--region`: AWS region for deployment
- `--notification-email`: Email for budget and error notifications
- `--fmp-api-key`: Your Financial Modeling Prep API key
- `--perplexity-api-key`: Your Perplexity API key

### 2. Package and Deploy Lambda Function

Create a deployment package for the Lambda function:

```bash
./infrastructure/scripts/package-lambda.sh --environment prod
```

Then update the Lambda function with the new code:

```bash
aws lambda update-function-code \
  --function-name anchor-alpha-momentum-processor-prod \
  --zip-file fileb://dist/anchor-alpha-lambda-prod.zip
```

### 3. Deploy Streamlit Container

Deploy the Streamlit frontend to AWS Lightsail:

```bash
./infrastructure/scripts/deploy-container.sh \
  --environment prod \
  --region us-east-1 \
  --power nano \
  --scale 1
```

**Parameters:**
- `--power`: Container size (nano/micro/small/medium/large/xlarge)
- `--scale`: Number of container instances

## Configuration

### Environment Variables

The Lambda function uses these environment variables (automatically set by CloudFormation):

- `ENVIRONMENT`: Deployment environment
- `S3_BUCKET`: S3 bucket name for data storage
- `FMP_API_KEY_SECRET`: ARN of FMP API key in Secrets Manager
- `PERPLEXITY_API_KEY_SECRET`: ARN of Perplexity API key in Secrets Manager

### EventBridge Schedule

The Lambda function is scheduled to run daily at 9:30 PM UTC (4:30 PM EST) on weekdays using the cron expression:
```
cron(30 21 ? * MON-FRI *)
```

You can modify this schedule in the CloudFormation template if needed.

### Cost Control

AWS Budgets is configured with:
- **Monthly limit**: $10 USD
- **Alert at 80%**: $8 spent
- **Alert at 100%**: $10 forecasted spend
- **Notifications**: Sent to the specified email address

## Monitoring and Logging

### CloudWatch Logs

- Lambda logs: `/aws/lambda/anchor-alpha-momentum-processor-{environment}`
- S3 access logs: `/aws/s3/anchor-alpha-momentum-data-{environment}`

### CloudWatch Alarms

- **Lambda Errors**: Triggers when Lambda function has errors
- **Lambda Duration**: Triggers when execution takes longer than 10 minutes

### SNS Notifications

Notifications are sent for:
- Lambda function errors
- Long-running Lambda executions
- Budget threshold breaches

## Security

### IAM Roles and Policies

The Lambda execution role has minimal permissions:
- Read/write access to the specific S3 bucket
- Read access to Secrets Manager for API keys
- CloudWatch Logs write permissions

### API Key Security

- API keys are stored in AWS Secrets Manager
- Keys are encrypted at rest
- Lambda retrieves keys at runtime using IAM permissions

### S3 Security

- Bucket encryption enabled (AES-256)
- Public access blocked
- Versioning enabled
- Lifecycle policy deletes old data after 90 days

## Troubleshooting

### Common Issues

1. **Lambda timeout**: Increase timeout in CloudFormation template (max 15 minutes)
2. **API rate limits**: Implement exponential backoff in Lambda code
3. **S3 permissions**: Verify Lambda execution role has correct S3 permissions
4. **Container deployment fails**: Check Docker image build and AWS credentials

### Useful Commands

Check Lambda function status:
```bash
aws lambda get-function --function-name anchor-alpha-momentum-processor-prod
```

View CloudWatch logs:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/anchor-alpha"
```

Check S3 bucket contents:
```bash
aws s3 ls s3://anchor-alpha-momentum-data-prod-{account-id}/
```

Monitor Lightsail container:
```bash
aws lightsail get-container-services --service-name anchor-alpha-streamlit-prod
```

## Cleanup

To remove all resources:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name anchor-alpha-infrastructure-prod

# Delete Lightsail container service
aws lightsail delete-container-service --service-name anchor-alpha-streamlit-prod

# Delete S3 bucket contents (if needed)
aws s3 rm s3://anchor-alpha-momentum-data-prod-{account-id} --recursive
```

## Cost Optimization

The infrastructure is designed for minimal cost:

- **Lambda**: Pay per execution (daily runs)
- **S3**: Minimal storage costs with lifecycle policies
- **Lightsail**: Fixed monthly cost (~$7/month for nano instance)
- **EventBridge**: Minimal cost for scheduled rules
- **Secrets Manager**: ~$0.40/month per secret

Total estimated monthly cost: **$8-10 USD**

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Verify AWS service limits and quotas
3. Review IAM permissions and policies
4. Check API key validity and rate limits