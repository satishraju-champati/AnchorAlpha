# AnchorAlpha Makefile

.PHONY: help install test lint format clean build deploy deploy-infra push deploy-dashboard

AWS_ACCOUNT_ID := 013523127218
AWS_REGION     := us-east-1
ECR_REPO       := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/anchoralpha-trading
CFN_STACK      := anchor-alpha-infrastructure-prod
CFN_TEMPLATE   := infrastructure/cloudformation/anchor-alpha-infrastructure.yaml

# Default target
help:
	@echo "Available targets:"
	@echo "  install       - Install dependencies"
	@echo "  test          - Run unit tests"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code with black and isort"
	@echo "  clean         - Clean build artifacts"
	@echo "  build         - Build Lambda deployment package"
	@echo "  deploy        - Deploy Lambda code to AWS"
	@echo "  deploy-infra  - Deploy/update CloudFormation stack (ECS, ECR, IAM, EventBridge)"
	@echo "  push              - Build and push trading bot Docker image to ECR"
	@echo "  deploy-dashboard  - Build and deploy Streamlit dashboard to Lightsail"
	@echo "  dev               - Run Streamlit app locally"

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Run tests
test:
	python -m pytest tst/ -v --cov=src/AnchorAlpha --cov-report=html --cov-report=term

# Run linting
lint:
	flake8 src/ cfg/ --count --statistics
	black --check src/ cfg/
	isort --check-only src/ cfg/
	mypy src/ cfg/ --ignore-missing-imports

# Format code
format:
	black src/ cfg/ tst/
	isort src/ cfg/ tst/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/

# Build Lambda deployment package
build: clean
	mkdir -p build/lambda
	pip install -r requirements.txt -t build/lambda/
	cp -r src/AnchorAlpha build/lambda/
	cp -r cfg build/lambda/
	cd build/lambda && zip -r ../lambda-deployment.zip .

# Deploy Lambda code to AWS
deploy: build
	aws lambda update-function-code \
		--function-name anchoralpha-momentum-processor \
		--zip-file fileb://build/lambda-deployment.zip

# Deploy/update CloudFormation stack (ECS, ECR, IAM, EventBridge)
deploy-infra:
	aws cloudformation deploy \
		--stack-name $(CFN_STACK) \
		--template-file $(CFN_TEMPLATE) \
		--capabilities CAPABILITY_NAMED_IAM \
		--region $(AWS_REGION) \
		--parameter-overrides \
			Environment=prod \
			NotificationEmail=satishraju.info@gmail.com \
			ParameterKey=FMPApiKey,UsePreviousValue=true \
		--no-fail-on-empty-changeset

# Build and push trading bot Docker image to ECR
push:
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	docker build -t anchoralpha-trading .
	docker tag anchoralpha-trading:latest $(ECR_REPO):latest
	docker push $(ECR_REPO):latest
	@echo "Pushed $(ECR_REPO):latest"

# Build and deploy Streamlit dashboard to Lightsail
deploy-dashboard:
	bash scripts/deploy-dashboard.sh

# Run Streamlit app locally
dev:
	streamlit run src/AnchorAlpha/streamlit_app/app.py

# Setup development environment
setup-dev:
	python -m venv venv
	@echo "Activate virtual environment with: source venv/bin/activate"
	@echo "Then run: make install"