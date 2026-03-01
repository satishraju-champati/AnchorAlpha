# AnchorAlpha Monitoring and Logging System

This directory contains the comprehensive monitoring and logging infrastructure for the AnchorAlpha momentum screener application.

## Overview

The monitoring system provides:

- **Structured JSON Logging**: Comprehensive logging with execution tracking and metrics
- **CloudWatch Integration**: Custom metrics, dashboards, and alarms
- **API Usage Monitoring**: Rate limit tracking and cost optimization
- **SNS Notifications**: Critical error alerts and budget notifications
- **Performance Monitoring**: Execution time, success rates, and resource utilization

## Components

### 1. Structured Logging (`src/AnchorAlpha/utils/logging_utils.py`)

**Key Features:**
- JSON-formatted logs for easy parsing and analysis
- Execution ID tracking across all log entries
- Automatic metrics collection during execution
- Context managers for API call timing
- CloudWatch metrics publishing
- SNS notification management

**Usage Example:**
```python
from AnchorAlpha.utils.logging_utils import get_logger

logger = get_logger("MyComponent", "execution_123")

# Basic logging
logger.info("Processing started", stocks_count=100)
logger.warning("Rate limit approaching", utilization=85.0)
logger.error("API call failed", exception=e, api_name="FMP")

# API call timing
with logger.api_call_timer("FMP", "stock-screener"):
    data = api_client.get_data()

# Metrics logging
logger.log_processing_metrics("data_fetch", stocks_fetched=100)
logger.log_s3_operation("upload", "bucket", "key", success=True)
```

### 2. API Usage Monitoring (`src/AnchorAlpha/utils/api_monitoring.py`)

**Key Features:**
- Rate limit tracking with sliding windows
- API call recording and analytics
- Cost estimation and optimization recommendations
- Usage report generation
- CloudWatch metrics publishing

**Usage Example:**
```python
from AnchorAlpha.utils.api_monitoring import get_api_monitor

monitor = get_api_monitor()

# Check rate limits before making calls
wait_time = monitor.check_rate_limit("FMP")
if wait_time > 0:
    time.sleep(wait_time)

# Record API calls
monitor.record_api_call(
    api_name="FMP",
    endpoint="stock-screener",
    duration_seconds=1.5,
    success=True,
    status_code=200
)

# Generate usage reports
report = monitor.generate_usage_report(hours=24)
```

### 3. CloudWatch Dashboard (`infrastructure/cloudformation/monitoring-dashboard.yaml`)

**Includes:**
- Lambda function performance metrics
- Data processing success rates
- API usage and error rates
- Rate limit utilization
- S3 storage metrics
- Recent error logs
- Execution summaries

### 4. Deployment Scripts

**`infrastructure/scripts/deploy-monitoring.sh`**
- Automated deployment of monitoring infrastructure
- CloudWatch dashboard creation
- SNS notification setup
- Custom alarm configuration
- Log retention policy setup

**Usage:**
```bash
./infrastructure/scripts/deploy-monitoring.sh prod \
  anchor-alpha-momentum-processor-prod \
  anchor-alpha-data-prod \
  admin@example.com
```

## Metrics and Alarms

### Custom CloudWatch Metrics

**Namespace: `AnchorAlpha/MomentumScreener`**
- `ExecutionDuration` - Time taken for complete pipeline execution
- `ExecutionSuccess` - Success/failure indicator (1/0)
- `StocksFetched` - Number of stocks retrieved from FMP API
- `StocksProcessed` - Number of stocks successfully processed
- `SummariesGenerated` - Number of AI summaries created
- `FMPAPICalls` - Number of FMP API requests
- `FMPAPIErrors` - Number of FMP API failures
- `PerplexityAPICalls` - Number of Perplexity API requests
- `PerplexityAPIErrors` - Number of Perplexity API failures
- `S3Uploads` - Number of successful S3 uploads
- `S3UploadErrors` - Number of failed S3 uploads
- `ErrorCount` - Total number of errors per execution
- `WarningCount` - Total number of warnings per execution

**Namespace: `AnchorAlpha/APIUsage`**
- `APIRateLimitUtilization` - Percentage of rate limit used
- `APICallCount` - Number of API calls per hour
- `APIErrorCount` - Number of API errors per hour
- `APIAverageResponseTime` - Average API response time
- `APIEstimatedCost` - Estimated cost of API usage

### CloudWatch Alarms

