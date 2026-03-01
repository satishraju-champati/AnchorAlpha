"""
Integration tests for AWS Lambda handler function.

These tests verify the complete Lambda execution flow including:
- API client initialization
- Data fetching and processing
- Error handling and recovery
- Structured logging
- S3 storage integration

Requirements: 5.2, 6.1, 8.1, 8.3
"""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

from AnchorAlpha.lambda_function.handler import LambdaOrchestrator, lambda_handler
from AnchorAlpha.models import Stock
from AnchorAlpha.momentum_engine import HistoricalPriceData


class TestLambdaOrchestrator:
    """Test cases for the LambdaOrchestrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = LambdaOrchestrator()
    
    def test_orchestrator_initialization(self):
        """Test that orchestrator initializes correctly."""
        assert self.orchestrator.execution_id is not None
        assert self.orchestrator.market_date == date.today().strftime("%Y-%m-%d")
        assert self.orchestrator.momentum_engine is not None
        assert self.orchestrator.data_pipeline is not None
        assert "execution_id" in self.orchestrator.metrics
        assert "start_time" in self.orchestrator.metrics
        assert self.orchestrator.metrics["stocks_fetched"] == 0
        assert self.orchestrator.metrics["stocks_processed"] == 0
        assert self.orchestrator.metrics["summaries_generated"] == 0
        assert self.orchestrator.metrics["errors"] == []
        assert self.orchestrator.metrics["warnings"] == []
    
    @patch.dict(os.environ, {"FMP_API_KEY": "test_fmp_key", "PERPLEXITY_API_KEY": "test_perp_key"})
    @patch("AnchorAlpha.lambda_function.handler.FMPClient")
    @patch("AnchorAlpha.lambda_function.handler.PerplexityFactory")
    def test_initialize_clients_success(self, mock_perp_factory, mock_fmp_client):
        """Test successful API client initialization."""
        # Setup mocks
        mock_fmp_client.return_value = Mock()
        mock_perp_factory.create_client.return_value = Mock()
        
        # Test initialization
        result = self.orchestrator._initialize_clients()
        
        assert result is True
        assert self.orchestrator.fmp_client is not None
        assert self.orchestrator.perplexity_client is not None
        mock_fmp_client.assert_called_once_with("test_fmp_key")
        mock_perp_factory.create_client.assert_called_once_with(
            api_key="test_perp_key", 
            use_mock=False
        )
    
    @patch.dict(os.environ, {}, clear=True)
    def test_initialize_clients_missing_fmp_key(self):
        """Test client initialization with missing FMP API key."""
        result = self.orchestrator._initialize_clients()
        
        assert result is False
        assert len(self.orchestrator.metrics["errors"]) == 1
        assert "FMP_API_KEY environment variable is required" in self.orchestrator.metrics["errors"][0]
    
    @patch.dict(os.environ, {"FMP_API_KEY": "test_fmp_key"})
    @patch("AnchorAlpha.lambda_function.handler.FMPClient")
    @patch("AnchorAlpha.lambda_function.handler.PerplexityFactory")
    def test_initialize_clients_missing_perplexity_key(self, mock_perp_factory, mock_fmp_client):
        """Test client initialization with missing Perplexity API key (should use mock)."""
        # Setup mocks
        mock_fmp_client.return_value = Mock()
        mock_perp_factory.create_client.return_value = Mock()
        
        # Test initialization
        result = self.orchestrator._initialize_clients()
        
        assert result is True
        mock_perp_factory.create_client.assert_called_once_with(use_mock=True)
    
    def test_fetch_stock_data_success(self):
        """Test successful stock data fetching."""
        # Setup mock FMP client
        mock_fmp_client = Mock()
        mock_screener_data = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "price": 150.0,
                "marketCap": 2500000000000
            },
            {
                "symbol": "MSFT",
                "companyName": "Microsoft Corporation",
                "price": 300.0,
                "marketCap": 2200000000000
            }
        ]
        
        mock_stock_objects = [
            Stock("AAPL", "Apple Inc.", 150.0, 2500000000000),
            Stock("MSFT", "Microsoft Corporation", 300.0, 2200000000000)
        ]
        
        mock_fmp_client.get_large_cap_stocks.return_value = mock_screener_data
        mock_fmp_client.create_stock_from_screener_data.side_effect = mock_stock_objects
        
        self.orchestrator.fmp_client = mock_fmp_client
        
        # Test stock fetching
        result = self.orchestrator._fetch_stock_data()
        
        assert len(result) == 2
        assert result[0].ticker == "AAPL"
        assert result[1].ticker == "MSFT"
        assert self.orchestrator.metrics["stocks_fetched"] == 2
        mock_fmp_client.get_large_cap_stocks.assert_called_once()
    
    def test_fetch_stock_data_fmp_error(self):
        """Test stock data fetching with FMP API error."""
        from AnchorAlpha.api.fmp_client import FMPAPIError
        
        # Setup mock FMP client that raises error
        mock_fmp_client = Mock()
        mock_fmp_client.get_large_cap_stocks.side_effect = FMPAPIError("API rate limit exceeded")
        
        self.orchestrator.fmp_client = mock_fmp_client
        
        # Test that error is properly handled
        with pytest.raises(FMPAPIError):
            self.orchestrator._fetch_stock_data()
        
        assert len(self.orchestrator.metrics["errors"]) == 1
        assert "FMP API error" in self.orchestrator.metrics["errors"][0]
    
    def test_fetch_historical_data_batch(self):
        """Test historical data fetching for multiple stocks."""
        # Setup test stocks
        stocks = [
            Stock("AAPL", "Apple Inc.", 150.0, 2500000000000),
            Stock("MSFT", "Microsoft Corporation", 300.0, 2200000000000)
        ]
        
        # Setup mock FMP client with simple, predictable historical data
        mock_fmp_client = Mock()
        # Create 100 days of historical data with predictable prices
        historical_prices = []
        for i in range(100):
            date_str = f"2026-{3 - (i // 30):02d}-{(30 - (i % 30)):02d}"
            if i < 30:
                date_str = f"2026-03-{30-i:02d}"
            elif i < 60:
                date_str = f"2026-02-{60-i:02d}"
            else:
                date_str = f"2026-01-{90-i:02d}"
            
            # Set specific prices for key days
            if i == 0:
                price = 150.0  # Current price
            elif i == 7:
                price = 145.0  # 7 days ago
            elif i == 30:
                price = 140.0  # 30 days ago
            elif i == 60:
                price = 135.0  # 60 days ago
            elif i == 90:
                price = 130.0  # 90 days ago
            else:
                price = 150.0 - i * 0.2  # Gradual decline
            
            historical_prices.append({"date": date_str, "close": price})
        
        mock_historical_data = {"historical": historical_prices}
        
        mock_fmp_client.get_historical_prices.return_value = mock_historical_data
        self.orchestrator.fmp_client = mock_fmp_client
        
        # Test historical data fetching
        result = self.orchestrator._fetch_historical_data_batch(stocks)
        
        assert len(result) == 2
        assert "AAPL" in result
        assert "MSFT" in result
        
        # Verify historical data structure
        aapl_data = result["AAPL"]
        assert aapl_data.ticker == "AAPL"
        assert aapl_data.current_price == 150.0
        assert aapl_data.prices_7d_ago == 145.0
        assert aapl_data.prices_30d_ago == 140.0
        assert aapl_data.prices_60d_ago == 135.0
        assert aapl_data.prices_90d_ago == 130.0
    
    def test_calculate_momentum_for_stocks(self):
        """Test momentum calculation for stocks."""
        # Setup test stocks
        stocks = [
            Stock("AAPL", "Apple Inc.", 150.0, 2500000000000),
            Stock("MSFT", "Microsoft Corporation", 300.0, 2200000000000)
        ]
        
        # Setup historical data
        historical_data = {
            "AAPL": HistoricalPriceData(
                ticker="AAPL",
                current_price=150.0,
                prices_7d_ago=145.0,
                prices_30d_ago=140.0,
                prices_60d_ago=135.0,
                prices_90d_ago=130.0
            ),
            "MSFT": HistoricalPriceData(
                ticker="MSFT",
                current_price=300.0,
                prices_7d_ago=290.0,
                prices_30d_ago=280.0,
                prices_60d_ago=270.0,
                prices_90d_ago=260.0
            )
        }
        
        # Test momentum calculation
        result = self.orchestrator._calculate_momentum_for_stocks(stocks, historical_data)
        
        assert len(result) == 2
        assert self.orchestrator.metrics["stocks_processed"] == 2
        
        # Verify momentum calculations
        aapl_stock = next(s for s in result if s.ticker == "AAPL")
        assert aapl_stock.momentum_7d is not None
        assert aapl_stock.momentum_30d is not None
        assert aapl_stock.momentum_60d is not None
        assert aapl_stock.momentum_90d is not None
        
        # Check specific momentum values
        expected_7d_momentum = (150.0 / 145.0) - 1  # ~3.45%
        assert abs(aapl_stock.momentum_7d - expected_7d_momentum) < 0.001
    
    def test_generate_ai_summaries(self):
        """Test AI summary generation for top performers."""
        # Setup test tier rankings
        test_stocks = [
            Stock("AAPL", "Apple Inc.", 150.0, 2500000000000, momentum_7d=0.05, momentum_30d=0.10),
            Stock("MSFT", "Microsoft Corporation", 300.0, 2200000000000, momentum_7d=0.03, momentum_30d=0.08)
        ]
        
        tier_rankings = {
            "1T_plus": {
                7: test_stocks,
                30: test_stocks,
                60: [],
                90: []
            },
            "500B_1T": {7: [], 30: [], 60: [], 90: []},
            "200B_500B": {7: [], 30: [], 60: [], 90: []},
            "100B_200B": {7: [], 30: [], 60: [], 90: []}
        }
        
        # Setup mock Perplexity client
        mock_perplexity_client = Mock()
        mock_summaries = {
            "AAPL": "Apple shares rose on strong iPhone sales and positive earnings guidance.",
            "MSFT": "Microsoft gained on cloud growth and AI product announcements."
        }
        mock_perplexity_client.generate_batch_summaries.return_value = mock_summaries
        
        self.orchestrator.perplexity_client = mock_perplexity_client
        
        # Test AI summary generation
        result = self.orchestrator._generate_ai_summaries(tier_rankings)
        
        assert self.orchestrator.metrics["summaries_generated"] == 2
        
        # Verify summaries were applied to stocks
        for stock in result["1T_plus"][7]:
            assert stock.ai_summary is not None
            assert stock.ai_summary in mock_summaries.values()
    
    def test_generate_ai_summaries_with_perplexity_error(self):
        """Test AI summary generation with Perplexity API error."""
        from AnchorAlpha.api.perplexity_client import PerplexityAPIError
        
        # Setup test tier rankings
        test_stocks = [Stock("AAPL", "Apple Inc.", 150.0, 2500000000000, momentum_7d=0.05)]
        tier_rankings = {
            "1T_plus": {7: test_stocks, 30: [], 60: [], 90: []},
            "500B_1T": {7: [], 30: [], 60: [], 90: []},
            "200B_500B": {7: [], 30: [], 60: [], 90: []},
            "100B_200B": {7: [], 30: [], 60: [], 90: []}
        }
        
        # Setup mock Perplexity client that raises error
        mock_perplexity_client = Mock()
        mock_perplexity_client.generate_batch_summaries.side_effect = PerplexityAPIError("API quota exceeded")
        
        self.orchestrator.perplexity_client = mock_perplexity_client
        
        # Test that error is handled gracefully
        result = self.orchestrator._generate_ai_summaries(tier_rankings)
        
        assert len(self.orchestrator.metrics["warnings"]) == 1
        assert "Perplexity API error" in self.orchestrator.metrics["warnings"][0]
        assert result == tier_rankings  # Should return original rankings
    
    def test_store_results_success(self):
        """Test successful S3 storage of results."""
        # Setup test stocks
        test_stocks = [
            Stock("AAPL", "Apple Inc.", 150.0, 2500000000000, momentum_7d=0.05),
            Stock("MSFT", "Microsoft Corporation", 300.0, 2200000000000, momentum_7d=0.03)
        ]
        
        # Setup mock data pipeline
        mock_data_pipeline = Mock()
        mock_data_pipeline.process_and_store_momentum_data.return_value = True
        
        self.orchestrator.data_pipeline = mock_data_pipeline
        
        # Test S3 storage
        result = self.orchestrator._store_results(test_stocks)
        
        assert result is True
        mock_data_pipeline.process_and_store_momentum_data.assert_called_once_with(
            test_stocks, 
            self.orchestrator.market_date
        )
    
    def test_store_results_failure(self):
        """Test S3 storage failure handling."""
        # Setup test stocks
        test_stocks = [Stock("AAPL", "Apple Inc.", 150.0, 2500000000000)]
        
        # Setup mock data pipeline that fails
        mock_data_pipeline = Mock()
        mock_data_pipeline.process_and_store_momentum_data.return_value = False
        
        self.orchestrator.data_pipeline = mock_data_pipeline
        
        # Test S3 storage failure
        result = self.orchestrator._store_results(test_stocks)
        
        assert result is False
        assert len(self.orchestrator.metrics["errors"]) == 1
        assert "S3 data storage failed" in self.orchestrator.metrics["errors"][0]


class TestLambdaHandler:
    """Test cases for the main lambda_handler function."""
    
    def test_lambda_handler_success(self):
        """Test successful Lambda handler execution."""
        # Setup test event and context
        test_event = {"source": "aws.events", "detail-type": "Scheduled Event"}
        mock_context = Mock()
        mock_context.function_name = "anchoralpha-momentum-screener"
        mock_context.function_version = "1"
        mock_context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        mock_context.memory_limit_in_mb = 512
        mock_context.get_remaining_time_in_millis.return_value = 300000
        
        # Mock the orchestrator execution
        with patch("AnchorAlpha.lambda_function.handler.LambdaOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_pipeline.return_value = {
                "statusCode": 200,
                "body": json.dumps({"message": "Pipeline execution completed", "success": True})
            }
            mock_orchestrator_class.return_value = mock_orchestrator
            
            # Test Lambda handler
            result = lambda_handler(test_event, mock_context)
            
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["success"] is True
            mock_orchestrator.execute_pipeline.assert_called_once()
    
    def test_lambda_handler_failure(self):
        """Test Lambda handler with execution failure."""
        # Setup test event and context
        test_event = {"source": "aws.events"}
        mock_context = Mock()
        mock_context.function_name = "anchoralpha-momentum-screener"
        mock_context.function_version = "1"
        mock_context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        mock_context.memory_limit_in_mb = 512
        mock_context.get_remaining_time_in_millis.return_value = 300000
        
        # Mock the orchestrator to raise an exception
        with patch("AnchorAlpha.lambda_function.handler.LambdaOrchestrator") as mock_orchestrator_class:
            mock_orchestrator_class.side_effect = Exception("Test pipeline failure")
            
            # Test Lambda handler
            result = lambda_handler(test_event, mock_context)
            
            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "Lambda function failed" in body["message"]
            assert "Test pipeline failure" in body["error"]
    
    @patch.dict(os.environ, {"FMP_API_KEY": "test_key", "PERPLEXITY_API_KEY": "test_key"})
    @patch("AnchorAlpha.lambda_function.handler.FMPClient")
    @patch("AnchorAlpha.lambda_function.handler.PerplexityFactory")
    @patch("AnchorAlpha.lambda_function.handler.MomentumDataPipeline")
    def test_full_pipeline_integration(self, mock_pipeline_class, mock_perp_factory, mock_fmp_client_class):
        """Test full pipeline integration with mocked external dependencies."""
        # Setup comprehensive mocks
        mock_fmp_client = Mock()
        mock_fmp_client.get_large_cap_stocks.return_value = [
            {"symbol": "AAPL", "companyName": "Apple Inc.", "price": 150.0, "marketCap": 2500000000000}
        ]
        mock_fmp_client.create_stock_from_screener_data.return_value = Stock(
            "AAPL", "Apple Inc.", 150.0, 2500000000000
        )
        mock_fmp_client.get_historical_prices.return_value = {
            "historical": [
                {"date": "2026-03-01", "close": 150.0},
                {"date": "2026-02-22", "close": 145.0},
                {"date": "2026-02-01", "close": 140.0},
                {"date": "2026-01-01", "close": 135.0},
                {"date": "2025-12-01", "close": 130.0},
            ] + [{"date": f"2025-11-{i:02d}", "close": 125.0} for i in range(1, 31)]
        }
        mock_fmp_client_class.return_value = mock_fmp_client
        
        mock_perplexity_client = Mock()
        mock_perplexity_client.generate_batch_summaries.return_value = {
            "AAPL": "Apple shares rose on strong earnings."
        }
        mock_perp_factory.create_client.return_value = mock_perplexity_client
        
        mock_data_pipeline = Mock()
        mock_data_pipeline.process_and_store_momentum_data.return_value = True
        mock_pipeline_class.return_value = mock_data_pipeline
        
        # Test full pipeline execution
        orchestrator = LambdaOrchestrator()
        result = orchestrator.execute_pipeline()
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True
        assert orchestrator.metrics["stocks_fetched"] > 0
        assert orchestrator.metrics["stocks_processed"] > 0
        
        # Verify all components were called
        mock_fmp_client.get_large_cap_stocks.assert_called_once()
        mock_fmp_client.get_historical_prices.assert_called()
        mock_perplexity_client.generate_batch_summaries.assert_called()
        mock_data_pipeline.process_and_store_momentum_data.assert_called_once()


class TestStructuredLogging:
    """Test cases for structured logging functionality."""
    
    def test_structured_logging_format(self):
        """Test that structured logging produces valid JSON."""
        orchestrator = LambdaOrchestrator()
        
        # Capture log output
        with patch("AnchorAlpha.lambda_function.handler.logger") as mock_logger:
            orchestrator._log_structured("info", "Test message", test_field="test_value")
            
            # Verify logger was called
            mock_logger.handle.assert_called_once()
            
            # Get the log record
            log_record = mock_logger.handle.call_args[0][0]
            assert hasattr(log_record, 'extra_fields')
            assert log_record.extra_fields["execution_id"] == orchestrator.execution_id
            assert log_record.extra_fields["test_field"] == "test_value"
    
    def test_metrics_tracking(self):
        """Test that metrics are properly tracked throughout execution."""
        orchestrator = LambdaOrchestrator()
        
        # Verify initial metrics
        assert orchestrator.metrics["stocks_fetched"] == 0
        assert orchestrator.metrics["stocks_processed"] == 0
        assert orchestrator.metrics["summaries_generated"] == 0
        assert orchestrator.metrics["errors"] == []
        assert orchestrator.metrics["warnings"] == []
        
        # Simulate metric updates
        orchestrator.metrics["stocks_fetched"] = 100
        orchestrator.metrics["stocks_processed"] = 95
        orchestrator.metrics["summaries_generated"] = 20
        orchestrator.metrics["errors"].append("Test error")
        orchestrator.metrics["warnings"].append("Test warning")
        
        # Verify metrics are updated
        assert orchestrator.metrics["stocks_fetched"] == 100
        assert orchestrator.metrics["stocks_processed"] == 95
        assert orchestrator.metrics["summaries_generated"] == 20
        assert len(orchestrator.metrics["errors"]) == 1
        assert len(orchestrator.metrics["warnings"]) == 1


if __name__ == "__main__":
    pytest.main([__file__])