"""
Tests for logging utilities and monitoring functionality.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import logging

from AnchorAlpha.utils.logging_utils import (
    StructuredLogger,
    ExecutionMetrics,
    CloudWatchMetricsPublisher,
    SNSNotificationManager,
    StructuredFormatter,
    get_logger
)


class TestExecutionMetrics:
    """Test ExecutionMetrics dataclass functionality."""
    
    def test_initialization(self):
        """Test ExecutionMetrics initialization."""
        execution_id = "20260301_120000"
        start_time = datetime.now(timezone.utc).isoformat()
        
        metrics = ExecutionMetrics(
            execution_id=execution_id,
            start_time=start_time
        )
        
        assert metrics.execution_id == execution_id
        assert metrics.start_time == start_time
        assert metrics.end_time is None
        assert metrics.success is False
        assert metrics.errors == []
        assert metrics.warnings == []
        assert metrics.fmp_api_calls == 0
        assert metrics.perplexity_api_calls == 0
    
    def test_add_error(self):
        """Test adding errors to metrics."""
        metrics = ExecutionMetrics("test_id", "2026-03-01T12:00:00Z")
        
        metrics.add_error("Test error message")
        
        assert len(metrics.errors) == 1
        assert "Test error message" in metrics.errors
        assert metrics.success is False
    
    def test_add_warning(self):
        """Test adding warnings to metrics."""
        metrics = ExecutionMetrics("test_id", "2026-03-01T12:00:00Z")
        
        metrics.add_warning("Test warning message")
        
        assert len(metrics.warnings) == 1
        assert "Test warning message" in metrics.warnings
    
    def test_finalize(self):
        """Test metrics finalization."""
        start_time = datetime.now(timezone.utc).isoformat()
        metrics = ExecutionMetrics("test_id", start_time)
        
        # Add a small delay to ensure duration > 0
        time.sleep(0.1)
        
        metrics.finalize()
        
        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None
        assert metrics.duration_seconds > 0
        assert metrics.success is True  # No errors, so should be successful
    
    def test_finalize_with_errors(self):
        """Test finalization with errors sets success to False."""
        metrics = ExecutionMetrics("test_id", "2026-03-01T12:00:00Z")
        metrics.add_error("Test error")
        
        metrics.finalize()
        
        assert metrics.success is False


class TestStructuredFormatter:
    """Test StructuredFormatter functionality."""
    
    def test_format_simple_message(self):
        """Test formatting a simple log message."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed
    
    def test_format_json_message(self):
        """Test formatting a message that's already JSON."""
        formatter = StructuredFormatter()
        json_message = json.dumps({"level": "INFO", "message": "JSON message"})
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=json_message,
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "JSON message"
    
    def test_format_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            import sys
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Error occurred"
        assert "exception" in parsed
        assert "traceback" in parsed["exception"]


