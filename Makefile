# AnchorAlpha Makefile

.PHONY: help install test lint format clean build deploy

# Default target
help:
	@echo "Available targets:"
	@echo "  install    - Install dependencies"
	@echo "  test       - Run unit tests"
	@echo "  lint       - Run linting checks"
	@echo "  format     - Format code with black and isort"
	@echo "  clean      - Clean build artifacts"
	@echo "  build      - Build Lambda deployment package"
	@echo "  deploy     - Deploy to AWS"
	@echo "  dev        - Run Streamlit app locally"

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

# Deploy to AWS (requires AWS CLI configured)
deploy: build
	aws lambda update-function-code \
		--function-name anchoralpha-momentum-processor \
		--zip-file fileb://build/lambda-deployment.zip

# Run Streamlit app locally
dev:
	streamlit run src/AnchorAlpha/streamlit_app/app.py

# Setup development environment
setup-dev:
	python -m venv venv
	@echo "Activate virtual environment with: source venv/bin/activate"
	@echo "Then run: make install"