# AnchorAlpha End-to-End Integration Tests

This directory contains comprehensive end-to-end integration tests for the AnchorAlpha momentum screener system. These tests verify the complete data pipeline from FMP API to S3, Streamlit app functionality, EventBridge triggers, error recovery scenarios, and cost optimization.

## Test Coverage

### 1. Complete Data Pipeline Tests (`test_end_to_end_integration.py`)

**TestCompleteDataPipeline**
- ✅ `test_complete_pipeline_fmp_to_s3`: Tests full pipeline from FMP API data fetching through S3 storage
- ✅ `test_pipeline_with_api_failures`: Tests pipeline resilience with API failures and error handling
- ✅ `test_pipeline_data_consistency`: Tests data consistency across all pipeline stages

**TestStreamlitS3Integration**
- ✅ `test_streamlit_data_loading_from_s3`: Tests Streamlit app loading data from S3
- ✅ `test_streamlit_ui_data_transformation`: Tests UI data transformation pipeline
- ✅ `test_streamlit_error_handling`: Tests error handling in Streamlit app

**TestEventBridgeLambdaIntegration**
- ✅ `test_eventbridge_lambda_trigger`: Tests EventBridge triggering Lambda function
- ✅ `test_lambda_handler_with_eventbridge_event`: Tests Lambda handler with EventBridge events

**TestErrorRecoveryScenarios**
- ✅ `test_s3_upload_failure_recovery`: Tests recovery from S3 upload failures
- ✅ `test_partial_data_processing_recovery`: Tests recovery from partial data processing failures
- ✅ `test_data_consistency_validation`: Tests data consistency validation

**TestCostOptimizationValidation**
- ✅ `test_api_rate_limiting`: Tests API rate limiting to control costs
- ✅ `test_s3_storage_optimization`: Tests S3 storage optimization features
- ✅ `test_lambda_memory_optimization`: Tests Lambda memory usage optimization
- ✅ `test_resource_usage_monitoring`: Tests resource usage monitoring capabilities

### 2. AWS Infrastructure Integration Tests (`test_aws_infrastructure_integration.py`)

**TestCloudWatchIntegration**
- ✅ `test_structured_logging_to_cloudwatch`: Tests structured logging integration
- ✅ `test_cloudwatch_metrics_publishing`: Tests CloudWatch metrics publishing
- ✅ `test_api_monitoring_cloudwatch_integration`: Tests API monitoring with CloudWatch

**TestSNSNotificationIntegration**
- ✅ `test_sns_notification_setup`: Tests SNS topic and subscription setup
- ✅ `test_error_notification_scenarios`: Tests various error notification scenarios

**TestEventBridgeScheduling**
- ✅ `test_eventbridge_rule_creation`: Tests EventBridge rule creation and configuration
- ✅ `test_eventbridge_lambda_target`: Tests EventBridge Lambda target configuration
- ✅ `test_schedule_expression_validation`: Tests schedule expression validation

**TestBudgetMonitoring**
- ✅ `test_budget_creation_and_monitoring`: Tests budget creation and monitoring setup
- ✅ `test_cost_optimization_monitoring`: Tests cost optimization monitoring logic

**TestIAMPermissionsValidation**
- ✅ `test_lambda_execution_role_permissions`: Tests Lambda execution role permissions
- ✅ `test_s3_bucket_policy_validation`: Tests S3 bucket policy validation

**TestInfrastructureDeployment**
- ✅ `test_cloudformation_template_validation`: Tests CloudFormation template structure
- ✅ `test_deployment_script_validation`: Tests deployment script functionality

### 3. Simple Integration Tests (`test_simple_integration.py`)

Basic integration tests that verify core functionality:
- ✅ `test_imports`: Tests that all required modules can be imported
- ✅ `test_basic_data_pipeline`: Tests basic data pipeline components
- ✅ `test_mock_s3_integration`: Tests mock S3 integration
- ✅ `test_lambda_handler_mock`: Tests Lambda handler with mocked dependencies
- ✅ `test_streamlit_data_loader_mock`: Tests Streamlit data loader with mocked S3

### 4. Test Runner (`test_integration_runner.py`)

Comprehensive test runner that:
- ✅ Executes all integration test modules
- ✅ Generates detailed test reports
- ✅ Provides performance benchmarks
- ✅ Validates pipeline functionality
- ✅ Saves results to JSON files

## Requirements Coverage

