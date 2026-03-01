#!/bin/bash

# Deploy AnchorAlpha monitoring and logging infrastructure
# This script deploys CloudWatch dashboards, alarms, and monitoring configuration

set -e

# Configuration
ENVIRONMENT=${1:-prod}
STACK_NAME="anchor-alpha-monitoring-${ENVIRONMENT}"
LAMBDA_FUNCTION_NAME=${2:-"anchor-alpha-momentum-processor-${ENVIRONMENT}"}
S3_BUCKET_NAME=${3:-"anchor-alpha-momentum-data-${ENVIRONMENT}"}
NOTIFICATION_EMAIL=${4:-""}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    # Check required parameters
    if [[ -z "$LAMBDA_FUNCTION_NAME" ]]; then
        log_error "Lambda function name is required"
        exit 1
    fi
    
    if [[ -z "$S3_BUCKET_NAME" ]]; then
        log_error "S3 bucket name is required"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Validate CloudFormation template
validate_template() {
    local template_file=$1
    log_info "Validating CloudFormation template: $template_file"
    
    if aws cloudformation validate-template --template-body file://$template_file > /dev/null; then
        log_info "Template validation passed"
    else
        log_error "Template validation failed"
        exit 1
    fi
}

# Deploy monitoring dashboard
deploy_monitoring_dashboard() {
    log_info "Deploying monitoring dashboard stack..."
    
    local template_file="../cloudformation/monitoring-dashboard.yaml"
    
    # Validate template
    validate_template $template_file
    
    # Prepare parameters
    local parameters="ParameterKey=Environment,ParameterValue=${ENVIRONMENT}"
    parameters="${parameters} ParameterKey=LambdaFunctionName,ParameterValue=${LAMBDA_FUNCTION_NAME}"
    parameters="${parameters} ParameterKey=S3BucketName,ParameterValue=${S3_BUCKET_NAME}"
    
    # Deploy stack
    if aws cloudformation describe-stacks --stack-name $STACK_NAME &> /dev/null; then
        log_info "Stack exists, updating..."
        aws cloudformation update-stack \
            --stack-name $STACK_NAME \
            --template-body file://$template_file \
            --parameters $parameters \
            --capabilities CAPABILITY_IAM
        
        log_info "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete --stack-name $STACK_NAME
    else
        log_info "Creating new stack..."
        aws cloudformation create-stack \
            --stack-name $STACK_NAME \
            --template-body file://$template_file \
            --parameters $parameters \
            --capabilities CAPABILITY_IAM
        
        log_info "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name $STACK_NAME
    fi
    
    log_info "Monitoring dashboard stack deployed successfully"
}

# Configure SNS notifications
configure_sns_notifications() {
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        log_info "Configuring SNS notifications for email: $NOTIFICATION_EMAIL"
        
        # Get SNS topic ARN from main infrastructure stack
        local main_stack_name="anchor-alpha-infrastructure-${ENVIRONMENT}"
        local topic_arn=$(aws cloudformation describe-stacks \
            --stack-name $main_stack_name \
            --query 'Stacks[0].Outputs[?OutputKey==`NotificationTopicArn`].OutputValue' \
            --output text 2>/dev/null || echo "")
        
        if [[ -n "$topic_arn" ]]; then
            # Subscribe email to SNS topic
            aws sns subscribe \
                --topic-arn $topic_arn \
                --protocol email \
                --notification-endpoint $NOTIFICATION_EMAIL
            
            log_info "SNS email subscription created. Please check your email and confirm the subscription."
        else
            log_warn "Could not find SNS topic ARN. Make sure the main infrastructure stack is deployed."
        fi
    else
        log_warn "No notification email provided. Skipping SNS configuration."
    fi
}

# Set up CloudWatch log retention
configure_log_retention() {
    log_info "Configuring CloudWatch log retention..."
    
    local log_groups=(
        "/aws/lambda/${LAMBDA_FUNCTION_NAME}"
        "/aws/anchoralpha/custom-metrics-${ENVIRONMENT}"
        "/aws/anchoralpha/api-usage-${ENVIRONMENT}"
    )
    
    for log_group in "${log_groups[@]}"; do
        if aws logs describe-log-groups --log-group-name-prefix "$log_group" --query 'logGroups[0].logGroupName' --output text | grep -q "$log_group"; then
            log_info "Setting retention for log group: $log_group"
            aws logs put-retention-policy \
                --log-group-name "$log_group" \
                --retention-in-days 30
        else
            log_warn "Log group $log_group does not exist yet. It will be created when the Lambda function runs."
        fi
    done
}

