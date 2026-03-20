"""
Enhanced logging utilities for AnchorAlpha monitoring and observability.

This module provides structured JSON logging, metrics tracking, and CloudWatch integration
for comprehensive system monitoring and debugging.

Requirements: 8.1, 8.2, 8.3
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import traceback
import boto3
from botocore.exceptions import ClientError


@dataclass
class ExecutionMetrics:
    """Container for execution metrics and performance data."""
    execution_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    success: bool = False
    
    # API metrics
    fmp_api_calls: int = 0
    fmp_api_errors: int = 0
    fmp_api_total_time: float = 0.0
    perplexity_api_calls: int = 0
    perplexity_api_errors: int = 0
    perplexity_api_total_time: float = 0.0
    
    # Data processing metrics
    stocks_fetched: int = 0
    stocks_processed: int = 0
    summaries_generated: int = 0
    s3_uploads: int = 0
    s3_upload_errors: int = 0
    
    # Error tracking
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def add_error(self, error_message: str):
        """Add an error to the metrics."""
        self.errors.append(error_message)
        self.success = False
    
    def add_warning(self, warning_message: str):
        """Add a warning to the metrics."""
        self.warnings.append(warning_message)
    
    def finalize(self):
        """Finalize metrics by calculating duration and setting end time."""
        self.end_time = datetime.now(timezone.utc).isoformat()
        if self.start_time and self.end_time:
            start_dt = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
            self.duration_seconds = (end_dt - start_dt).total_seconds()
        
        # Set success based on error count
        if not self.errors:
            self.success = True


class StructuredLogger:
    """Enhanced structured logger with CloudWatch integration."""
    
    def __init__(self, name: str, execution_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.execution_id = execution_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.metrics = ExecutionMetrics(
            execution_id=self.execution_id,
            start_time=datetime.now(timezone.utc).isoformat()
        )
        
        # Configure structured formatter if not already configured
        if not self.logger.handlers or not any(
            isinstance(h.formatter, StructuredFormatter) for h in self.logger.handlers
        ):
            self._configure_structured_logging()
    
    def _configure_structured_logging(self):
        """Configure structured JSON logging format."""
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler with structured formatter
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _create_log_entry(self, level: str, message: str, **extra_fields) -> Dict[str, Any]:
        """Create structured log entry with standard fields."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "logger": self.logger.name,
            "execution_id": self.execution_id,
            "message": message,
            **extra_fields
        }
        return log_entry
    
    def info(self, message: str, **extra_fields):
        """Log info message with structured format."""
        log_entry = self._create_log_entry("INFO", message, **extra_fields)
        self.logger.info(json.dumps(log_entry))
    
    def warning(self, message: str, **extra_fields):
        """Log warning message with structured format."""
        log_entry = self._create_log_entry("WARNING", message, **extra_fields)
        self.logger.warning(json.dumps(log_entry))
        self.metrics.add_warning(message)
    
    def error(self, message: str, exception: Optional[Exception] = None, **extra_fields):
        """Log error message with structured format and exception details."""
        log_entry = self._create_log_entry("ERROR", message, **extra_fields)
        
        if exception:
            log_entry["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc()
            }
        
        self.logger.error(json.dumps(log_entry))
        self.metrics.add_error(message)
    
    def debug(self, message: str, **extra_fields):
        """Log debug message with structured format."""
        log_entry = self._create_log_entry("DEBUG", message, **extra_fields)
        self.logger.debug(json.dumps(log_entry))
    
    @contextmanager
    def api_call_timer(self, api_name: str, endpoint: str):
        """Context manager for timing API calls and tracking metrics."""
        start_time = time.time()
        call_info = {
            "api_name": api_name,
            "endpoint": endpoint,
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        
        self.info(f"Starting {api_name} API call", **call_info)
        
        try:
            yield
            
            # Success - update metrics
            duration = time.time() - start_time
            call_info.update({
                "duration_seconds": duration,
                "status": "success"
            })
            
            if api_name.lower() == "fmp":
                self.metrics.fmp_api_calls += 1
                self.metrics.fmp_api_total_time += duration
            elif api_name.lower() == "perplexity":
                self.metrics.perplexity_api_calls += 1
                self.metrics.perplexity_api_total_time += duration
            
            self.info(f"Completed {api_name} API call", **call_info)
            
        except Exception as e:
            # Error - update error metrics
            duration = time.time() - start_time
            call_info.update({
                "duration_seconds": duration,
                "status": "error",
                "error_message": str(e)
            })
            
            if api_name.lower() == "fmp":
                self.metrics.fmp_api_errors += 1
            elif api_name.lower() == "perplexity":
                self.metrics.perplexity_api_errors += 1
            
            self.error(f"Failed {api_name} API call", exception=e, **call_info)
            raise
    
    def log_processing_metrics(self, phase: str, **metrics):
        """Log processing phase metrics."""
        self.info(f"Processing phase: {phase}", phase=phase, **metrics)
        
        # Update internal metrics
        if "stocks_fetched" in metrics:
            self.metrics.stocks_fetched = metrics["stocks_fetched"]
        if "stocks_processed" in metrics:
            self.metrics.stocks_processed = metrics["stocks_processed"]
        if "summaries_generated" in metrics:
            self.metrics.summaries_generated = metrics["summaries_generated"]
    
    def log_s3_operation(self, operation: str, bucket: str, key: str, success: bool, **extra_fields):
        """Log S3 operations with metrics tracking."""
        log_data = {
            "operation": operation,
            "bucket": bucket,
            "key": key,
            "success": success,
            **extra_fields
        }
        
        if success:
            self.info(f"S3 {operation} successful", **log_data)
            if operation == "upload":
                self.metrics.s3_uploads += 1
        else:
            self.error(f"S3 {operation} failed", **log_data)
            if operation == "upload":
                self.metrics.s3_upload_errors += 1
    
    def get_metrics(self) -> ExecutionMetrics:
        """Get current execution metrics."""
        return self.metrics
    
    def finalize_and_log_metrics(self):
        """Finalize metrics and log comprehensive execution summary."""
        self.metrics.finalize()
        
        self.info(
            "Execution completed - Final metrics",
            **asdict(self.metrics)
        )


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record):
        """Format log record as structured JSON."""
        try:
            # Try to parse message as JSON first (for already structured logs)
            log_entry = json.loads(record.getMessage())
        except (json.JSONDecodeError, ValueError):
            # Fallback to creating structured entry
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "function": getattr(record, 'funcName', ''),
                "line": getattr(record, 'lineno', ''),
            }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, default=str)


