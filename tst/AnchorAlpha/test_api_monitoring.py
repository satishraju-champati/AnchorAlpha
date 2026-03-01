"""
Tests for API monitoring and rate limiting functionality.

Requirements: 8.2, 8.3, 8.4
"""

import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from AnchorAlpha.utils.api_monitoring import (
    APICallRecord,
    APIUsageStats,
    APIRateLimitTracker,
    APIUsageMonitor,
    get_api_monitor
)


class TestAPICallRecord:
    """Test APICallRecord dataclass."""
    
    def test_initialization(self):
        """Test APICallRecord initialization."""
        timestamp = datetime.now(timezone.utc).isoformat()
        record = APICallRecord(
            timestamp=timestamp,
            api_name="FMP",
            endpoint="stock-screener",
            duration_seconds=1.5,
            success=True,
            status_code=200,
            request_size=1024,
            response_size=2048
        )
        
        assert record.timestamp == timestamp
        assert record.api_name == "FMP"
        assert record.endpoint == "stock-screener"
        assert record.duration_seconds == 1.5
        assert record.success is True
        assert record.status_code == 200
        assert record.request_size == 1024
        assert record.response_size == 2048


class TestAPIUsageStats:
    """Test APIUsageStats dataclass."""
    
    def test_initialization(self):
        """Test APIUsageStats initialization."""
        stats = APIUsageStats(
            api_name="FMP",
            time_period="last_24_hours",
            total_calls=100,
            successful_calls=95,
            failed_calls=5,
            total_duration=150.0,
            average_duration=1.5,
            min_duration=0.5,
            max_duration=5.0,
            rate_limit_hits=2,
            estimated_cost=10.0
        )
        
        assert stats.api_name == "FMP"
        assert stats.total_calls == 100
        assert stats.successful_calls == 95
        assert stats.failed_calls == 5
        assert stats.average_duration == 1.5
        assert stats.rate_limit_hits == 2
        assert stats.estimated_cost == 10.0


