# AnchorAlpha - Multi-Tier Large-Cap Momentum Screener

A Python-based momentum screening application that identifies top-performing large-cap US stocks across different market capitalization tiers.

## Project Structure

```
AnchorAlpha/
├── src/AnchorAlpha/           # Main application code
│   ├── models.py              # Core data models
│   ├── api/                   # API clients (FMP, mock data)
│   ├── lambda_function/       # AWS Lambda components
│   ├── streamlit_app/         # Streamlit web app
│   └── utils/                 # Shared utilities
├── cfg/                       # Configuration files
│   └── config.py              # Application configuration
├── tst/AnchorAlpha/           # Unit tests
│   ├── test_models.py         # Model tests
│   ├── test_fmp_client.py     # FMP API client tests
│   └── test_mock_data_provider.py # Mock data provider tests
├── scripts/                   # Development and diagnostic scripts
│   └── README.md              # Script documentation
├── requirements.txt           # Python dependencies
└── .env.example              # Environment variables template
```

## Setup

1. Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

2. Create virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run tests:
   ```bash
   pytest tst/
   ```

## Development

### Running Tests
```bash
# All tests
make test

# Specific test file
pytest tst/AnchorAlpha/test_models.py -v
```

### Code Quality
```bash
# Format code
make format

# Run linting
make lint
```

### API Testing
```bash
# Test with mock data (always works)
pytest tst/AnchorAlpha/test_mock_data_provider.py -v

# Test real API (requires valid API key)
python scripts/manual_fmp_integration_test.py
```

## Configuration

Set your API keys in the `.env` file:
- `FMP_API_KEY`: Financial Modeling Prep API key
- `PERPLEXITY_API_KEY`: Perplexity Sonar API key
- `AWS_REGION`: AWS region for deployment
- `S3_BUCKET`: S3 bucket for data storage

## Architecture

The system uses a serverless architecture:
- **AWS Lambda**: Daily data processing and momentum calculations
- **Amazon S3**: Storage for processed results
- **Streamlit**: Web interface for viewing momentum rankings
- **EventBridge**: Scheduled triggers for data updates