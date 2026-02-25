# AnchorAlpha - Multi-Tier Large-Cap Momentum Screener

A Python-based momentum screening application that identifies top-performing large-cap US stocks across different market capitalization tiers.

## Project Structure

```
AnchorAlpha/
├── src/AnchorAlpha/           # Main application code
│   ├── models.py              # Core data models
│   ├── lambda_function/       # AWS Lambda components
│   ├── streamlit_app/         # Streamlit web app
│   └── utils/                 # Shared utilities
├── cfg/                       # Configuration files
│   └── config.py              # Application configuration
├── tst/AnchorAlpha/           # Unit tests
│   └── test_models.py         # Model tests
├── requirements.txt           # Python dependencies
└── .env.example              # Environment variables template
```

## Setup

1. Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run tests:
   ```bash
   pytest tst/
   ```

## Configuration

Set your API keys in the `.env` file:
- `FMP_API_KEY`: Financial Modeling Prep API key
- `PERPLEXITY_API_KEY`: Perplexity Sonar API key
- `AWS_REGION`: AWS region for deployment
- `S3_BUCKET`: S3 bucket for data storage