class TestAPIRateLimitTracker:
    """Test API rate limit tracking functionality."""
    
    def test_initialization(self):
        """Test rate limit tracker initialization."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        assert tracker.api_name == "FMP"
        assert tracker.requests_per_minute == 300
        assert tracker.requests_per_day == 10000
        assert len(tracker.minute_requests) == 0
        assert len(tracker.daily_requests) == 0
        assert tracker.rate_limit_hits == 0
    
    def test_can_make_request_empty(self):
        """Test can_make_request with no previous requests."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        assert tracker.can_make_request() is True
    
    def test_can_make_request_under_limit(self):
        """Test can_make_request under rate limits."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        # Add some requests under the limit
        for _ in range(250):
            tracker.record_request()
        
        assert tracker.can_make_request() is True
    
    def test_can_make_request_at_minute_limit(self):
        """Test can_make_request at minute rate limit."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        # Fill up to the minute limit
        for _ in range(300):
            tracker.record_request()
        
        assert tracker.can_make_request() is False
    
    def test_can_make_request_at_daily_limit(self):
        """Test can_make_request at daily rate limit."""
        tracker = APIRateLimitTracker("FMP", 300, 100)  # Low daily limit for testing
        
        # Fill up to the daily limit
        for _ in range(100):
            tracker.record_request()
        
        assert tracker.can_make_request() is False
    
    def test_record_request(self):
        """Test recording API requests."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        initial_minute_count = len(tracker.minute_requests)
        initial_daily_count = len(tracker.daily_requests)
        
        tracker.record_request()
        
        assert len(tracker.minute_requests) == initial_minute_count + 1
        assert len(tracker.daily_requests) == initial_daily_count + 1
    
    def test_wait_for_rate_limit_no_wait(self):
        """Test wait_for_rate_limit when no wait is needed."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        wait_time = tracker.wait_for_rate_limit()
        
        assert wait_time == 0.0
        assert tracker.rate_limit_hits == 0
    
    def test_wait_for_rate_limit_minute_limit(self):
        """Test wait_for_rate_limit when minute limit is hit."""
        tracker = APIRateLimitTracker("FMP", 2, 1000)  # Low limit for testing
        
        # Fill up the minute limit
        tracker.record_request()
        tracker.record_request()
        
        wait_time = tracker.wait_for_rate_limit()
        
        assert wait_time > 0
        assert tracker.rate_limit_hits == 1
        assert tracker.last_rate_limit_hit is not None
    
    def test_get_utilization_stats(self):
        """Test getting utilization statistics."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        # Add some requests
        for _ in range(150):
            tracker.record_request()
        
        stats = tracker.get_utilization_stats()
        
        assert stats["api_name"] == "FMP"
        assert stats["minute_utilization"] == 50.0  # 150/300 * 100
        assert stats["daily_utilization"] == 1.5  # 150/10000 * 100
        assert stats["requests_in_last_minute"] == 150
        assert stats["requests_in_last_day"] == 150
        assert stats["rate_limit_hits"] == 0
    
    def test_old_requests_cleanup(self):
        """Test that old requests are cleaned up properly."""
        tracker = APIRateLimitTracker("FMP", 300, 10000)
        
        # Mock time to simulate old requests
        with patch('time.time') as mock_time:
            # Set initial time
            mock_time.return_value = 1000.0
            
            # Add some requests
            for _ in range(10):
                tracker.record_request()
            
            # Move time forward by 2 minutes
            mock_time.return_value = 1120.0  # 1000 + 120 seconds
            
            # Check utilization - old requests should be cleaned up
            stats = tracker.get_utilization_stats()
            
            assert stats["requests_in_last_minute"] == 0


class TestAPIUsageMonitor:
    """Test comprehensive API usage monitoring."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = APIUsageMonitor()
    
    def test_initialization(self):
        """Test monitor initialization."""
        assert len(self.monitor.call_records) == 0
        assert "FMP" in self.monitor.rate_limiters
        assert "Perplexity" in self.monitor.rate_limiters
        assert "FMP" in self.monitor.api_costs
        assert "Perplexity" in self.monitor.api_costs
    
    def test_record_api_call(self):
        """Test recording API calls."""
        self.monitor.record_api_call(
            api_name="FMP",
            endpoint="stock-screener",
            duration_seconds=1.5,
            success=True,
            status_code=200,
            request_size=1024,
            response_size=2048
        )
        
        assert len(self.monitor.call_records) == 1
        
        record = self.monitor.call_records[0]
        assert record.api_name == "FMP"
        assert record.endpoint == "stock-screener"
        assert record.duration_seconds == 1.5
        assert record.success is True
        assert record.status_code == 200
    
    def test_check_rate_limit(self):
        """Test rate limit checking."""
        # Should return 0 for unknown API
        wait_time = self.monitor.check_rate_limit("UnknownAPI")
        assert wait_time == 0.0
        
        # Should return 0 for known API under limit
        wait_time = self.monitor.check_rate_limit("FMP")
        assert wait_time == 0.0
    
    def test_get_usage_stats_empty(self):
        """Test getting usage stats with no data."""
        stats = self.monitor.get_usage_stats()
        
        assert len(stats) == 0
    
    def test_get_usage_stats_with_data(self):
        """Test getting usage stats with recorded data."""
        # Record some API calls
        for i in range(10):
            self.monitor.record_api_call(
                api_name="FMP",
                endpoint="stock-screener",
                duration_seconds=1.0 + i * 0.1,
                success=i < 8,  # 8 successful, 2 failed
                status_code=200 if i < 8 else 500
            )
        
        stats = self.monitor.get_usage_stats(api_name="FMP")
        
        assert len(stats) == 1
        fmp_stats = stats[0]
        
        assert fmp_stats.api_name == "FMP"
        assert fmp_stats.total_calls == 10
        assert fmp_stats.successful_calls == 8
        assert fmp_stats.failed_calls == 2
        assert fmp_stats.min_duration == 1.0
        assert fmp_stats.max_duration == 1.9
        assert fmp_stats.estimated_cost > 0
    
    def test_get_usage_stats_time_filtering(self):
        """Test usage stats with time filtering."""
        # Record calls with different timestamps
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        recent_time = datetime.now(timezone.utc).isoformat()
        
        # Add old call (should be filtered out)
        old_record = APICallRecord(
            timestamp=old_time,
            api_name="FMP",
            endpoint="old-call",
            duration_seconds=1.0,
            success=True
        )
        self.monitor.call_records.append(old_record)
        
        # Add recent call (should be included)
        recent_record = APICallRecord(
            timestamp=recent_time,
            api_name="FMP",
            endpoint="recent-call",
            duration_seconds=2.0,
            success=True
        )
        self.monitor.call_records.append(recent_record)
        
        stats = self.monitor.get_usage_stats(hours=24)
        
        assert len(stats) == 1
        fmp_stats = stats[0]
        assert fmp_stats.total_calls == 1  # Only recent call
        assert fmp_stats.average_duration == 2.0
    
    def test_get_rate_limit_status(self):
        """Test getting rate limit status."""
        # Record some calls
        for _ in range(50):
            self.monitor.record_api_call(
                api_name="FMP",
                endpoint="test",
                duration_seconds=1.0,
                success=True
            )
        
        status = self.monitor.get_rate_limit_status()
        
        assert "FMP" in status
        assert "Perplexity" in status
        
        fmp_status = status["FMP"]
        assert fmp_status["api_name"] == "FMP"
        assert fmp_status["requests_in_last_minute"] == 50
        assert fmp_status["minute_utilization"] > 0
    
    def test_generate_usage_report(self):
        """Test generating comprehensive usage report."""
        # Record some test data
        for i in range(5):
            self.monitor.record_api_call(
                api_name="FMP",
                endpoint="test",
                duration_seconds=1.0,
                success=True
            )
            
            self.monitor.record_api_call(
                api_name="Perplexity",
                endpoint="chat",
                duration_seconds=2.0,
                success=i < 4  # 4 successful, 1 failed
            )
        
        report = self.monitor.generate_usage_report(hours=24)
        
        assert "report_timestamp" in report
        assert "time_period_hours" in report
        assert "summary" in report
        assert "api_stats" in report
        assert "rate_limit_status" in report
        assert "recommendations" in report
        
        summary = report["summary"]
        assert summary["total_api_calls"] == 10
        assert summary["total_errors"] == 1
        assert summary["average_success_rate"] == 90.0  # 9/10 * 100
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        # Create stats with high error rate
        high_error_stats = [
            APIUsageStats(
                api_name="TestAPI",
                time_period="test",
                total_calls=10,
                successful_calls=5,
                failed_calls=5,  # 50% error rate
                total_duration=10.0,
                average_duration=1.0,
                min_duration=0.5,
                max_duration=2.0,
                rate_limit_hits=0,
                estimated_cost=0.1
            )
        ]
        
        rate_limit_status = {
            "TestAPI": {
                "minute_utilization": 85.0,  # High utilization
                "requests_in_last_minute": 255
            }
        }
        
        recommendations = self.monitor._generate_recommendations(
            high_error_stats, 
            rate_limit_status
        )
        
        assert len(recommendations) >= 2
        assert any("High error rate" in rec for rec in recommendations)
        assert any("High rate limit utilization" in rec for rec in recommendations)
    
    @patch('boto3.client')
    def test_publish_metrics_to_cloudwatch(self, mock_boto_client):
        """Test publishing metrics to CloudWatch."""
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        # Record some test data
        self.monitor.record_api_call(
            api_name="FMP",
            endpoint="test",
            duration_seconds=1.0,
            success=True
        )
        
        self.monitor.publish_metrics_to_cloudwatch()
        
        # Verify CloudWatch was called
        mock_cloudwatch.put_metric_data.assert_called()
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        assert call_args[1]['Namespace'] == 'AnchorAlpha/APIUsage'
        
        metric_data = call_args[1]['MetricData']
        assert len(metric_data) > 0
        
        # Check for expected metrics
        metric_names = [metric['MetricName'] for metric in metric_data]
        assert 'APICallCount' in metric_names
        assert 'APIAverageResponseTime' in metric_names
    
    @patch('boto3.client')
    def test_save_usage_report_to_s3(self, mock_boto_client):
        """Test saving usage report to S3."""
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Record some test data
        self.monitor.record_api_call(
            api_name="FMP",
            endpoint="test",
            duration_seconds=1.0,
            success=True
        )
        
        self.monitor.save_usage_report_to_s3("test-bucket")
        
        # Verify S3 put_object was called
        mock_s3.put_object.assert_called_once()
        
        call_args = mock_s3.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert 'api-usage-reports' in call_args[1]['Key']
        assert call_args[1]['ContentType'] == 'application/json'
        
        # Verify the report content is valid JSON
        report_body = call_args[1]['Body']
        parsed_report = json.loads(report_body)
        assert 'report_timestamp' in parsed_report
        assert 'summary' in parsed_report


