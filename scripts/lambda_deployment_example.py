#!/usr/bin/env python3
"""
Example script demonstrating Lambda function deployment configuration.

This script shows how to configure environment variables and test the Lambda handler
locally before deployment to AWS.

Requirements: 5.2, 6.1, 8.1, 8.3
"""

import os
import json
from datetime import datetime
from unittest.mock import Mock

# Set up environment variables for testing
os.environ.update({
    "FMP_API_KEY": "your_fmp_api_key_here",
    "PERPLEXITY_API_KEY": "your_perplexity_api_key_here",
    "AWS_REGION": "us-east-1",
    "S3_BUCKET": "anchoralpha-data-test",
})

# Import the Lambda handler after setting environment variables
from AnchorAlpha.lambda_function.handler import lambda_handler


def create_test_event():
    """Create a test EventBridge event for Lambda testing."""
    return {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": datetime.utcnow().isoformat() + "Z",
        "region": "us-east-1",
        "detail": {}
    }


def create_test_context():
    """Create a mock Lambda context for testing."""
    context = Mock()
    context.function_name = "anchoralpha-momentum-screener"
    context.function_version = "1"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:anchoralpha-momentum-screener"
    context.memory_limit_in_mb = 512
    context.get_remaining_time_in_millis = Mock(return_value=300000)  # 5 minutes
    return context


def test_lambda_handler_locally():
    """Test the Lambda handler function locally."""
    print("Testing Lambda handler locally...")
    
    # Create test event and context
    event = create_test_event()
    context = create_test_context()
    
    print(f"Test event: {json.dumps(event, indent=2)}")
    print(f"Function name: {context.function_name}")
    print(f"Memory limit: {context.memory_limit_in_mb} MB")
    print(f"Remaining time: {context.get_remaining_time_in_millis()} ms")
    
    try:
        # Call the Lambda handler
        result = lambda_handler(event, context)
        
        print(f"\nLambda execution result:")
        print(f"Status Code: {result['statusCode']}")
        
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', 'Unknown')}")
        print(f"Message: {body.get('message', 'No message')}")
        
        if 'metrics' in body:
            metrics = body['metrics']
            print(f"\nExecution Metrics:")
            print(f"- Execution ID: {metrics.get('execution_id')}")
            print(f"- Market Date: {metrics.get('market_date')}")
            print(f"- Stocks Fetched: {metrics.get('stocks_fetched', 0)}")
            print(f"- Stocks Processed: {metrics.get('stocks_processed', 0)}")
            print(f"- Summaries Generated: {metrics.get('summaries_generated', 0)}")
            print(f"- Duration: {metrics.get('duration_seconds', 0):.2f} seconds")
            
            if metrics.get('errors'):
                print(f"- Errors: {len(metrics['errors'])}")
                for error in metrics['errors']:
                    print(f"  * {error}")
            
            if metrics.get('warnings'):
                print(f"- Warnings: {len(metrics['warnings'])}")
                for warning in metrics['warnings']:
                    print(f"  * {warning}")
        
        return result
        
    except Exception as e:
        print(f"Lambda handler failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_deployment_configuration():
    """Show example deployment configuration."""
    print("\n" + "="*80)
    print("AWS LAMBDA DEPLOYMENT CONFIGURATION")
    print("="*80)
    
    print("\n1. Environment Variables:")
    env_vars = {
        "FMP_API_KEY": "your_financial_modeling_prep_api_key",
        "PERPLEXITY_API_KEY": "your_perplexity_api_key",
        "AWS_REGION": "us-east-1",
        "S3_BUCKET": "anchoralpha-data-production"
    }
    
    for key, value in env_vars.items():
        print(f"   {key}={value}")
    
    print("\n2. Lambda Function Configuration:")
    lambda_config = {
        "FunctionName": "anchoralpha-momentum-screener",
        "Runtime": "python3.9",
        "Handler": "AnchorAlpha.lambda_function.handler.lambda_handler",
        "MemorySize": 512,
        "Timeout": 900,  # 15 minutes
        "ReservedConcurrencyLimit": 1
    }
    
    for key, value in lambda_config.items():
        print(f"   {key}: {value}")
    
    print("\n3. IAM Role Permissions Required:")
    permissions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream", 
        "logs:PutLogEvents",
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
    ]
    
    for permission in permissions:
        print(f"   - {permission}")
    
    print("\n4. EventBridge Schedule Expression:")
    print("   Schedule: rate(1 day)")
    print("   Description: Trigger daily at market close")
    
    print("\n5. CloudFormation Template Example:")
    print("""
Resources:
  AnchorAlphaLambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: anchoralpha-momentum-screener
      Runtime: python3.9
      Handler: AnchorAlpha.lambda_function.handler.lambda_handler
      Code:
        ZipFile: |
          # Lambda deployment package
      MemorySize: 512
      Timeout: 900
      Environment:
        Variables:
          FMP_API_KEY: !Ref FMPAPIKey
          PERPLEXITY_API_KEY: !Ref PerplexityAPIKey
          S3_BUCKET: !Ref DataBucket
      Role: !GetAtt LambdaExecutionRole.Arn

  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                  - s3:ListBucket
                Resource:
                  - !Sub "${DataBucket}/*"
                  - !GetAtt DataBucket.Arn

  ScheduleRule:
    Type: AWS::Events::Rule
    Properties:
      Description: "Daily trigger for momentum screener"
      ScheduleExpression: "rate(1 day)"
      State: ENABLED
      Targets:
        - Arn: !GetAtt AnchorAlphaLambdaFunction.Arn
          Id: "AnchorAlphaTarget"
    """)


