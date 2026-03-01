"""
Unit tests for the momentum data pipeline.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date

from AnchorAlpha.storage.data_pipeline import MomentumDataPipeline
from AnchorAlpha.storage.s3_client import S3DataStorage
from AnchorAlpha.models import Stock


class TestMomentumDataPipeline:
    """Test cases for MomentumDataPipeline class."""
    
    @pytest.fixture
    def mock_s3_storage(self):
        """Mock S3DataStorage for testing."""
        return Mock(spec=S3DataStorage)
    
    @pytest.fixture
    def pipeline(self, mock_s3_storage):
        """MomentumDataPipeline instance with mocked S3 storage."""
        return MomentumDataPipeline(s3_storage=mock_s3_storage)
    
    @pytest.fixture
    def sample_stocks(self):
        """Sample stock data for testing."""
        return [
            Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.25,
                market_cap=2400000000000,  # $2.4T - 1T_plus tier
                momentum_7d=0.0523,
                momentum_30d=0.1245,
                momentum_60d=0.0876,
                momentum_90d=0.1567
            ),
            Stock(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                current_price=300.50,
                market_cap=2200000000000,  # $2.2T - 1T_plus tier
                momentum_7d=0.0312,
                momentum_30d=0.0987,
                momentum_60d=0.1234,
                momentum_90d=0.0876
            ),
            Stock(
                ticker="GOOGL",
                company_name="Alphabet Inc.",
                current_price=120.75,
                market_cap=1500000000000,  # $1.5T - 1T_plus tier
                momentum_7d=0.0234,
                momentum_30d=0.0654,
                momentum_60d=0.0987,
                momentum_90d=0.1123
            ),
            Stock(
                ticker="TSLA",
                company_name="Tesla Inc.",
                current_price=200.00,
                market_cap=600000000000,  # $600B - 500B_1T tier
                momentum_7d=0.0876,
                momentum_30d=0.1543,
                momentum_60d=0.0432,
                momentum_90d=0.0765
            ),
            Stock(
                ticker="NVDA",
                company_name="NVIDIA Corporation",
                current_price=450.00,
                market_cap=1100000000000,  # $1.1T - 1T_plus tier
                momentum_7d=0.1234,  # Highest 7-day momentum
                momentum_30d=0.0876,
                momentum_60d=0.1567,
                momentum_90d=0.0543
            )
        ]
    
    def test_init_with_s3_storage(self, mock_s3_storage):
        """Test initialization with provided S3 storage."""
        pipeline = MomentumDataPipeline(s3_storage=mock_s3_storage)
        
        assert pipeline.s3_storage == mock_s3_storage
        assert pipeline.momentum_engine is not None
    
    @patch('AnchorAlpha.storage.data_pipeline.S3DataStorage')
    def test_init_without_s3_storage(self, mock_s3_class):
        """Test initialization without provided S3 storage."""
        mock_s3_instance = Mock()
        mock_s3_class.return_value = mock_s3_instance
        
        pipeline = MomentumDataPipeline()
        
        assert pipeline.s3_storage == mock_s3_instance
        mock_s3_class.assert_called_once()
    
    def test_organize_stocks_by_tier_and_timeframe(self, pipeline, sample_stocks):
        """Test stock organization by tier and timeframe."""
        organized_data = pipeline._organize_stocks_by_tier_and_timeframe(sample_stocks)
        
        # Check structure
        assert "1T_plus" in organized_data
        assert "500B_1T" in organized_data
        assert "200B_500B" in organized_data
        assert "100B_200B" in organized_data
        
        # Check timeframes
        for tier in organized_data.values():
            assert "7" in tier
            assert "30" in tier
            assert "60" in tier
            assert "90" in tier
        
        # Check 1T_plus tier has 4 stocks (AAPL, MSFT, GOOGL, NVDA)
        assert len(organized_data["1T_plus"]["7"]) == 4
        
        # Check 500B_1T tier has 1 stock (TSLA)
        assert len(organized_data["500B_1T"]["7"]) == 1
        assert organized_data["500B_1T"]["7"][0].ticker == "TSLA"
        
        # Check sorting by momentum (NVDA should be first in 7-day for 1T_plus)
        top_7d_1t = organized_data["1T_plus"]["7"]
        assert top_7d_1t[0].ticker == "NVDA"  # Highest 7-day momentum (0.1234)
        assert top_7d_1t[1].ticker == "AAPL"  # Second highest (0.0523)
    
    def test_organize_stocks_filters_missing_momentum(self, pipeline):
        """Test that stocks without momentum data for a timeframe are filtered out."""
        stocks_with_missing_data = [
            Stock(
                ticker="TEST1",
                company_name="Test Company 1",
                current_price=100.0,
                market_cap=1500000000000,
                momentum_7d=0.05,
                momentum_30d=None,  # Missing 30-day data
                momentum_60d=0.03,
                momentum_90d=0.02
            ),
            Stock(
                ticker="TEST2",
                company_name="Test Company 2",
                current_price=200.0,
                market_cap=1200000000000,
                momentum_7d=0.04,
                momentum_30d=0.06,
                momentum_60d=None,  # Missing 60-day data
                momentum_90d=0.01
            )
        ]
        
        organized_data = pipeline._organize_stocks_by_tier_and_timeframe(stocks_with_missing_data)
        
        # Both stocks should appear in 7-day (both have data)
        assert len(organized_data["1T_plus"]["7"]) == 2
        
        # Only TEST2 should appear in 30-day (TEST1 missing data)
        assert len(organized_data["1T_plus"]["30"]) == 1
        assert organized_data["1T_plus"]["30"][0].ticker == "TEST2"
        
        # Only TEST1 should appear in 60-day (TEST2 missing data)
        assert len(organized_data["1T_plus"]["60"]) == 1
        assert organized_data["1T_plus"]["60"][0].ticker == "TEST1"
    
    def test_process_and_store_momentum_data_success(self, pipeline, mock_s3_storage, sample_stocks):
        """Test successful momentum data processing and storage."""
        mock_s3_storage.upload_momentum_data.return_value = True
        
        result = pipeline.process_and_store_momentum_data(sample_stocks, "2026-02-21")
        
        assert result is True
        mock_s3_storage.upload_momentum_data.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_s3_storage.upload_momentum_data.call_args
        organized_data, market_date = call_args[0]
        
        assert market_date == "2026-02-21"
        assert "1T_plus" in organized_data
        assert "500B_1T" in organized_data
    
    def test_process_and_store_momentum_data_failure(self, pipeline, mock_s3_storage, sample_stocks):
        """Test momentum data processing when S3 upload fails."""
        mock_s3_storage.upload_momentum_data.return_value = False
        
        result = pipeline.process_and_store_momentum_data(sample_stocks, "2026-02-21")
        
        assert result is False
    
    @patch('AnchorAlpha.storage.data_pipeline.date')
    def test_process_and_store_momentum_data_default_date(self, mock_date, pipeline, mock_s3_storage, sample_stocks):
        """Test momentum data processing with default date."""
        mock_date.today.return_value.strftime.return_value = "2026-02-22"
        mock_s3_storage.upload_momentum_data.return_value = True
        
        result = pipeline.process_and_store_momentum_data(sample_stocks)
        
        assert result is True
        call_args = mock_s3_storage.upload_momentum_data.call_args
        _, market_date = call_args[0]
        assert market_date == "2026-02-22"
    
    def test_process_and_store_momentum_data_exception(self, pipeline, mock_s3_storage, sample_stocks):
        """Test momentum data processing when an exception occurs."""
        mock_s3_storage.upload_momentum_data.side_effect = Exception("S3 error")
        
        result = pipeline.process_and_store_momentum_data(sample_stocks, "2026-02-21")
        
        assert result is False
    
    def test_retrieve_momentum_data_success(self, pipeline, mock_s3_storage):
        """Test successful momentum data retrieval."""
        expected_data = {"market_date": "2026-02-21", "tiers": {}}
        mock_s3_storage.download_momentum_data.return_value = expected_data
        
        result = pipeline.retrieve_momentum_data("2026-02-21")
        
        assert result == expected_data
        mock_s3_storage.download_momentum_data.assert_called_once_with("2026-02-21")
    
    def test_retrieve_momentum_data_not_found(self, pipeline, mock_s3_storage):
        """Test momentum data retrieval when data doesn't exist."""
        mock_s3_storage.download_momentum_data.return_value = None
        
        result = pipeline.retrieve_momentum_data("2026-02-21")
        
        assert result is None
    
    def test_retrieve_momentum_data_exception(self, pipeline, mock_s3_storage):
        """Test momentum data retrieval when an exception occurs."""
        mock_s3_storage.download_momentum_data.side_effect = Exception("S3 error")
        
        result = pipeline.retrieve_momentum_data("2026-02-21")
        
        assert result is None
    
    def test_get_available_data_dates_success(self, pipeline, mock_s3_storage):
        """Test successful retrieval of available data dates."""
        expected_dates = ["2026-02-21", "2026-02-20", "2026-02-19"]
        mock_s3_storage.list_available_dates.return_value = expected_dates
        
        result = pipeline.get_available_data_dates()
        
        assert result == expected_dates
        mock_s3_storage.list_available_dates.assert_called_once_with(30)
    
    def test_get_available_data_dates_with_limit(self, pipeline, mock_s3_storage):
        """Test retrieval of available data dates with custom limit."""
        expected_dates = ["2026-02-21", "2026-02-20"]
        mock_s3_storage.list_available_dates.return_value = expected_dates
        
        result = pipeline.get_available_data_dates(limit=10)
        
        assert result == expected_dates
        mock_s3_storage.list_available_dates.assert_called_once_with(10)
    
    def test_get_available_data_dates_exception(self, pipeline, mock_s3_storage):
        """Test retrieval of available data dates when an exception occurs."""
        mock_s3_storage.list_available_dates.side_effect = Exception("S3 error")
        
        result = pipeline.get_available_data_dates()
        
        assert result == []
    
    def test_validate_stored_data_success(self, pipeline, mock_s3_storage):
        """Test successful data validation."""
        mock_data = {
            "market_date": "2026-02-21",
            "generated_at": "2026-02-21T16:30:00Z",
            "data_version": "1.0",
            "tiers": {}
        }
        mock_s3_storage.download_momentum_data.return_value = mock_data
        mock_s3_storage.validate_json_schema.return_value = True
        
        result = pipeline.validate_stored_data("2026-02-21")
        
        assert result is True
        mock_s3_storage.download_momentum_data.assert_called_once_with("2026-02-21")
        mock_s3_storage.validate_json_schema.assert_called_once_with(mock_data)
    
    def test_validate_stored_data_no_data(self, pipeline, mock_s3_storage):
        """Test data validation when no data exists."""
        mock_s3_storage.download_momentum_data.return_value = None
        
        result = pipeline.validate_stored_data("2026-02-21")
        
        assert result is False
    
    def test_validate_stored_data_invalid_schema(self, pipeline, mock_s3_storage):
        """Test data validation with invalid schema."""
        mock_data = {"invalid": "data"}
        mock_s3_storage.download_momentum_data.return_value = mock_data
        mock_s3_storage.validate_json_schema.return_value = False
        
        result = pipeline.validate_stored_data("2026-02-21")
        
        assert result is False
    
    def test_validate_stored_data_date_mismatch(self, pipeline, mock_s3_storage):
        """Test data validation with market date mismatch."""
        mock_data = {
            "market_date": "2026-02-20",  # Different from requested date
            "generated_at": "2026-02-21T16:30:00Z",
            "data_version": "1.0",
            "tiers": {}
        }
        mock_s3_storage.download_momentum_data.return_value = mock_data
        mock_s3_storage.validate_json_schema.return_value = True
        
        result = pipeline.validate_stored_data("2026-02-21")
        
        assert result is False
    
    def test_validate_stored_data_exception(self, pipeline, mock_s3_storage):
        """Test data validation when an exception occurs."""
        mock_s3_storage.download_momentum_data.side_effect = Exception("S3 error")
        
        result = pipeline.validate_stored_data("2026-02-21")
        
        assert result is False


