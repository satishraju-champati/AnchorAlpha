# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Set up dev environment
python3 -m venv venv && source venv/bin/activate
make install                  # installs requirements.txt + requirements-dev.txt

# Run all tests with coverage
make test                     # pytest tst/ -v --cov=src/AnchorAlpha

# Run a single test file
pytest tst/AnchorAlpha/test_momentum_engine.py -v

# Lint / format
make lint                     # flake8, black --check, isort --check, mypy
make format                   # black + isort (writes in place)

# Run Streamlit dashboard locally
make dev                      # streamlit run src/AnchorAlpha/streamlit_app/app.py
streamlit run src/AnchorAlpha/streamlit_app/momentum_dashboard.py  # direct

# Run demo with mock data (no API keys needed)
streamlit run src/AnchorAlpha/streamlit_app/demo_interactive_dashboard.py

# Build Lambda deployment zip
make build                    # outputs build/lambda-deployment.zip

# Deploy Lambda to AWS (requires configured AWS CLI)
make deploy
```

Pre-commit hooks run black, isort, flake8, mypy, and standard file checks on every commit. Install with `pre-commit install`.

## Architecture

AnchorAlpha is a two-component serverless app: a **Lambda pipeline** that runs daily and a **Streamlit frontend** that reads from S3.

### Data pipeline (Lambda)

`src/AnchorAlpha/lambda_function/handler.py` is the Lambda entry point. `lambda_handler()` creates a `LambdaOrchestrator` and calls `execute_pipeline()`, which runs eight sequential steps:

1. **Initialize clients** — `LambdaOrchestrator._initialize_clients()` creates `FMPClient` (requires `FMP_API_KEY`) and either `PerplexityClient` (real) or `MockPerplexityClient` via `PerplexityFactory` (when `PERPLEXITY_API_KEY` is absent).
2. **Fetch stocks** — `api/fmp_client.py::FMPClient.get_large_cap_stocks()` calls FMP `/stable/profile` and `/stable/quote` for ~60 hardcoded large-cap symbols. Returns a list of `Stock` objects.
3. **Price changes** — `FMPClient.get_price_changes(ticker)` calls the `/stable/stock-price-change/{ticker}` endpoint (not historical OHLCV). Returns percentage changes for keys `5D`, `1M`, `3M` which are then back-calculated into implied historical prices.
4. **Momentum calculation** — `momentum_engine.py::MomentumEngine.process_stock_batch()` computes 7d/30d/60d/90d returns as `(current_price / price_n_ago) - 1`. Capped at +1000% / floored at -90%.
5. **Tier ranking** — `MomentumEngine.get_comprehensive_rankings()` produces `{tier: {window: [top_stocks]}}` — a nested dict over 4 market-cap tiers × 4 time windows, top 20 stocks each.
6. **AI summaries** — Top 5 unique stocks per tier/timeframe get a natural-language summary via `PerplexityClient.generate_stock_summary()`. Stored as `stock.ai_summary`.
7. **Storage** — `storage/data_pipeline.py::MomentumDataPipeline.process_and_store_momentum_data()` serialises ranked data to JSON and calls `storage/s3_client.py::S3DataStorage.upload_momentum_data()` → S3 path `momentum-data/YYYY-MM-DD/processed_data.json`.
8. **Metrics & notifications** — `LambdaOrchestrator._publish_final_metrics()` pushes CloudWatch metrics, saves an API usage report to S3, and sends SNS alerts on failure.

### Streamlit frontend

`streamlit_app/momentum_dashboard.py` is the main dashboard. `streamlit_app/app.py` is the entry point that patches `sys.path` so relative imports work when launched from the repo root.

The dashboard delegates to:
- `data_loader.py::StreamlitDataLoader` — fetches JSON from S3 (`@st.cache_data TTL=300s`); falls back gracefully when S3 is unavailable.
- `cache_manager.py` — supplemental caching utilities for the frontend.
- `data_transforms.py` — formats momentum percentages and builds pandas DataFrames for display.
- `ui_components.py` — renders tier tabs, stock cards, momentum charts, timeframe selectors.
- `styling.py` — injects CSS for colour themes and card styles.

### Utilities

`utils/logging_utils.py` — `StructuredLogger` (JSON-structured logging with execution IDs, API call timers, S3 op logging), `CloudWatchMetricsPublisher` (publishes execution + rate-limit metrics), `SNSNotificationManager` (critical error alerts).

`utils/api_monitoring.py` — `get_api_monitor()` singleton that tracks per-API rate-limit windows and call counts; exposes `check_rate_limit(api_name)`, `publish_metrics_to_cloudwatch()`, and `save_usage_report_to_s3()`.

### Configuration

`cfg/config.py::Config` is the single source of truth for tunable constants. Key values:

| Setting | Default | Env var override |
|---|---|---|
| `FMP_BASE_URL` | `https://financialmodelingprep.com/stable` | — |
| `AWS_REGION` | `us-east-1` | `AWS_REGION` |
| `S3_BUCKET` | `anchoralpha-data` | `S3_BUCKET` |
| `FMP_REQUESTS_PER_MINUTE` | 300 | — |
| `PERPLEXITY_REQUESTS_PER_MINUTE` | 60 | — |
| `TOP_PERFORMERS_COUNT` | 20 | — |