class CloudWatchMetricsPublisher:
    """Publisher for custom CloudWatch metrics."""
    
    def __init__(self, namespace: str = "AnchorAlpha/MomentumScreener"):
        self.namespace = namespace
        self.cloudwatch = boto3.client('cloudwatch')
    
    def publish_execution_metrics(self, metrics: ExecutionMetrics):
        """Publish execution metrics to CloudWatch."""
        try:
            metric_data = []
            
            # Duration metric
            if metrics.duration_seconds is not None:
                metric_data.append({
                    'MetricName': 'ExecutionDuration',
                    'Value': metrics.duration_seconds,
                    'Unit': 'Seconds',
                    'Dimensions': [
                        {'Name': 'ExecutionId', 'Value': metrics.execution_id}
                    ]
                })
            
            # Success/failure metric
            metric_data.append({
                'MetricName': 'ExecutionSuccess',
                'Value': 1 if metrics.success else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'ExecutionId', 'Value': metrics.execution_id}
                ]
            })
            
            # API call metrics
            if metrics.fmp_api_calls > 0:
                metric_data.extend([
                    {
                        'MetricName': 'FMPAPICalls',
                        'Value': metrics.fmp_api_calls,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'FMPAPIErrors',
                        'Value': metrics.fmp_api_errors,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'FMPAPIAverageResponseTime',
                        'Value': metrics.fmp_api_total_time / metrics.fmp_api_calls,
                        'Unit': 'Seconds'
                    }
                ])
            
            if metrics.perplexity_api_calls > 0:
                metric_data.extend([
                    {
                        'MetricName': 'PerplexityAPICalls',
                        'Value': metrics.perplexity_api_calls,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'PerplexityAPIErrors',
                        'Value': metrics.perplexity_api_errors,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'PerplexityAPIAverageResponseTime',
                        'Value': metrics.perplexity_api_total_time / metrics.perplexity_api_calls,
                        'Unit': 'Seconds'
                    }
                ])
            
            # Data processing metrics
            metric_data.extend([
                {
                    'MetricName': 'StocksFetched',
                    'Value': metrics.stocks_fetched,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'StocksProcessed',
                    'Value': metrics.stocks_processed,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'SummariesGenerated',
                    'Value': metrics.summaries_generated,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'S3Uploads',
                    'Value': metrics.s3_uploads,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'S3UploadErrors',
                    'Value': metrics.s3_upload_errors,
                    'Unit': 'Count'
                }
            ])
            
            # Error count metrics
            metric_data.extend([
                {
                    'MetricName': 'ErrorCount',
                    'Value': len(metrics.errors),
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'WarningCount',
                    'Value': len(metrics.warnings),
                    'Unit': 'Count'
                }
            ])
            
            # Publish metrics in batches (CloudWatch limit is 20 per call)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logging.info(f"Published {len(metric_data)} metrics to CloudWatch")
            
        except ClientError as e:
            logging.error(f"Failed to publish CloudWatch metrics: {e}")
        except Exception as e:
            logging.error(f"Unexpected error publishing metrics: {e}")
    
    def publish_api_rate_limit_metrics(self, api_name: str, requests_made: int, rate_limit: int):
        """Publish API rate limit utilization metrics."""
        try:
            utilization_percentage = (requests_made / rate_limit) * 100
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'APIRateLimitUtilization',
                        'Value': utilization_percentage,
                        'Unit': 'Percent',
                        'Dimensions': [
                            {'Name': 'APIName', 'Value': api_name}
                        ]
                    },
                    {
                        'MetricName': 'APIRequestCount',
                        'Value': requests_made,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'APIName', 'Value': api_name}
                        ]
                    }
                ]
            )
            
        except Exception as e:
            logging.error(f"Failed to publish rate limit metrics for {api_name}: {e}")