class TestMomentumDataPipelineIntegration:
    """Integration tests for MomentumDataPipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Real MomentumDataPipeline instance for integration tests."""
        # Use a mock S3 storage to avoid actual AWS calls
        mock_s3 = Mock(spec=S3DataStorage)
        return MomentumDataPipeline(s3_storage=mock_s3)
    
    @pytest.fixture
    def large_stock_dataset(self):
        """Large dataset for testing top 20 selection."""
        stocks = []
        
        # Create 25 stocks in 1T_plus tier to test top 20 selection
        for i in range(25):
            stocks.append(Stock(
                ticker=f"STOCK{i:02d}",
                company_name=f"Company {i}",
                current_price=100.0 + i,
                market_cap=1000000000000 + (i * 100000000000),  # $1T+ tier
                momentum_7d=0.01 + (i * 0.001),  # Increasing momentum
                momentum_30d=0.02 + (i * 0.001),
                momentum_60d=0.03 + (i * 0.001),
                momentum_90d=0.04 + (i * 0.001)
            ))
        
        return stocks
    
    def test_top_20_selection_per_tier(self, pipeline, large_stock_dataset):
        """Test that only top 20 performers are selected per tier."""
        organized_data = pipeline._organize_stocks_by_tier_and_timeframe(large_stock_dataset)
        
        # Should have exactly 20 stocks in 1T_plus tier for each timeframe
        assert len(organized_data["1T_plus"]["7"]) == 20
        assert len(organized_data["1T_plus"]["30"]) == 20
        assert len(organized_data["1T_plus"]["60"]) == 20
        assert len(organized_data["1T_plus"]["90"]) == 20
        
        # Verify they are the top performers (highest momentum values)
        top_7d = organized_data["1T_plus"]["7"]
        
        # Should be sorted by momentum descending
        for i in range(len(top_7d) - 1):
            assert top_7d[i].momentum_7d >= top_7d[i + 1].momentum_7d
        
        # Top performer should be STOCK24 (highest momentum)
        assert top_7d[0].ticker == "STOCK24"
        assert top_7d[0].momentum_7d == 0.01 + (24 * 0.001)
        
        # 20th performer should be STOCK05 (20th highest)
        assert top_7d[19].ticker == "STOCK05"
        assert top_7d[19].momentum_7d == 0.01 + (5 * 0.001)