Copy `config/environment.template.env` to `.env` for local development. Required env vars: `FMP_API_KEY`. Optional: `PERPLEXITY_API_KEY`, `AWS_REGION`, `S3_BUCKET`.

### Core models

`models.py` defines two dataclasses:
- `Stock` — ticker, company_name, current_price, market_cap, momentum_7d/30d/60d/90d, ai_summary. Raises on market_cap < $10B or price ≤ 0. `get_tier()` returns tier key; `get_momentum(days)` returns the matching field.
- `MomentumCalculation` — ticker, current_price, historical_prices dict. `calculate_momentum(days)` returns `(current/historical) - 1` capped to [-0.9, 10.0].

### Market-cap tiers

| Tier key | Range |
|---|---|
| `100B_200B` | $100B – $200B |
| `200B_500B` | $200B – $500B |
| `500B_1T` | $500B – $1T |
| `1T_plus` | $1T+ |

Minimum qualifying market cap is $10B (enforced in both `Stock.__post_init__()` and `MomentumEngine.calculate_stock_momentum()`).

### AWS infrastructure

Defined in `infrastructure/cloudformation/anchor-alpha-infrastructure.yaml`. Key resources:
- **EventBridge** cron triggers Lambda Mon–Fri at 4:30 PM EST.
- **S3 bucket** `anchor-alpha-momentum-data-prod` with 90-day lifecycle and AES-256 encryption.
- **Secrets Manager** holds API keys injected as Lambda env vars.
- **Lightsail container** serves the Streamlit app on port 8501.
- **CloudWatch alarms** → SNS email on Lambda errors or duration > 10 min.
- **SQS dead-letter queue** captures failed Lambda invocations (14-day retention).
- **Budget** capped at $10/month.

### Tests

Tests live in `tst/AnchorAlpha/`. Most unit tests use `moto` to mock AWS. Integration tests (prefixed `*_integration*.py` or `*_manual*.py`) hit real APIs and require valid env vars — do not run in CI without credentials. `tst/AnchorAlpha/README_INTEGRATION_TESTS.md` documents which tests need what.

Key test files:
- `test_momentum_engine.py` — unit tests for tier categorization, ranking, cross-timeframe leaders
- `test_models.py` — `Stock` and `MomentumCalculation` validation
- `test_fmp_client.py` — FMP client with mocked HTTP responses
- `test_s3_client.py` — S3 operations with moto
- `test_data_pipeline.py` — end-to-end pipeline with mocked dependencies
- `test_lambda_handler_integration.py` — full Lambda handler integration test
