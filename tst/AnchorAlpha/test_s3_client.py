"""
Unit tests for S3 data storage functionality.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from botocore.exceptions import ClientError, NoCredentialsError

from AnchorAlpha.storage.s3_client import S3DataStorage
from AnchorAlpha.models import Stock


class TestS3DataStorage:
    """Test cases for S3DataStorage class."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client for testing."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            yield mock_s3
    
    @pytest.fixture
    def s3_storage(self, mock_s3_client):
        """S3DataStorage instance with mocked client."""
        return S3DataStorage(bucket_name="test-bucket", region="us-east-1")
    
    @pytest.fixture
    def sample_stock_data(self):
        """Sample stock data for testing."""
        stocks = [
            Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.25,
                market_cap=2400000000000,
                momentum_7d=0.0523,
                momentum_30d=0.1245,
                momentum_60d=0.0876,
                momentum_90d=0.1567,
                ai_summary="Apple shares surged on strong iPhone sales"
            ),
            Stock(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                current_price=300.50,
                market_cap=2200000000000,
                momentum_7d=0.0312,
                momentum_30d=0.0987,
                momentum_60d=0.1234,
                momentum_90d=0.0876
            )
        ]
        
        return {
            "1T_plus": {
                "7": stocks,
                "30": stocks[:1],
                "60": stocks,
                "90": stocks[:1]
            },
            "500B_1T": {
                "7": [],
                "30": [],
                "60": [],
                "90": []
            }
        }
    
    def test_init_success(self, mock_s3_client):
        """Test successful S3DataStorage initialization."""
        storage = S3DataStorage(bucket_name="test-bucket", region="us-east-1")
        
        assert storage.bucket_name == "test-bucket"
        assert storage.region == "us-east-1"
        assert storage.key_prefix == "momentum-data"
    
    def test_init_no_credentials(self):
        """Test initialization failure with no credentials."""
        with patch('boto3.client', side_effect=NoCredentialsError()):
            with pytest.raises(NoCredentialsError):
                S3DataStorage()
    
    def test_generate_s3_key(self, s3_storage):
        """Test S3 key generation."""
        key = s3_storage._generate_s3_key("2026-02-21")
        assert key == "momentum-data/momentum-data-2026-02-21.json"
    
    def test_validate_bucket_access_success(self, s3_storage, mock_s3_client):
        """Test successful bucket access validation."""
        mock_s3_client.head_bucket.return_value = {}
        
        result = s3_storage._validate_bucket_access()
        
        assert result is True
        mock_s3_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    
    def test_validate_bucket_access_not_found(self, s3_storage, mock_s3_client):
        """Test bucket access validation when bucket doesn't exist."""
        mock_s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadBucket'
        )
        
        result = s3_storage._validate_bucket_access()
        
        assert result is False
    
    def test_validate_bucket_access_forbidden(self, s3_storage, mock_s3_client):
        """Test bucket access validation when access is denied."""
        mock_s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '403'}}, 'HeadBucket'
        )
        
        result = s3_storage._validate_bucket_access()
        
        assert result is False
    
    def test_serialize_stock(self, s3_storage):
        """Test stock serialization to dictionary."""
        stock = Stock(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=150.25,
            market_cap=2400000000000,
            momentum_7d=0.0523,
            momentum_30d=0.1245,
            ai_summary="Test summary"
        )
        
        result = s3_storage._serialize_stock(stock)
        
        expected = {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "current_price": 150.25,
            "market_cap": 2400000000000,
            "momentum_7d": 0.0523,
            "momentum_30d": 0.1245,
            "momentum_60d": None,
            "momentum_90d": None,
            "ai_summary": "Test summary",
            "tier": "1T_plus"
        }
        
        assert result == expected
    
    def test_serialize_stock_data(self, s3_storage, sample_stock_data):
        """Test complete stock data serialization."""
        with patch('AnchorAlpha.storage.s3_client.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2026-02-21T16:30:00Z"
            
            result = s3_storage._serialize_stock_data(sample_stock_data, "2026-02-21")
        
        assert result["generated_at"] == "2026-02-21T16:30:00Z"
        assert result["market_date"] == "2026-02-21"
        assert result["data_version"] == "1.0"
        assert "tiers" in result
        assert "1T_plus" in result["tiers"]
        assert "7_day" in result["tiers"]["1T_plus"]
        assert len(result["tiers"]["1T_plus"]["7_day"]) == 2
    
    def test_upload_momentum_data_success(self, s3_storage, mock_s3_client, sample_stock_data):
        """Test successful momentum data upload."""
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.put_object.return_value = {}
        
        result = s3_storage.upload_momentum_data(sample_stock_data, "2026-02-21")
        
        assert result is True
        mock_s3_client.put_object.assert_called_once()
        
        # Verify put_object call arguments
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == "test-bucket"
        assert call_args[1]['Key'] == "momentum-data/momentum-data-2026-02-21.json"
        assert call_args[1]['ContentType'] == 'application/json'
        assert call_args[1]['ServerSideEncryption'] == 'AES256'
    
    def test_upload_momentum_data_bucket_validation_fails(self, s3_storage, mock_s3_client, sample_stock_data):
        """Test upload failure when bucket validation fails."""
        mock_s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadBucket'
        )
        
        result = s3_storage.upload_momentum_data(sample_stock_data, "2026-02-21")
        
        assert result is False
        mock_s3_client.put_object.assert_not_called()
    
    def test_upload_momentum_data_with_retry(self, s3_storage, mock_s3_client, sample_stock_data):
        """Test upload with retry logic."""
        mock_s3_client.head_bucket.return_value = {}
        
        # First two attempts fail, third succeeds
        mock_s3_client.put_object.side_effect = [
            ClientError({'Error': {'Code': '500'}}, 'PutObject'),
            ClientError({'Error': {'Code': '503'}}, 'PutObject'),
            {}
        ]
        
        result = s3_storage.upload_momentum_data(sample_stock_data, "2026-02-21", retry_count=3)
        
        assert result is True
        assert mock_s3_client.put_object.call_count == 3
    
    def test_upload_momentum_data_all_retries_fail(self, s3_storage, mock_s3_client, sample_stock_data):
        """Test upload failure after all retries."""
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': '500'}}, 'PutObject'
        )
        
        result = s3_storage.upload_momentum_data(sample_stock_data, "2026-02-21", retry_count=2)
        
        assert result is False
        assert mock_s3_client.put_object.call_count == 2
    
    def test_download_momentum_data_success(self, s3_storage, mock_s3_client):
        """Test successful momentum data download."""
        mock_data = {
            "generated_at": "2026-02-21T16:30:00Z",
            "market_date": "2026-02-21",
            "tiers": {}
        }
        
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = json.dumps(mock_data).encode('utf-8')
        mock_s3_client.get_object.return_value = mock_response
        
        result = s3_storage.download_momentum_data("2026-02-21")
        
        assert result == mock_data
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="momentum-data/momentum-data-2026-02-21.json"
        )
    
    def test_download_momentum_data_not_found(self, s3_storage, mock_s3_client):
        """Test download when data doesn't exist."""
        mock_s3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )
        
        result = s3_storage.download_momentum_data("2026-02-21")
        
        assert result is None
    
    def test_download_momentum_data_error(self, s3_storage, mock_s3_client):
        """Test download with unexpected error."""
        mock_s3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': '500'}}, 'GetObject'
        )
        
        result = s3_storage.download_momentum_data("2026-02-21")
        
        assert result is None
    
    def test_list_available_dates_success(self, s3_storage, mock_s3_client):
        """Test listing available dates."""
        mock_response = {
            'Contents': [
                {'Key': 'momentum-data/momentum-data-2026-02-21.json'},
                {'Key': 'momentum-data/momentum-data-2026-02-20.json'},
                {'Key': 'momentum-data/momentum-data-2026-02-19.json'}
            ]
        }
        mock_s3_client.list_objects_v2.return_value = mock_response
        
        result = s3_storage.list_available_dates()
        
        expected = ["2026-02-21", "2026-02-20", "2026-02-19"]
        assert result == expected
        
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket="test-bucket",
            Prefix="momentum-data/momentum-data-",
            MaxKeys=30
        )
    
    def test_list_available_dates_empty(self, s3_storage, mock_s3_client):
        """Test listing dates when no files exist."""
        mock_s3_client.list_objects_v2.return_value = {}
        
        result = s3_storage.list_available_dates()
        
        assert result == []
    
    def test_list_available_dates_error(self, s3_storage, mock_s3_client):
        """Test listing dates with error."""
        mock_s3_client.list_objects_v2.side_effect = Exception("S3 error")
        
        result = s3_storage.list_available_dates()
        
        assert result == []
    
    def test_validate_json_schema_valid(self, s3_storage):
        """Test JSON schema validation with valid data."""
        valid_data = {
            "generated_at": "2026-02-21T16:30:00Z",
            "market_date": "2026-02-21",
            "data_version": "1.0",
            "tiers": {
                "1T_plus": {
                    "7_day": [
                        {
                            "ticker": "AAPL",
                            "company_name": "Apple Inc.",
                            "current_price": 150.25,
                            "market_cap": 2400000000000
                        }
                    ]
                }
            }
        }
        
        result = s3_storage.validate_json_schema(valid_data)
        assert result is True
    
    def test_validate_json_schema_missing_field(self, s3_storage):
        """Test JSON schema validation with missing required field."""
        invalid_data = {
            "generated_at": "2026-02-21T16:30:00Z",
            "market_date": "2026-02-21",
            # Missing data_version and tiers
        }
        
        result = s3_storage.validate_json_schema(invalid_data)
        assert result is False
    
    def test_validate_json_schema_invalid_tiers(self, s3_storage):
        """Test JSON schema validation with invalid tiers structure."""
        invalid_data = {
            "generated_at": "2026-02-21T16:30:00Z",
            "market_date": "2026-02-21",
            "data_version": "1.0",
            "tiers": "not_a_dict"  # Should be dict
        }
        
        result = s3_storage.validate_json_schema(invalid_data)
        assert result is False
    
    def test_validate_stock_data_valid(self, s3_storage):
        """Test stock data validation with valid data."""
        valid_stock = {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "current_price": 150.25,
            "market_cap": 2400000000000
        }
        
        result = s3_storage._validate_stock_data(valid_stock)
        assert result is True
    
    def test_validate_stock_data_missing_field(self, s3_storage):
        """Test stock data validation with missing field."""
        invalid_stock = {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            # Missing current_price and market_cap
        }
        
        result = s3_storage._validate_stock_data(invalid_stock)
        assert result is False
    
    def test_validate_stock_data_invalid_types(self, s3_storage):
        """Test stock data validation with invalid data types."""
        invalid_stock = {
            "ticker": 123,  # Should be string
            "company_name": "Apple Inc.",
            "current_price": "150.25",  # Should be number
            "market_cap": "2400000000000"  # Should be int
        }
        
        result = s3_storage._validate_stock_data(invalid_stock)
        assert result is False