class TestGetAPIMonitor:
    """Test the global API monitor function."""
    
    def test_get_api_monitor_singleton(self):
        """Test that get_api_monitor returns the same instance."""
        monitor1 = get_api_monitor()
        monitor2 = get_api_monitor()
        
        assert monitor1 is monitor2
        assert isinstance(monitor1, APIUsageMonitor)
    
    def test_get_api_monitor_initialization(self):
        """Test that the global monitor is properly initialized."""
        monitor = get_api_monitor()
        
        assert "FMP" in monitor.rate_limiters
        assert "Perplexity" in monitor.rate_limiters
        assert len(monitor.call_records) >= 0  # May have records from other tests


class TestIntegration:
    """Integration tests for API monitoring system."""
    
    def test_complete_monitoring_workflow(self):
        """Test complete API monitoring workflow."""
        monitor = APIUsageMonitor()
        
        # Simulate a series of API calls
        api_calls = [
            ("FMP", "stock-screener", 1.2, True, 200),
            ("FMP", "historical-price", 2.1, True, 200),
            ("FMP", "company-profile", 0.8, False, 500),
            ("Perplexity", "chat/completions", 3.5, True, 200),
            ("Perplexity", "chat/completions", 2.8, True, 200),
        ]
        
        for api_name, endpoint, duration, success, status_code in api_calls:
            # Check rate limits
            wait_time = monitor.check_rate_limit(api_name)
            if wait_time > 0:
                time.sleep(wait_time)
            
            # Record the call
            monitor.record_api_call(
                api_name=api_name,
                endpoint=endpoint,
                duration_seconds=duration,
                success=success,
                status_code=status_code
            )
        
        # Generate comprehensive report
        report = monitor.generate_usage_report()
        
        # Verify report structure and content
        assert report["summary"]["total_api_calls"] == 5
        assert report["summary"]["total_errors"] == 1
        assert len(report["api_stats"]) == 2  # FMP and Perplexity
        
        # Check API-specific stats
        fmp_stats = next(s for s in report["api_stats"] if s["api_name"] == "FMP")
        assert fmp_stats["total_calls"] == 3
        assert fmp_stats["failed_calls"] == 1
        
        perplexity_stats = next(s for s in report["api_stats"] if s["api_name"] == "Perplexity")
        assert perplexity_stats["total_calls"] == 2
        assert perplexity_stats["failed_calls"] == 0
        
        # Verify rate limit status
        rate_status = monitor.get_rate_limit_status()
        assert "FMP" in rate_status
        assert "Perplexity" in rate_status
        
        # Check recommendations
        recommendations = report["recommendations"]
        assert isinstance(recommendations, list)
    
    @patch('boto3.client')
    def test_monitoring_with_aws_integration(self, mock_boto_client):
        """Test monitoring with AWS CloudWatch and S3 integration."""
        # Mock AWS clients
        mock_cloudwatch = Mock()
        mock_s3 = Mock()
        mock_boto_client.side_effect = lambda service: {
            'cloudwatch': mock_cloudwatch,
            's3': mock_s3
        }[service]
        
        monitor = APIUsageMonitor()
        
        # Record some API calls
        for i in range(3):
            monitor.record_api_call(
                api_name="FMP",
                endpoint="test",
                duration_seconds=1.0 + i * 0.5,
                success=True,
                status_code=200
            )
        
        # Publish metrics to CloudWatch
        monitor.publish_metrics_to_cloudwatch()
        
        # Save report to S3
        monitor.save_usage_report_to_s3("test-bucket")
        
        # Verify AWS interactions
        mock_cloudwatch.put_metric_data.assert_called()
        mock_s3.put_object.assert_called()
        
        # Verify CloudWatch metrics
        cw_call_args = mock_cloudwatch.put_metric_data.call_args
        assert cw_call_args[1]['Namespace'] == 'AnchorAlpha/APIUsage'
        
        # Verify S3 report
        s3_call_args = mock_s3.put_object.call_args
        assert s3_call_args[1]['Bucket'] == 'test-bucket'
        assert s3_call_args[1]['ContentType'] == 'application/json'


if __name__ == "__main__":
    pytest.main([__file__])