def show_monitoring_setup():
    """Show monitoring and alerting configuration."""
    print("\n" + "="*80)
    print("MONITORING AND ALERTING SETUP")
    print("="*80)
    
    print("\n1. CloudWatch Log Groups:")
    print("   - /aws/lambda/anchoralpha-momentum-screener")
    print("   - Retention: 30 days")
    print("   - Log format: Structured JSON")
    
    print("\n2. CloudWatch Metrics:")
    metrics = [
        "Duration",
        "Errors", 
        "Invocations",
        "Throttles",
        "ConcurrentExecutions"
    ]
    
    for metric in metrics:
        print(f"   - {metric}")
    
    print("\n3. CloudWatch Alarms:")
    alarms = [
        ("Lambda Errors", "Errors > 0 for 1 period"),
        ("Lambda Duration", "Duration > 600000 ms for 2 periods"),
        ("Lambda Throttles", "Throttles > 0 for 1 period")
    ]
    
    for alarm_name, condition in alarms:
        print(f"   - {alarm_name}: {condition}")
    
    print("\n4. SNS Topics for Notifications:")
    print("   - anchoralpha-alerts")
    print("   - Subscribers: operations team email")
    
    print("\n5. AWS Budgets:")
    print("   - Monthly budget: $10")
    print("   - Alert threshold: 80% of budget")
    print("   - Notification: SNS topic")


if __name__ == "__main__":
    print("AnchorAlpha Lambda Function Deployment Example")
    print("=" * 50)
    
    # Show configuration examples
    show_deployment_configuration()
    show_monitoring_setup()
    
    # Test the handler locally (will use mock clients due to missing API keys)
    print("\n" + "="*80)
    print("LOCAL TESTING")
    print("="*80)
    
    result = test_lambda_handler_locally()
    
    if result:
        print(f"\nLocal test completed successfully!")
    else:
        print(f"\nLocal test failed - check configuration and API keys")
    
    print("\nNext steps:")
    print("1. Set up real API keys in environment variables")
    print("2. Create S3 bucket for data storage")
    print("3. Deploy Lambda function using AWS CLI or CloudFormation")
    print("4. Set up EventBridge schedule for daily execution")
    print("5. Configure CloudWatch monitoring and alerts")