class TestS3DataStorageIntegration:
    """Integration tests for S3DataStorage."""
    
    @pytest.fixture
    def s3_storage(self):
        """Real S3DataStorage instance for integration tests."""
        return S3DataStorage(bucket_name="test-bucket", region="us-east-1")
    
    @pytest.fixture
    def sample_stocks(self):
        """Sample stock objects for integration testing."""
        return [
            Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.25,
                market_cap=2400000000000,
                momentum_7d=0.0523,
                momentum_30d=0.1245,
                momentum_60d=0.0876,
                momentum_90d=0.1567,
                ai_summary="Apple shares surged on strong iPhone sales"
            ),
            Stock(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                current_price=300.50,
                market_cap=2200000000000,
                momentum_7d=0.0312,
                momentum_30d=0.0987,
                momentum_60d=0.1234,
                momentum_90d=0.0876
            )
        ]
    
    def test_end_to_end_serialization(self, s3_storage, sample_stocks):
        """Test complete serialization and validation flow."""
        # Organize stock data by tier and timeframe
        stock_data = {
            "1T_plus": {
                "7": sample_stocks,
                "30": sample_stocks[:1],
                "60": sample_stocks,
                "90": sample_stocks[:1]
            }
        }
        
        # Serialize the data
        json_data = s3_storage._serialize_stock_data(stock_data, "2026-02-21")
        
        # Validate the serialized data
        assert s3_storage.validate_json_schema(json_data)
        
        # Verify structure
        assert json_data["market_date"] == "2026-02-21"
        assert "1T_plus" in json_data["tiers"]
        assert "7_day" in json_data["tiers"]["1T_plus"]
        assert len(json_data["tiers"]["1T_plus"]["7_day"]) == 2
        
        # Verify stock data integrity
        first_stock = json_data["tiers"]["1T_plus"]["7_day"][0]
        assert first_stock["ticker"] == "AAPL"
        assert first_stock["current_price"] == 150.25
        assert first_stock["momentum_7d"] == 0.0523
        assert first_stock["ai_summary"] == "Apple shares surged on strong iPhone sales"