1. **High Error Rate** - Triggers when error count > 5 in 10 minutes
2. **API Rate Limit** - Triggers when rate limit utilization > 90%
3. **Long Execution** - Triggers when execution time > 10 minutes
4. **S3 Upload Failure** - Triggers on any S3 upload failure
5. **Processing Success Rate** - Triggers when success rate < 80%

## SNS Notifications

### Critical Error Notifications
Sent when:
- Pipeline execution fails completely
- Multiple consecutive errors occur
- Critical system components fail

**Includes:**
- Execution ID and timestamp
- Error details and context
- Performance metrics summary
- Recent error history

### Budget Alerts
Sent when:
- Monthly spending exceeds 80% of budget
- Forecasted spending exceeds 100% of budget

### Rate Limit Warnings
Sent when:
- API rate limit utilization exceeds 85%
- Multiple rate limit hits occur

## Configuration

### Environment Variables
```bash
# Required for CloudWatch and SNS
AWS_REGION=us-east-1
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:anchor-alpha-notifications

# Optional for enhanced monitoring
CLOUDWATCH_NAMESPACE=AnchorAlpha/MomentumScreener
LOG_LEVEL=INFO
```

### Monitoring Configuration (`infrastructure/config/monitoring-config.json`)
Contains detailed configuration for:
- CloudWatch metrics and alarms
- API rate limits and thresholds
- Notification settings
- Logging preferences

## Log Analysis

### CloudWatch Insights Queries

**Recent Errors:**
```sql
fields @timestamp, level, message, execution_id, error_type
| filter level = "ERROR"
| sort @timestamp desc
| limit 20
```

**API Performance:**
```sql
fields @timestamp, api_name, duration_seconds, success
| filter api_name exists
| stats avg(duration_seconds) by api_name
```

**Execution Summary:**
```sql
fields @timestamp, execution_id, stocks_fetched, stocks_processed, duration_seconds
| filter message like /Final metrics/
| sort @timestamp desc
```

### Log Structure
All logs follow a consistent JSON structure:
```json
{
  "timestamp": "2026-03-01T12:00:00Z",
  "level": "INFO",
  "logger": "LambdaOrchestrator",
  "execution_id": "20260301_120000",
  "message": "Processing completed successfully",
  "stocks_fetched": 100,
  "stocks_processed": 95,
  "duration_seconds": 120.5
}
```

## Cost Optimization

### API Usage Tracking
- Real-time rate limit monitoring
- Cost estimation per API call
- Usage pattern analysis
- Optimization recommendations

### Recommendations Engine
Automatically generates suggestions for:
- Reducing API call frequency
- Implementing caching strategies
- Optimizing error handling
- Improving response times

## Troubleshooting

### Common Issues

1. **High Error Rates**
   - Check CloudWatch logs for specific error messages
   - Verify API key validity and rate limits
   - Review network connectivity and timeouts

2. **Rate Limit Hits**
   - Monitor API usage patterns
   - Implement exponential backoff
   - Consider request batching

3. **Long Execution Times**
   - Analyze processing bottlenecks
   - Check API response times
   - Review data volume and complexity

4. **Missing Metrics**
   - Verify CloudWatch permissions
   - Check metric publishing code
   - Review AWS region configuration

### Debug Mode
Enable detailed logging by setting:
```bash
LOG_LEVEL=DEBUG
```

This provides additional context for:
- API request/response details
- Processing step timing
- Data transformation logs
- Error stack traces

## Maintenance

### Regular Tasks
1. **Weekly**: Review CloudWatch dashboards and alarms
2. **Monthly**: Analyze usage reports and cost optimization
3. **Quarterly**: Update rate limits and thresholds
4. **Annually**: Review and update monitoring configuration

### Log Retention
- Lambda logs: 30 days
- Custom metrics logs: 30 days
- API usage logs: 90 days
- Error logs: 90 days

### Backup and Recovery
- CloudWatch dashboards are version controlled
- Alarm configurations are in CloudFormation templates
- Monitoring code is tested and documented

## Testing

Run the monitoring system tests:
```bash
# Test logging utilities
python -m pytest tst/AnchorAlpha/test_logging_utils.py -v

# Test API monitoring
python -m pytest tst/AnchorAlpha/test_api_monitoring.py -v
```

## Support

For issues with the monitoring system:
1. Check CloudWatch logs for error details
2. Review SNS notifications for alerts
3. Consult the troubleshooting guide above
4. Contact the development team with execution IDs and timestamps