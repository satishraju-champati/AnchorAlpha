"""
API usage tracking and rate limit monitoring for AnchorAlpha.

This module provides comprehensive monitoring of API usage patterns,
rate limit tracking, and cost optimization insights.

Requirements: 8.2, 8.3, 8.4
"""

import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import boto3
from botocore.exceptions import ClientError

from .logging_utils import StructuredLogger


@dataclass
class APICallRecord:
    """Record of an individual API call."""
    timestamp: str
    api_name: str
    endpoint: str
    duration_seconds: float
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None


@dataclass
class APIUsageStats:
    """Statistics for API usage over a time period."""
    api_name: str
    time_period: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_duration: float
    average_duration: float
    min_duration: float
    max_duration: float
    rate_limit_hits: int
    estimated_cost: float


class APIRateLimitTracker:
    """Tracks API rate limits and usage patterns."""
    
    def __init__(self, api_name: str, requests_per_minute: int, requests_per_day: Optional[int] = None):
        self.api_name = api_name
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        
        # Track requests in sliding windows
        self.minute_requests = deque()
        self.daily_requests = deque()
        
        # Rate limit hit tracking
        self.rate_limit_hits = 0
        self.last_rate_limit_hit = None
        
        self.logger = StructuredLogger(f"APIRateLimit.{api_name}")
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without hitting rate limits."""
        now = time.time()
        
        # Clean old requests from minute window
        while self.minute_requests and now - self.minute_requests[0] > 60:
            self.minute_requests.popleft()
        
        # Clean old requests from daily window
        if self.requests_per_day:
            while self.daily_requests and now - self.daily_requests[0] > 86400:
                self.daily_requests.popleft()
        
        # Check minute limit
        if len(self.minute_requests) >= self.requests_per_minute:
            return False
        
        # Check daily limit
        if self.requests_per_day and len(self.daily_requests) >= self.requests_per_day:
            return False
        
        return True
    
    def record_request(self):
        """Record a new API request."""
        now = time.time()
        self.minute_requests.append(now)
        if self.requests_per_day:
            self.daily_requests.append(now)
    
    def wait_for_rate_limit(self) -> float:
        """Calculate how long to wait before next request."""
        if self.can_make_request():
            return 0.0
        
        now = time.time()
        
        # Calculate wait time for minute limit
        minute_wait = 0.0
        if len(self.minute_requests) >= self.requests_per_minute:
            oldest_request = self.minute_requests[0]
            minute_wait = 60 - (now - oldest_request)
        
        # Calculate wait time for daily limit
        daily_wait = 0.0
        if self.requests_per_day and len(self.daily_requests) >= self.requests_per_day:
            oldest_request = self.daily_requests[0]
            daily_wait = 86400 - (now - oldest_request)
        
        wait_time = max(minute_wait, daily_wait)
        
        if wait_time > 0:
            self.rate_limit_hits += 1
            self.last_rate_limit_hit = datetime.now(timezone.utc).isoformat()
            
            self.logger.warning(
                f"Rate limit hit for {self.api_name}",
                wait_time_seconds=wait_time,
                minute_requests=len(self.minute_requests),
                daily_requests=len(self.daily_requests) if self.requests_per_day else None
            )
        
        return wait_time
    
    def get_utilization_stats(self) -> Dict[str, Any]:
        """Get current rate limit utilization statistics."""
        now = time.time()
        
        # Clean old requests
        while self.minute_requests and now - self.minute_requests[0] > 60:
            self.minute_requests.popleft()
        
        if self.requests_per_day:
            while self.daily_requests and now - self.daily_requests[0] > 86400:
                self.daily_requests.popleft()
        
        return {
            "api_name": self.api_name,
            "minute_utilization": (len(self.minute_requests) / self.requests_per_minute) * 100,
            "daily_utilization": (len(self.daily_requests) / self.requests_per_day) * 100 if self.requests_per_day else None,
            "requests_in_last_minute": len(self.minute_requests),
            "requests_in_last_day": len(self.daily_requests) if self.requests_per_day else None,
            "rate_limit_hits": self.rate_limit_hits,
            "last_rate_limit_hit": self.last_rate_limit_hit
        }


class APIUsageMonitor:
    """Comprehensive API usage monitoring and analytics."""
    
    def __init__(self):
        self.call_records: List[APICallRecord] = []
        self.rate_limiters: Dict[str, APIRateLimitTracker] = {}
        self.logger = StructuredLogger("APIUsageMonitor")
        
        # Cost tracking (estimated)
        self.api_costs = {
            "FMP": 0.0001,  # Estimated cost per request
            "Perplexity": 0.002  # Estimated cost per request
        }
        
        # Initialize rate limiters for known APIs
        self.rate_limiters["FMP"] = APIRateLimitTracker("FMP", 300, 10000)  # 300/min, 10k/day
        self.rate_limiters["Perplexity"] = APIRateLimitTracker("Perplexity", 60, 1000)  # 60/min, 1k/day
    
    def record_api_call(
        self,
        api_name: str,
        endpoint: str,
        duration_seconds: float,
        success: bool,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ):
        """Record an API call for monitoring and analysis."""
        record = APICallRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            api_name=api_name,
            endpoint=endpoint,
            duration_seconds=duration_seconds,
            success=success,
            status_code=status_code,
            error_message=error_message,
            request_size=request_size,
            response_size=response_size
        )
        
        self.call_records.append(record)
        
        # Update rate limiter
        if api_name in self.rate_limiters:
            self.rate_limiters[api_name].record_request()
        
        # Log the call
        self.logger.info(
            f"API call recorded: {api_name}",
            **asdict(record)
        )
    
    def check_rate_limit(self, api_name: str) -> float:
        """Check rate limit and return wait time if needed."""
        if api_name not in self.rate_limiters:
            return 0.0
        
        return self.rate_limiters[api_name].wait_for_rate_limit()
    
    def get_usage_stats(self, api_name: Optional[str] = None, hours: int = 24) -> List[APIUsageStats]:
        """Get usage statistics for APIs."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        # Filter records by time and API
        filtered_records = [
            record for record in self.call_records
            if record.timestamp >= cutoff_str and (api_name is None or record.api_name == api_name)
        ]
        
        # Group by API
        api_groups = defaultdict(list)
        for record in filtered_records:
            api_groups[record.api_name].append(record)
        
        stats = []
        for api, records in api_groups.items():
            if not records:
                continue
            
            successful_calls = sum(1 for r in records if r.success)
            failed_calls = len(records) - successful_calls
            durations = [r.duration_seconds for r in records]
            
            api_stats = APIUsageStats(
                api_name=api,
                time_period=f"last_{hours}_hours",
                total_calls=len(records),
                successful_calls=successful_calls,
                failed_calls=failed_calls,
                total_duration=sum(durations),
                average_duration=sum(durations) / len(durations),
                min_duration=min(durations),
                max_duration=max(durations),
                rate_limit_hits=self.rate_limiters.get(api, APIRateLimitTracker(api, 0)).rate_limit_hits,
                estimated_cost=len(records) * self.api_costs.get(api, 0.001)
            )
            
            stats.append(api_stats)
        
        return stats
    
    def get_rate_limit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current rate limit status for all APIs."""
        status = {}
        for api_name, rate_limiter in self.rate_limiters.items():
            status[api_name] = rate_limiter.get_utilization_stats()
        return status
    
    def generate_usage_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive usage report."""
        stats = self.get_usage_stats(hours=hours)
        rate_limit_status = self.get_rate_limit_status()
        
        total_calls = sum(s.total_calls for s in stats)
        total_cost = sum(s.estimated_cost for s in stats)
        total_errors = sum(s.failed_calls for s in stats)
        
        # Calculate efficiency metrics
        avg_success_rate = (sum(s.successful_calls for s in stats) / total_calls * 100) if total_calls > 0 else 0
        
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "time_period_hours": hours,
            "summary": {
                "total_api_calls": total_calls,
                "total_estimated_cost": total_cost,
                "total_errors": total_errors,
                "average_success_rate": avg_success_rate
            },
            "api_stats": [asdict(stat) for stat in stats],
            "rate_limit_status": rate_limit_status,
            "recommendations": self._generate_recommendations(stats, rate_limit_status)
        }
        
        return report
    
    def _generate_recommendations(self, stats: List[APIUsageStats], rate_limit_status: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on usage patterns."""
        recommendations = []
        
        for stat in stats:
            # High error rate recommendation
            if stat.total_calls > 0 and (stat.failed_calls / stat.total_calls) > 0.1:
                recommendations.append(
                    f"{stat.api_name}: High error rate ({stat.failed_calls}/{stat.total_calls}). "
                    "Consider implementing better error handling and retry logic."
                )
            
            # High cost recommendation
            if stat.estimated_cost > 1.0:
                recommendations.append(
                    f"{stat.api_name}: High estimated cost (${stat.estimated_cost:.2f}). "
                    "Consider caching responses or reducing call frequency."
                )
            
            # Slow response time recommendation
            if stat.average_duration > 5.0:
                recommendations.append(
                    f"{stat.api_name}: Slow average response time ({stat.average_duration:.2f}s). "
                    "Consider implementing timeout handling and parallel processing."
                )
        
        # Rate limit recommendations
        for api_name, status in rate_limit_status.items():
            if status["minute_utilization"] > 80:
                recommendations.append(
                    f"{api_name}: High rate limit utilization ({status['minute_utilization']:.1f}%). "
                    "Consider implementing request batching or spreading calls over time."
                )
        
        return recommendations
    
    def publish_metrics_to_cloudwatch(self):
        """Publish API usage metrics to CloudWatch."""
        try:
            cloudwatch = boto3.client('cloudwatch')
            
            # Get recent stats
            stats = self.get_usage_stats(hours=1)  # Last hour
            rate_limit_status = self.get_rate_limit_status()
            
            metric_data = []
            
            for stat in stats:
                metric_data.extend([
                    {
                        'MetricName': 'APICallCount',
                        'Value': stat.total_calls,
                        'Unit': 'Count',
                        'Dimensions': [{'Name': 'APIName', 'Value': stat.api_name}]
                    },
                    {
                        'MetricName': 'APIErrorCount',
                        'Value': stat.failed_calls,
                        'Unit': 'Count',
                        'Dimensions': [{'Name': 'APIName', 'Value': stat.api_name}]
                    },
                    {
                        'MetricName': 'APIAverageResponseTime',
                        'Value': stat.average_duration,
                        'Unit': 'Seconds',
                        'Dimensions': [{'Name': 'APIName', 'Value': stat.api_name}]
                    },
                    {
                        'MetricName': 'APIEstimatedCost',
                        'Value': stat.estimated_cost,
                        'Unit': 'None',
                        'Dimensions': [{'Name': 'APIName', 'Value': stat.api_name}]
                    }
                ])
            
            # Rate limit utilization metrics
            for api_name, status in rate_limit_status.items():
                metric_data.append({
                    'MetricName': 'APIRateLimitUtilization',
                    'Value': status['minute_utilization'],
                    'Unit': 'Percent',
                    'Dimensions': [{'Name': 'APIName', 'Value': api_name}]
                })
            
            # Publish in batches
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                cloudwatch.put_metric_data(
                    Namespace='AnchorAlpha/APIUsage',
                    MetricData=batch
                )
            
            self.logger.info(f"Published {len(metric_data)} API usage metrics to CloudWatch")
            
        except Exception as e:
            self.logger.error("Failed to publish API usage metrics", exception=e)
    
    def save_usage_report_to_s3(self, bucket: str, key_prefix: str = "api-usage-reports"):
        """Save usage report to S3 for historical analysis."""
        try:
            s3 = boto3.client('s3')
            
            report = self.generate_usage_report()
            
            # Create S3 key with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/%H")
            key = f"{key_prefix}/{timestamp}/usage-report.json"
            
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(report, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            self.logger.info(f"Saved usage report to S3: s3://{bucket}/{key}")
            
        except Exception as e:
            self.logger.error("Failed to save usage report to S3", exception=e)


# Global monitor instance
_global_monitor = None

def get_api_monitor() -> APIUsageMonitor:
    """Get the global API usage monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = APIUsageMonitor()
    return _global_monitor