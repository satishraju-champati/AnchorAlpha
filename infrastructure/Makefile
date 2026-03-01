# AnchorAlpha Infrastructure Makefile
# Simplifies deployment and management commands

.PHONY: help validate deploy-infra package-lambda deploy-lambda deploy-container clean

# Default environment
ENV ?= prod
REGION ?= us-east-1
NOTIFICATION_EMAIL ?= 
FMP_API_KEY ?= 
PERPLEXITY_API_KEY ?= 

help: ## Show this help message
	@echo "AnchorAlpha Infrastructure Management"
	@echo ""
	@echo "Usage: make [target] [ENV=environment] [REGION=region]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ""
	@echo "Environment Variables:"
	@echo "  ENV                  Environment (dev/staging/prod) [default: prod]"
	@echo "  REGION              AWS region [default: us-east-1]"
	@echo "  NOTIFICATION_EMAIL  Email for notifications (required)"
	@echo "  FMP_API_KEY         Financial Modeling Prep API key (required)"
	@echo "  PERPLEXITY_API_KEY  Perplexity API key (required)"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy-infra ENV=prod NOTIFICATION_EMAIL=me@example.com FMP_API_KEY=xxx PERPLEXITY_API_KEY=yyy"
	@echo "  make deploy-container ENV=staging"
	@echo "  make package-lambda ENV=dev"

validate: ## Validate CloudFormation templates
	@echo "🔍 Validating CloudFormation templates..."
	@aws cloudformation validate-template \
		--template-body file://cloudformation/anchor-alpha-infrastructure.yaml \
		--region $(REGION)
	@aws cloudformation validate-template \
		--template-body file://cloudformation/lightsail-container.yaml \
		--region $(REGION)
	@echo "✅ Templates are valid"

deploy-infra: validate ## Deploy AWS infrastructure
	@if [ -z "$(NOTIFICATION_EMAIL)" ]; then echo "❌ NOTIFICATION_EMAIL is required"; exit 1; fi
	@if [ -z "$(FMP_API_KEY)" ]; then echo "❌ FMP_API_KEY is required"; exit 1; fi
	@if [ -z "$(PERPLEXITY_API_KEY)" ]; then echo "❌ PERPLEXITY_API_KEY is required"; exit 1; fi
	@echo "🚀 Deploying infrastructure for environment: $(ENV)"
	@./scripts/deploy-infrastructure.sh \
		--environment $(ENV) \
		--region $(REGION) \
		--notification-email $(NOTIFICATION_EMAIL) \
		--fmp-api-key $(FMP_API_KEY) \
		--perplexity-api-key $(PERPLEXITY_API_KEY)

package-lambda: ## Create Lambda deployment package
	@echo "📦 Creating Lambda deployment package for environment: $(ENV)"
	@./scripts/package-lambda.sh --environment $(ENV)

deploy-lambda: package-lambda ## Deploy Lambda function code
	@echo "🚀 Deploying Lambda function for environment: $(ENV)"
	@aws lambda update-function-code \
		--function-name anchor-alpha-momentum-processor-$(ENV) \
		--zip-file fileb://dist/anchor-alpha-lambda-$(ENV).zip \
		--region $(REGION)
	@echo "✅ Lambda function updated successfully"

deploy-container: ## Deploy Streamlit container to Lightsail
	@echo "🐳 Deploying Streamlit container for environment: $(ENV)"
	@./scripts/deploy-container.sh \
		--environment $(ENV) \
		--region $(REGION) \
		--power nano \
		--scale 1

deploy-all: deploy-infra deploy-lambda deploy-container ## Deploy complete infrastructure and applications
	@echo "🎉 Complete deployment finished for environment: $(ENV)"

status: ## Show deployment status
	@echo "📊 Deployment Status for Environment: $(ENV)"
	@echo ""
	@echo "CloudFormation Stack:"
	@aws cloudformation describe-stacks \
		--stack-name anchor-alpha-infrastructure-$(ENV) \
		--region $(REGION) \
		--query 'Stacks[0].{StackName:StackName,Status:StackStatus,CreationTime:CreationTime}' \
		--output table 2>/dev/null || echo "Stack not found"
	@echo ""
	@echo "Lambda Function:"
	@aws lambda get-function \
		--function-name anchor-alpha-momentum-processor-$(ENV) \
		--region $(REGION) \
		--query 'Configuration.{FunctionName:FunctionName,Runtime:Runtime,LastModified:LastModified,State:State}' \
		--output table 2>/dev/null || echo "Function not found"
	@echo ""
	@echo "Lightsail Container:"
	@aws lightsail get-container-services \
		--service-name anchor-alpha-streamlit-$(ENV) \
		--region $(REGION) \
		--query 'containerServices[0].{Name:serviceName,State:state,Power:power,Scale:scale,URL:url}' \
		--output table 2>/dev/null || echo "Container service not found"

logs: ## View Lambda function logs
	@echo "📋 Recent Lambda logs for environment: $(ENV)"
	@aws logs describe-log-streams \
		--log-group-name /aws/lambda/anchor-alpha-momentum-processor-$(ENV) \
		--region $(REGION) \
		--order-by LastEventTime \
		--descending \
		--max-items 1 \
		--query 'logStreams[0].logStreamName' \
		--output text | xargs -I {} aws logs get-log-events \
		--log-group-name /aws/lambda/anchor-alpha-momentum-processor-$(ENV) \
		--log-stream-name {} \
		--region $(REGION) \
		--query 'events[*].[timestamp,message]' \
		--output table

test-lambda: ## Test Lambda function manually
	@echo "🧪 Testing Lambda function for environment: $(ENV)"
	@aws lambda invoke \
		--function-name anchor-alpha-momentum-processor-$(ENV) \
		--region $(REGION) \
		--payload '{"source":"manual-test","environment":"$(ENV)"}' \
		--cli-binary-format raw-in-base64-out \
		/tmp/lambda-response.json
	@echo "Response:"
	@cat /tmp/lambda-response.json | jq .
	@rm -f /tmp/lambda-response.json

clean: ## Clean up build artifacts
	@echo "🧹 Cleaning up build artifacts..."
	@rm -rf dist/
	@rm -rf build/
	@rm -rf *.egg-info/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

destroy: ## Destroy all infrastructure (use with caution!)
	@echo "⚠️  This will destroy all infrastructure for environment: $(ENV)"
	@echo "Are you sure? This action cannot be undone."
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	@echo "🗑️  Deleting Lightsail container service..."
	@aws lightsail delete-container-service \
		--service-name anchor-alpha-streamlit-$(ENV) \
		--region $(REGION) 2>/dev/null || echo "Container service not found"
	@echo "🗑️  Deleting CloudFormation stack..."
	@aws cloudformation delete-stack \
		--stack-name anchor-alpha-infrastructure-$(ENV) \
		--region $(REGION)
	@echo "⏳ Waiting for stack deletion to complete..."
	@aws cloudformation wait stack-delete-complete \
		--stack-name anchor-alpha-infrastructure-$(ENV) \
		--region $(REGION)
	@echo "✅ Infrastructure destroyed"