### Requirement 6.1: Data Processing Architecture
- ✅ Tests Lambda function data processing pipeline
- ✅ Validates separation of data processing from presentation
- ✅ Tests error handling and recovery mechanisms

### Requirement 6.2: S3 Data Storage Integration
- ✅ Tests S3 data upload and download functionality
- ✅ Validates JSON schema and data consistency
- ✅ Tests Streamlit app S3 integration

### Requirement 5.4: Cost Optimization
- ✅ Tests API rate limiting to control costs
- ✅ Validates AWS resource usage monitoring
- ✅ Tests budget monitoring and alerts

## Running the Tests

### Run All Integration Tests
```bash
# Run comprehensive integration test suite
python AnchorAlpha/tst/AnchorAlpha/test_integration_runner.py

# Run specific test modules with pytest
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_end_to_end_integration.py -v
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_aws_infrastructure_integration.py -v
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_simple_integration.py -v
```

### Run Specific Test Categories
```bash
# Run data pipeline tests
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_end_to_end_integration.py::TestCompleteDataPipeline -v

# Run Streamlit integration tests
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_end_to_end_integration.py::TestStreamlitS3Integration -v

# Run AWS infrastructure tests
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_aws_infrastructure_integration.py::TestCloudWatchIntegration -v

# Run error recovery tests
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_end_to_end_integration.py::TestErrorRecoveryScenarios -v
```

### Run Simple Validation Tests
```bash
# Quick validation of core functionality
python AnchorAlpha/tst/AnchorAlpha/test_simple_integration.py
```

## Test Environment Setup

### Required Dependencies
```bash
pip install pytest moto boto3 streamlit
```

### Environment Variables (for real AWS testing)
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
export FMP_API_KEY=your_fmp_key
export PERPLEXITY_API_KEY=your_perplexity_key
export S3_BUCKET=your-test-bucket
```

## Test Architecture

### Mocking Strategy
- **AWS Services**: Uses `moto` library for mocking AWS services (S3, Lambda, EventBridge, SNS, CloudWatch)
- **External APIs**: Uses `unittest.mock` for mocking FMP and Perplexity APIs
- **Streamlit**: Mocks Streamlit cache decorators for testing

### Test Data
- **Stock Data**: Uses realistic market cap values (>$10B threshold)
- **Historical Prices**: Generates predictable price sequences for momentum calculations
- **API Responses**: Simulates realistic API response structures

### Error Scenarios
- **API Failures**: Tests rate limiting, connection errors, invalid responses
- **S3 Failures**: Tests upload failures, permission errors, corrupted data
- **Data Consistency**: Tests partial failures and data validation

## Performance Benchmarks

The integration tests include performance benchmarks for:
- ✅ Lambda cold start time (target: < 5 seconds)
- ✅ S3 data upload speed (target: < 2 seconds for 1MB)
- ✅ Streamlit data loading (target: < 3 seconds)
- ✅ API rate limit compliance (target: 95% compliance)

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- ✅ No external dependencies (uses mocks)
- ✅ Deterministic results
- ✅ Comprehensive error reporting
- ✅ JSON output for automated analysis

## Test Reports

The test runner generates detailed reports including:
- ✅ Test execution summary
- ✅ Performance metrics
- ✅ Error analysis
- ✅ Coverage statistics
- ✅ JSON export for further analysis

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure `PYTHONPATH` includes the `src` directory
2. **Mock Failures**: Verify `moto` version compatibility
3. **Test Timeouts**: Increase timeout values for slower systems
4. **Memory Issues**: Reduce test data size if running on limited memory

### Debug Mode
```bash
# Run tests with verbose output and no capture
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_simple_integration.py -v -s

# Run with debugging
python -m pytest AnchorAlpha/tst/AnchorAlpha/test_simple_integration.py --pdb
```

## Future Enhancements

Planned improvements for the integration test suite:
- [ ] Real AWS environment testing (optional)
- [ ] Load testing with large datasets
- [ ] Security testing for IAM permissions
- [ ] Performance regression testing
- [ ] Automated test data generation
- [ ] Integration with GitHub Actions
- [ ] Test coverage reporting
- [ ] Parallel test execution

## Contributing

When adding new integration tests:
1. Follow the existing test structure and naming conventions
2. Use appropriate mocking for external dependencies
3. Include both success and failure scenarios
4. Add performance benchmarks where applicable
5. Update this README with new test descriptions
6. Ensure tests are deterministic and can run in any order