# Create custom CloudWatch alarms
create_custom_alarms() {
    log_info "Creating custom CloudWatch alarms..."
    
    # API Rate Limit Alarm for FMP
    aws cloudwatch put-metric-alarm \
        --alarm-name "AnchorAlpha-FMP-RateLimit-${ENVIRONMENT}" \
        --alarm-description "Alert when FMP API rate limit utilization is high" \
        --metric-name "APIRateLimitUtilization" \
        --namespace "AnchorAlpha/APIUsage" \
        --statistic "Maximum" \
        --period 300 \
        --evaluation-periods 2 \
        --threshold 85 \
        --comparison-operator "GreaterThanThreshold" \
        --dimensions "Name=APIName,Value=FMP" \
        --treat-missing-data "notBreaching"
    
    # API Rate Limit Alarm for Perplexity
    aws cloudwatch put-metric-alarm \
        --alarm-name "AnchorAlpha-Perplexity-RateLimit-${ENVIRONMENT}" \
        --alarm-description "Alert when Perplexity API rate limit utilization is high" \
        --metric-name "APIRateLimitUtilization" \
        --namespace "AnchorAlpha/APIUsage" \
        --statistic "Maximum" \
        --period 300 \
        --evaluation-periods 2 \
        --threshold 85 \
        --comparison-operator "GreaterThanThreshold" \
        --dimensions "Name=APIName,Value=Perplexity" \
        --treat-missing-data "notBreaching"
    
    # Data Processing Success Rate Alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "AnchorAlpha-ProcessingSuccess-${ENVIRONMENT}" \
        --alarm-description "Alert when data processing success rate is low" \
        --metric-name "ExecutionSuccess" \
        --namespace "AnchorAlpha/MomentumScreener" \
        --statistic "Average" \
        --period 300 \
        --evaluation-periods 2 \
        --threshold 0.8 \
        --comparison-operator "LessThanThreshold" \
        --treat-missing-data "breaching"
    
    log_info "Custom CloudWatch alarms created"
}

# Display deployment summary
display_summary() {
    log_info "Deployment Summary:"
    echo "===================="
    echo "Environment: $ENVIRONMENT"
    echo "Stack Name: $STACK_NAME"
    echo "Lambda Function: $LAMBDA_FUNCTION_NAME"
    echo "S3 Bucket: $S3_BUCKET_NAME"
    
    # Get dashboard URL
    local dashboard_url=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' \
        --output text 2>/dev/null || echo "Not available")
    
    echo "Dashboard URL: $dashboard_url"
    
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        echo "Notification Email: $NOTIFICATION_EMAIL"
    fi
    
    echo ""
    log_info "Monitoring infrastructure deployed successfully!"
    
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        log_warn "Please check your email and confirm the SNS subscription to receive alerts."
    fi
}

# Cleanup function for error handling
cleanup() {
    if [[ $? -ne 0 ]]; then
        log_error "Deployment failed. Check the error messages above."
        exit 1
    fi
}

# Main execution
main() {
    log_info "Starting AnchorAlpha monitoring infrastructure deployment..."
    log_info "Environment: $ENVIRONMENT"
    
    # Set up error handling
    trap cleanup EXIT
    
    # Execute deployment steps
    check_prerequisites
    deploy_monitoring_dashboard
    configure_sns_notifications
    configure_log_retention
    create_custom_alarms
    display_summary
    
    # Remove error trap on successful completion
    trap - EXIT
}

# Help function
show_help() {
    echo "Usage: $0 [ENVIRONMENT] [LAMBDA_FUNCTION_NAME] [S3_BUCKET_NAME] [NOTIFICATION_EMAIL]"
    echo ""
    echo "Deploy AnchorAlpha monitoring and logging infrastructure"
    echo ""
    echo "Arguments:"
    echo "  ENVIRONMENT           Environment name (default: prod)"
    echo "  LAMBDA_FUNCTION_NAME  Name of the Lambda function to monitor"
    echo "  S3_BUCKET_NAME        Name of the S3 bucket to monitor"
    echo "  NOTIFICATION_EMAIL    Email address for alerts (optional)"
    echo ""
    echo "Examples:"
    echo "  $0 prod anchor-alpha-momentum-processor-prod anchor-alpha-data-prod admin@example.com"
    echo "  $0 dev"
    echo ""
    echo "Prerequisites:"
    echo "  - AWS CLI installed and configured"
    echo "  - Appropriate AWS permissions for CloudFormation, CloudWatch, SNS, and S3"
    echo "  - Main AnchorAlpha infrastructure stack already deployed"
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@"