class SNSNotificationManager:
    """Manager for sending SNS notifications for critical events."""
    
    def __init__(self, topic_arn: Optional[str] = None):
        self.topic_arn = topic_arn or os.getenv("SNS_TOPIC_ARN")
        self.sns = boto3.client('sns') if self.topic_arn else None
    
    def send_critical_error_notification(self, error_message: str, execution_id: str, metrics: ExecutionMetrics):
        """Send notification for critical system errors."""
        if not self.sns or not self.topic_arn:
            logging.warning("SNS not configured, skipping error notification")
            return
        
        try:
            subject = f"AnchorAlpha Critical Error - {execution_id}"
            
            message = f"""
AnchorAlpha Momentum Screener encountered a critical error:

Execution ID: {execution_id}
Error: {error_message}
Timestamp: {datetime.now(timezone.utc).isoformat()}

Execution Metrics:
- Duration: {metrics.duration_seconds:.2f} seconds
- Stocks Fetched: {metrics.stocks_fetched}
- Stocks Processed: {metrics.stocks_processed}
- FMP API Calls: {metrics.fmp_api_calls} (Errors: {metrics.fmp_api_errors})
- Perplexity API Calls: {metrics.perplexity_api_calls} (Errors: {metrics.perplexity_api_errors})
- Total Errors: {len(metrics.errors)}
- Total Warnings: {len(metrics.warnings)}

Recent Errors:
{chr(10).join(metrics.errors[-5:])}  # Last 5 errors

Please check CloudWatch logs for detailed information.
            """.strip()
            
            self.sns.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message
            )
            
            logging.info(f"Sent critical error notification for execution {execution_id}")
            
        except Exception as e:
            logging.error(f"Failed to send SNS notification: {e}")
    
    def send_budget_alert(self, current_spend: float, budget_limit: float):
        """Send notification when budget threshold is exceeded."""
        if not self.sns or not self.topic_arn:
            return
        
        try:
            subject = "AnchorAlpha Budget Alert"
            
            message = f"""
AnchorAlpha monthly spending has exceeded the threshold:

Current Spend: ${current_spend:.2f}
Budget Limit: ${budget_limit:.2f}
Utilization: {(current_spend / budget_limit) * 100:.1f}%

Please review AWS costs and consider optimizing resource usage.
            """.strip()
            
            self.sns.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message
            )
            
        except Exception as e:
            logging.error(f"Failed to send budget alert: {e}")


# Global logger instance for easy access
def get_logger(name: str, execution_id: Optional[str] = None) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name, execution_id)