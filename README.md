# AnchorAlpha - AI-Powered Swing Trading Platform

An algorithmic swing trading platform that combines momentum screening with AI-scored dip detection across large-cap AI sector stocks. Runs a paper trading research engine to validate strategies before going live.

## 🚀 Quick Start

### Prerequisites

- AWS Account with CLI configured (`aws configure`)
- Docker installed
- Python 3.11+
- [Financial Modeling Prep](https://financialmodelingprep.com/developer/docs) API key (Starter plan)
- [Anthropic](https://console.anthropic.com) API key
- [Alpaca](https://alpaca.markets) paper trading account

### Deploy

```bash
make deploy-infra      # CloudFormation: ECS, ECR, IAM, EventBridge
make push              # Build & push trading engine Docker image to ECR
make deploy-dashboard  # Deploy Streamlit dashboard to Lightsail
```

## 🏗️ Architecture

```
  anchoralpha.com  (Namecheap → Lightsail SSL)
        │
        ▼
  ┌─────────────────────────────────────────────┐
  │         Lightsail — Streamlit Dashboard      │
  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
  │  │Momentum  │  │Research  │  │   Live    │  │
  │  │   Tab    │  │  Tab     │  │   Tab     │  │
  │  └──────────┘  └──────────┘  └───────────┘  │
  └─────────────────────────────────────────────┘
        │ reads                        │ reads
        ▼                              ▼
  ┌───────────┐                 ┌────────────────┐
  │  S3 Bucket│                 │  S3 Bucket     │
  │momentum-  │                 │research/       │
  │data/      │                 │  configs/      │
  └───────────┘                 │  positions/    │
        ▲                       │  trades/       │
        │ writes                └────────────────┘
        │                              ▲ writes
  ┌─────────────────┐          ┌───────────────────────────────────┐
  │   EventBridge   │          │  EventBridge (Mon–Fri 8:30 AM ET) │
  │ (Mon–Fri 4:30PM)│          └───────────────────────────────────┘
  └─────────────────┘                         │ starts
        │ triggers                            ▼
        ▼                       ┌─────────────────────────┐
  ┌──────────────────┐          │   ECS Fargate Task      │
  │  Lambda Function │          │  ┌───────────────────┐  │
  │  (Momentum       │          │  │  Research Loop    │  │
  │   Pipeline)      │          │  │  8 paper configs  │  │
  └──────────────────┘          │  └───────────────────┘  │
        │ calls                 │  ┌───────────────────┐  │
        ▼                       │  │  Live Loop        │  │
  ┌──────────────────┐          │  │  (Month 4+)       │  │
  │  FMP API         │          │  └───────────────────┘  │
  │  (stock data)    │          └─────────────────────────┘
  └──────────────────┘                    │ calls
                                          ▼
                            ┌─────────────────────────────┐
                            │       External APIs          │
                            │  FMP API  — price/news/data  │
                            │  Claude   — AI stock scoring │
                            │  Alpaca   — paper orders     │
                            │  AlphaVantage — earnings     │
                            └─────────────────────────────┘
                                          │
                            ┌─────────────────────────────┐
                            │  SNS → Email                 │
                            │  Daily trading summary       │
                            │  sent at market close        │
                            └─────────────────────────────┘
```

### How It Works

**Momentum Pipeline** (existing, runs daily):
- EventBridge fires Mon–Fri at 4:30 PM ET → Lambda fetches FMP data → ranks stocks by momentum across 4 market-cap tiers → stores to S3 → Momentum tab reads it

**Trading Engine** (new, runs during market hours):
- EventBridge fires Mon–Fri at 8:30 AM ET → starts ECS Fargate task
- Every 5 minutes during market hours (9:30 AM – 4:30 PM ET):
  - Fetches price history for 38 AI-sector stocks (once, cached across all configs)
  - Detects dips ≥ 10% from 10-day high
  - For dip candidates above $200B market cap → scores with Claude AI (Haiku for research)
  - Score ≥ threshold → places bracket order on Alpaca paper account
  - At market close → sends daily summary email via SNS → task exits

**Dashboard** (always on):
- Research tab — view paper trading configs, open positions, trade history
- Live tab — admin-gated, manage real-money profiles (Month 4+)

### AWS Components

| Component | Purpose | Cost/mo |
|---|---|---|
| Lightsail (nano) | Streamlit dashboard at anchoralpha.com | $7 |
| ECS Fargate | Trading engine (market hours only) | ~$9 |
| Lambda | Nightly momentum pipeline | ~$1 |
| S3 | All data storage | ~$1 |
| Secrets Manager | API keys (FMP, Claude, Alpaca, etc.) | ~$2 |
| ECR + EventBridge | Container registry + scheduling | ~$0.15 |
| SNS | Daily email summary | ~$0 |
| **Total** | | **~$20/mo** |

### Universe

39 large-cap AI sector stocks across semiconductors, cloud, SaaS, networking, and infrastructure:

`NVDA AMD INTC AVGO QCOM MU AMAT LRCX KLAC MRVL MSFT GOOGL AMZN META AAPL TSLA TSM ASML ARM ORCL CRM SNOW PLTR DDOG NET ZS ANET CSCO SMCI DELL HPE CRWV AI SOUN BBAI PANW CRWD`

**Entry criteria:** dip ≥ 10% from 10-day high + market cap ≥ $200B (paper) / $800B (live) + Claude score ≥ threshold + SPY & SOXX above 200-day MA

**Exit criteria:** +20% take-profit, -10% stop-loss, 20-day max hold, or Friday re-score below threshold

## 📋 Project Structure

```
AnchorAlpha/
├── src/AnchorAlpha/
│   ├── trading/                   # Trading engine (ECS Fargate)
│   │   ├── trading_engine.py      # Main loop — research + live
│   │   ├── claude_scorer.py       # Claude AI stock scoring
│   │   ├── alpaca_client.py       # Broker: orders, positions
│   │   ├── dip_detector.py        # 10-day high drawdown detection
│   │   ├── order_manager.py       # TP/SL logic, trade logging
│   │   ├── position_manager.py    # Open position registry
│   │   ├── earnings_guard.py      # Earnings calendar blocks
│   │   ├── config_manager.py      # S3 config read/write
│   │   └── secrets.py             # Secrets Manager loader
│   ├── streamlit_app/             # Dashboard (Lightsail)
│   │   ├── app.py                 # 3-tab entry point
│   │   ├── momentum_dashboard.py  # Momentum tab
│   │   ├── research_dashboard.py  # Research (paper trading) tab
│   │   └── live_dashboard.py      # Live tab (admin-gated)
│   ├── lambda_function/           # Nightly momentum pipeline
│   ├── api/                       # FMP client
│   └── models.py                  # Core data models
├── infrastructure/cloudformation/ # All AWS resources as code
├── scripts/
│   └── deploy-dashboard.sh        # Lightsail deployment
├── Dockerfile                     # Trading engine image
├── Dockerfile.streamlit           # Dashboard image
├── Makefile                       # push / deploy-dashboard / deploy-infra
└── requirements.txt
```

## 🚀 Deployment

```bash
# 1. Deploy / update AWS infrastructure
make deploy-infra

# 2. Build & push trading engine to ECR (linux/amd64 required for ECS)
make push

# 3. Deploy Streamlit dashboard to Lightsail
make deploy-dashboard

# 4. Run dashboard locally
make dev
```

## 📊 Monitoring

```bash
# View trading engine logs (CloudWatch)
aws logs tail /ecs/anchoralpha-trading --follow --region us-east-1

# View Lambda momentum pipeline logs
aws logs tail /aws/lambda/anchor-alpha-momentum-processor-prod --follow --region us-east-1

# Check running ECS tasks
aws ecs list-tasks --cluster anchoralpha --region us-east-1

# Enable / disable trading schedule
aws scheduler update-schedule --name anchoralpha-start-trading-prod --state ENABLED  # or DISABLED
```

## 🔧 Development

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp config/environment.template.env .env
# Edit .env with your API keys

# Run tests
pytest tst/ -v
```

### Running Tests

```bash
# All tests
make test

# Specific test categories
pytest tst/AnchorAlpha/test_momentum_engine.py -v
pytest tst/AnchorAlpha/test_fmp_client.py -v
pytest tst/AnchorAlpha/test_streamlit_integration.py -v

# Integration tests
pytest tst/AnchorAlpha/test_end_to_end_integration.py -v
```

### Local Streamlit Development

```bash
# Run Streamlit app locally
streamlit run src/AnchorAlpha/streamlit_app/momentum_dashboard.py

# Or use the demo with mock data
streamlit run src/AnchorAlpha/streamlit_app/demo_interactive_dashboard.py
```

## ⚙️ Configuration

### Secrets Manager Keys

| Secret Name | Keys | Used By |
|---|---|---|
| `anchor-alpha/fmp-api-key-prod` | (plain string) | Lambda + Trading engine |
| `anchoralpha/claude` | `CLAUDE_API_KEY` | Trading engine |
| `anchoralpha/alpaca-paper` | `ALPACA_KEY`, `ALPACA_SECRET` | Trading engine |
| `anchoralpha/alpaca-live` | `ALPACA_KEY`, `ALPACA_SECRET` | Trading engine (Month 4+) |
| `anchoralpha/alphavantage` | `ALPHAVANTAGE_API_KEY` | Trading engine |
| `anchoralpha/dashboard` | `ADMIN_PASSWORD` | Streamlit Live tab |

### Trading Parameters (per research config)

| Parameter | Default | Description |
|---|---|---|
| Score threshold | 0.60 – 0.75 | Claude AI score to enter |
| Dip threshold | 10% | Drawdown from 10-day high |
| Take profit | +20% | Auto-exit gain |
| Stop loss | -10% | Auto-exit loss |
| Max hold | 20 days | Maximum position age |
| Max positions | 5 | Per config simultaneously |
| Market cap (paper) | ≥ $200B | Entry filter |
| Market cap (live) | ≥ $800B | Entry filter |

## 🔒 Security

- API keys stored in AWS Secrets Manager
- IAM roles with least-privilege access
- S3 bucket encryption enabled
- VPC endpoints for internal communication
- Regular security audits and updates

## 💰 Cost Management

- **Budget Control**: $10/month limit with alerts
- **Resource Optimization**: Nano Lightsail instances
- **Data Lifecycle**: 90-day S3 retention policy
- **Monitoring**: Real-time cost tracking and alerts

## 🐛 Troubleshooting

For common issues and solutions, see:
- **[Deployment Guide](DEPLOYMENT_README.md)** - Complete setup instructions
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and fixes
- **[Infrastructure Guide](infrastructure/README.md)** - AWS infrastructure details

### Quick Diagnostics

```bash
# Health check
./scripts/health-check.sh prod

# View recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/anchor-alpha-momentum-processor-prod \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s) - 3600))000

# Check S3 data
aws s3 ls s3://anchor-alpha-momentum-data-prod-$(aws sts get-caller-identity --query Account --output text)/
```

## 📚 Documentation

- **[DEPLOYMENT_README.md](DEPLOYMENT_README.md)** - Comprehensive deployment guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Issue resolution guide
- **[infrastructure/README.md](infrastructure/README.md)** - Infrastructure documentation
- **[scripts/README.md](scripts/README.md)** - Development scripts guide

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `pytest tst/ -v`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues or questions:
1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review CloudWatch logs for error details
3. Verify configuration and API keys
4. Check AWS service status and limits