class TestStructuredLogger:
    """Test StructuredLogger functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.execution_id = "test_execution_123"
        self.logger = StructuredLogger("TestLogger", self.execution_id)
    
    def test_initialization(self):
        """Test logger initialization."""
        assert self.logger.execution_id == self.execution_id
        assert self.logger.metrics.execution_id == self.execution_id
        assert isinstance(self.logger.metrics, ExecutionMetrics)
    
    @patch('AnchorAlpha.utils.logging_utils.logging.getLogger')
    def test_info_logging(self, mock_get_logger):
        """Test info level logging."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Mock empty handlers list
        mock_get_logger.return_value = mock_logger
        
        logger = StructuredLogger("TestLogger", "test_id")
        logger.info("Test info message", extra_field="extra_value")
        
        # Verify logger.info was called
        mock_logger.info.assert_called_once()
        
        # Parse the logged message
        logged_message = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_message)
        
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test info message"
        assert parsed["execution_id"] == "test_id"
        assert parsed["extra_field"] == "extra_value"
    
    @patch('AnchorAlpha.utils.logging_utils.logging.getLogger')
    def test_error_logging(self, mock_get_logger):
        """Test error level logging."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Mock empty handlers list
        mock_get_logger.return_value = mock_logger
        
        logger = StructuredLogger("TestLogger", "test_id")
        test_exception = ValueError("Test error")
        logger.error("Test error message", exception=test_exception)
        
        # Verify logger.error was called
        mock_logger.error.assert_called_once()
        
        # Parse the logged message
        logged_message = mock_logger.error.call_args[0][0]
        parsed = json.loads(logged_message)
        
        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Test error message"
        assert parsed["execution_id"] == "test_id"
        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test error"
        
        # Verify error was added to metrics
        assert len(logger.metrics.errors) == 1
        assert "Test error message" in logger.metrics.errors
    
    @patch('AnchorAlpha.utils.logging_utils.logging.getLogger')
    def test_api_call_timer_success(self, mock_get_logger):
        """Test API call timer context manager for successful calls."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Mock empty handlers list
        mock_get_logger.return_value = mock_logger
        
        logger = StructuredLogger("TestLogger", "test_id")
        
        with logger.api_call_timer("FMP", "stock-screener"):
            time.sleep(0.1)  # Simulate API call
        
        # Verify start and completion messages were logged
        assert mock_logger.info.call_count == 2
        
        # Check metrics were updated
        assert logger.metrics.fmp_api_calls == 1
        assert logger.metrics.fmp_api_total_time > 0
    
    @patch('AnchorAlpha.utils.logging_utils.logging.getLogger')
    def test_api_call_timer_error(self, mock_get_logger):
        """Test API call timer context manager for failed calls."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Mock empty handlers list
        mock_get_logger.return_value = mock_logger
        
        logger = StructuredLogger("TestLogger", "test_id")
        
        with pytest.raises(ValueError):
            with logger.api_call_timer("Perplexity", "chat/completions"):
                raise ValueError("API call failed")
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        
        # Check error metrics were updated
        assert logger.metrics.perplexity_api_errors == 1
    
    def test_log_processing_metrics(self):
        """Test logging processing metrics."""
        self.logger.log_processing_metrics(
            "test_phase",
            stocks_fetched=100,
            stocks_processed=95
        )
        
        assert self.logger.metrics.stocks_fetched == 100
        assert self.logger.metrics.stocks_processed == 95
    
    def test_log_s3_operation(self):
        """Test logging S3 operations."""
        # Test successful upload
        self.logger.log_s3_operation(
            "upload",
            "test-bucket",
            "test-key",
            True,
            file_size=1024
        )
        
        assert self.logger.metrics.s3_uploads == 1
        assert self.logger.metrics.s3_upload_errors == 0
        
        # Test failed upload
        self.logger.log_s3_operation(
            "upload",
            "test-bucket",
            "test-key-2",
            False,
            error="Upload failed"
        )
        
        assert self.logger.metrics.s3_uploads == 1  # Still 1
        assert self.logger.metrics.s3_upload_errors == 1
    
    def test_finalize_and_log_metrics(self):
        """Test finalizing and logging metrics."""
        # Add some test data
        self.logger.metrics.stocks_fetched = 100
        self.logger.metrics.add_error("Test error")
        
        with patch.object(self.logger.logger, 'info') as mock_info:
            self.logger.finalize_and_log_metrics()
        
        # Verify metrics were finalized
        assert self.logger.metrics.end_time is not None
        assert self.logger.metrics.duration_seconds is not None
        assert self.logger.metrics.success is False  # Due to error
        
        # Verify final log was written
        mock_info.assert_called_once()


class TestCloudWatchMetricsPublisher:
    """Test CloudWatch metrics publishing."""
    
    @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'})
    def setup_method(self):
        """Set up test fixtures."""
        with patch('boto3.client'):
            self.publisher = CloudWatchMetricsPublisher("TestNamespace")
    
    @patch('boto3.client')
    def test_publish_execution_metrics(self, mock_boto_client):
        """Test publishing execution metrics to CloudWatch."""
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        # Create test metrics
        metrics = ExecutionMetrics("test_id", "2026-03-01T12:00:00Z")
        metrics.duration_seconds = 120.5
        metrics.success = True
        metrics.fmp_api_calls = 10
        metrics.fmp_api_total_time = 5.0
        metrics.stocks_fetched = 100
        metrics.stocks_processed = 95
        
        self.publisher.publish_execution_metrics(metrics)
        
        # Verify CloudWatch put_metric_data was called
        mock_cloudwatch.put_metric_data.assert_called()
        
        # Check the metrics data
        call_args = mock_cloudwatch.put_metric_data.call_args
        assert call_args[1]['Namespace'] == 'TestNamespace'
        
        metric_data = call_args[1]['MetricData']
        assert len(metric_data) > 0
        
        # Verify specific metrics are present
        metric_names = [metric['MetricName'] for metric in metric_data]
        assert 'ExecutionDuration' in metric_names
        assert 'ExecutionSuccess' in metric_names
        assert 'FMPAPICalls' in metric_names
        assert 'StocksFetched' in metric_names
    
    @patch('boto3.client')
    def test_publish_api_rate_limit_metrics(self, mock_boto_client):
        """Test publishing API rate limit metrics."""
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        self.publisher.publish_api_rate_limit_metrics("FMP", 250, 300)
        
        # Verify metrics were published
        mock_cloudwatch.put_metric_data.assert_called_once()
        
        call_args = mock_cloudwatch.put_metric_data.call_args
        metric_data = call_args[1]['MetricData']
        
        # Check utilization percentage calculation
        utilization_metric = next(
            m for m in metric_data if m['MetricName'] == 'APIRateLimitUtilization'
        )
        expected_utilization = (250 / 300) * 100
        assert utilization_metric['Value'] == expected_utilization
    
    @patch('boto3.client')
    def test_publish_metrics_error_handling(self, mock_boto_client):
        """Test error handling in metrics publishing."""
        mock_cloudwatch = Mock()
        mock_cloudwatch.put_metric_data.side_effect = Exception("CloudWatch error")
        mock_boto_client.return_value = mock_cloudwatch
        
        metrics = ExecutionMetrics("test_id", "2026-03-01T12:00:00Z")
        
        # Should not raise exception, but handle gracefully
        self.publisher.publish_execution_metrics(metrics)


class TestSNSNotificationManager:
    """Test SNS notification functionality."""
    
    @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'})
    def setup_method(self):
        """Set up test fixtures."""
        self.topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
        with patch('boto3.client'):
            self.manager = SNSNotificationManager(self.topic_arn)
    
    @patch('boto3.client')
    def test_send_critical_error_notification(self, mock_boto_client):
        """Test sending critical error notifications."""
        mock_sns = Mock()
        mock_boto_client.return_value = mock_sns
        
        # Create test metrics with errors
        metrics = ExecutionMetrics("test_execution", "2026-03-01T12:00:00Z")
        metrics.duration_seconds = 300.0
        metrics.stocks_fetched = 100
        metrics.add_error("Critical error occurred")
        metrics.add_error("Another error")
        
        self.manager.send_critical_error_notification(
            "Test critical error",
            "test_execution",
            metrics
        )
        
        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()
        
        call_args = mock_sns.publish.call_args
        assert call_args[1]['TopicArn'] == self.topic_arn
        assert 'AnchorAlpha Critical Error' in call_args[1]['Subject']
        
        message = call_args[1]['Message']
        assert 'test_execution' in message
        assert 'Test critical error' in message
        assert 'Duration: 300.00 seconds' in message
        assert 'Stocks Fetched: 100' in message
    
    @patch('boto3.client')
    def test_send_budget_alert(self, mock_boto_client):
        """Test sending budget alert notifications."""
        mock_sns = Mock()
        mock_boto_client.return_value = mock_sns
        
        self.manager.send_budget_alert(8.50, 10.00)
        
        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()
        
        call_args = mock_sns.publish.call_args
        assert call_args[1]['TopicArn'] == self.topic_arn
        assert 'Budget Alert' in call_args[1]['Subject']
        
        message = call_args[1]['Message']
        assert '$8.50' in message
        assert '$10.00' in message
        assert '85.0%' in message  # Utilization percentage
    
    def test_no_sns_configuration(self):
        """Test behavior when SNS is not configured."""
        manager = SNSNotificationManager(None)
        
        # Should not raise exception
        manager.send_critical_error_notification(
            "Test error",
            "test_id",
            ExecutionMetrics("test_id", "2026-03-01T12:00:00Z")
        )
        
        manager.send_budget_alert(5.0, 10.0)
    
    @patch('boto3.client')
    def test_sns_error_handling(self, mock_boto_client):
        """Test error handling in SNS operations."""
        mock_sns = Mock()
        mock_sns.publish.side_effect = Exception("SNS error")
        mock_boto_client.return_value = mock_sns
        
        metrics = ExecutionMetrics("test_id", "2026-03-01T12:00:00Z")
        
        # Should not raise exception, but handle gracefully
        self.manager.send_critical_error_notification(
            "Test error",
            "test_id",
            metrics
        )


class TestGetLogger:
    """Test the get_logger utility function."""
    
    def test_get_logger_with_execution_id(self):
        """Test getting logger with execution ID."""
        logger = get_logger("TestLogger", "test_execution_123")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.execution_id == "test_execution_123"
        assert logger.logger.name == "TestLogger"
    
    def test_get_logger_without_execution_id(self):
        """Test getting logger without execution ID."""
        logger = get_logger("TestLogger")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.execution_id is not None
        assert len(logger.execution_id) > 0
        assert logger.logger.name == "TestLogger"


class TestIntegration:
    """Integration tests for logging system."""
    
    @patch('boto3.client')
    def test_complete_logging_workflow(self, mock_boto_client):
        """Test complete logging workflow with all components."""
        # Mock AWS clients
        mock_cloudwatch = Mock()
        mock_sns = Mock()
        mock_boto_client.side_effect = lambda service: {
            'cloudwatch': mock_cloudwatch,
            'sns': mock_sns
        }[service]
        
        # Create logger and related components
        logger = StructuredLogger("IntegrationTest", "integration_test_123")
        metrics_publisher = CloudWatchMetricsPublisher()
        notification_manager = SNSNotificationManager("test-topic-arn")
        
        # Simulate a complete execution
        logger.info("Starting test execution")
        
        # Simulate API calls
        with logger.api_call_timer("FMP", "stock-screener"):
            time.sleep(0.1)
        
        with logger.api_call_timer("Perplexity", "chat/completions"):
            time.sleep(0.05)
        
        # Log processing metrics
        logger.log_processing_metrics("data_fetch", stocks_fetched=100)
        logger.log_processing_metrics("momentum_calc", stocks_processed=95)
        
        # Log S3 operations
        logger.log_s3_operation("upload", "test-bucket", "test-key", True)
        
        # Add a warning
        logger.warning("Test warning message")
        
        # Finalize metrics
        logger.finalize_and_log_metrics()
        
        # Publish metrics
        metrics = logger.get_metrics()
        metrics_publisher.publish_execution_metrics(metrics)
        
        # Verify metrics were collected correctly
        assert metrics.fmp_api_calls == 1
        assert metrics.perplexity_api_calls == 1
        assert metrics.stocks_fetched == 100
        assert metrics.stocks_processed == 95
        assert metrics.s3_uploads == 1
        assert len(metrics.warnings) == 1
        assert metrics.success is True  # No errors
        
        # Verify CloudWatch metrics were published
        mock_cloudwatch.put_metric_data.assert_called()
        
        # Test error notification
        metrics.add_error("Critical test error")
        notification_manager.send_critical_error_notification(
            "Integration test error",
            "integration_test_123",
            metrics
        )
        
        # Verify SNS notification was sent
        mock_sns.publish.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])