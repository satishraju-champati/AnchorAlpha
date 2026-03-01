"""
Simple integration test to verify the end-to-end testing framework works.
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

# Test basic imports work
def test_imports():
    """Test that all required modules can be imported."""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
        
        from AnchorAlpha.models import Stock
        from AnchorAlpha.momentum_engine import MomentumEngine
        
        # Test Stock creation with valid market cap
        stock = Stock("AAPL", "Apple Inc.", 150.0, 2500000000000)  # $2.5T
        assert stock.ticker == "AAPL"
        assert stock.market_cap == 2500000000000
        
        # Test MomentumEngine
        engine = MomentumEngine()
        assert engine is not None
        
        print("✅ All imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_basic_data_pipeline():
    """Test basic data pipeline components."""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
        
        from AnchorAlpha.models import Stock
        from AnchorAlpha.momentum_engine import MomentumEngine, HistoricalPriceData
        
        # Create test data
        stock = Stock("AAPL", "Apple Inc.", 150.0, 2500000000000)
        historical_data = HistoricalPriceData(
            ticker="AAPL",
            current_price=150.0,
            prices_7d_ago=145.0,
            prices_30d_ago=140.0,
            prices_60d_ago=135.0,
            prices_90d_ago=130.0
        )
        
        # Test momentum calculation
        engine = MomentumEngine()
        processed_stock = engine.calculate_stock_momentum(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=150.0,
            market_cap=2500000000000,
            historical_data=historical_data
        )
        
        assert processed_stock is not None
        assert processed_stock.momentum_7d is not None
        assert processed_stock.momentum_30d is not None
        
        # Verify momentum calculation
        expected_7d = (150.0 / 145.0) - 1
        assert abs(processed_stock.momentum_7d - expected_7d) < 0.001
        
        print("✅ Basic data pipeline test successful")
        return True
        
    except Exception as e:
        print(f"❌ Data pipeline test failed: {e}")
        return False


def test_mock_s3_integration():
    """Test mock S3 integration."""
    try:
        from moto import mock_aws
        import boto3
        
        with mock_aws():
            # Create mock S3 bucket
            s3_client = boto3.client('s3', region_name='us-east-1')
            bucket_name = 'test-bucket'
            s3_client.create_bucket(Bucket=bucket_name)
            
            # Test data upload
            test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
            s3_client.put_object(
                Bucket=bucket_name,
                Key='test-data.json',
                Body=json.dumps(test_data),
                ContentType='application/json'
            )
            
            # Test data download
            response = s3_client.get_object(Bucket=bucket_name, Key='test-data.json')
            downloaded_data = json.loads(response['Body'].read().decode('utf-8'))
            
            assert downloaded_data['test'] == 'data'
            
        print("✅ Mock S3 integration test successful")
        return True
        
    except Exception as e:
        print(f"❌ Mock S3 integration test failed: {e}")
        return False


def test_lambda_handler_mock():
    """Test Lambda handler with mocked dependencies."""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
        
        # Mock the Lambda handler execution
        with patch('AnchorAlpha.lambda_function.handler.LambdaOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_pipeline.return_value = {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Pipeline execution completed",
                    "success": True,
                    "execution_id": "test-execution-id"
                })
            }
            mock_orchestrator_class.return_value = mock_orchestrator
            
            from AnchorAlpha.lambda_function.handler import lambda_handler
            
            # Test event and context
            test_event = {"source": "aws.events", "detail-type": "Scheduled Event"}
            mock_context = Mock()
            mock_context.function_name = "test-function"
            mock_context.function_version = "1"
            mock_context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
            mock_context.memory_limit_in_mb = 512
            mock_context.get_remaining_time_in_millis.return_value = 300000
            
            # Execute handler
            result = lambda_handler(test_event, mock_context)
            
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["success"] is True
            
        print("✅ Lambda handler mock test successful")
        return True
        
    except Exception as e:
        print(f"❌ Lambda handler mock test failed: {e}")
        return False


def test_streamlit_data_loader_mock():
    """Test Streamlit data loader with mocked S3."""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
        
        # Mock streamlit cache decorators
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            with patch('AnchorAlpha.streamlit_app.data_loader.S3DataStorage') as mock_s3:
                mock_s3_instance = Mock()
                mock_s3_instance.list_available_dates.return_value = ['2026-03-01', '2026-02-28']
                mock_s3_instance.download_momentum_data.return_value = {
                    "generated_at": "2026-03-01T16:30:00Z",
                    "market_date": "2026-03-01",
                    "tiers": {
                        "1T_plus": {
                            "7_day": [
                                {
                                    "ticker": "AAPL",
                                    "company_name": "Apple Inc.",
                                    "current_price": 150.0,
                                    "market_cap": 2500000000000,
                                    "momentum_7d": 0.05
                                }
                            ]
                        }
                    }
                }
                mock_s3_instance.validate_json_schema.return_value = True
                mock_s3.return_value = mock_s3_instance
                
                from AnchorAlpha.streamlit_app.data_loader import StreamlitDataLoader
                
                data_loader = StreamlitDataLoader()
                result = data_loader.load_latest_momentum_data()
                
                assert result is not None
                assert result['market_date'] == '2026-03-01'
                assert '1T_plus' in result['tiers']
        
        print("✅ Streamlit data loader mock test successful")
        return True
        
    except Exception as e:
        print(f"❌ Streamlit data loader mock test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Running Simple Integration Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_basic_data_pipeline,
        test_mock_s3_integration,
        test_lambda_handler_mock,
        test_streamlit_data_loader_mock
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n🔍 Running {test.__name__}...")
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All simple integration tests passed!")
    else:
        print("⚠️  Some tests failed - check the output above")