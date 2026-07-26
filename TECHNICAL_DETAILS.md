# AnchorAlpha Trading Bot — Technical Details

Last updated: 2026-07-26

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Cloud | AWS (us-east-1) |
| Infrastructure as Code | AWS CloudFormation |
| Compute (trading engine) | ECS Fargate (1 task, 0.5 vCPU, 1 GB RAM) |
| Compute (nightly pipeline) | AWS Lambda (Python 3.11, 1 GB RAM) |
| Dashboard | Streamlit on AWS Lightsail (Nano, 512 MB) |
| Container Registry | AWS ECR |
| Storage | AWS S3 |
| Secrets | AWS Secrets Manager |
| Scheduling | AWS EventBridge Scheduler |
| Monitoring | AWS CloudWatch + SNS |
| Broker | Alpaca (paper trading) |
| Scoring AI | Anthropic Claude API |
| Market Data | Financial Modeling Prep (FMP) |
| Earnings Calendar | Alpha Vantage (free tier) |

---

## AWS Account Details

| Detail | Value |
|---|---|
| Account ID | `013523127218` |
| Region | `us-east-1` |
| S3 Bucket | `anchor-alpha-momentum-data-prod-013523127218` |
| CloudFormation Stack | `anchor-alpha-infrastructure-prod` |
| ECS Cluster | `anchoralpha` |
| ECR Repository | `anchoralpha-trading` |
| Lightsail Service | `anchoralpha-dashboard` |
| VPC | `vpc-1651da6c` (default VPC) |
| Subnets | `subnet-c70c49e9`, `subnet-2389b82c`, `subnet-0f404e45` |

---

## AWS Secrets Manager

All API keys stored in Secrets Manager. Secret names and key structure:

| Secret Name | JSON Keys | Used By |
|---|---|---|
| `anchor-alpha/fmp-api-key-prod` | plain string (bare API key) | Lambda + Fargate |
| `anchoralpha/claude` | `CLAUDE_API_KEY` | Fargate trading engine |
| `anchoralpha/alpaca-paper` | `ALPACA_KEY`, `ALPACA_SECRET` | Fargate trading engine |
| `anchoralpha/alphavantage` | `ALPHAVANTAGE_API_KEY` | Fargate trading engine |
| `anchoralpha/dashboard` | `ADMIN_PASSWORD` | Streamlit Live tab |

> Note: The FMP secret was created by CloudFormation as a plain string (not JSON). The secrets loader handles both plain string and JSON formats automatically.

---

## ECS Fargate Task

### Task Definition

| Setting | Value |
|---|---|
| Family | `anchoralpha-trading` |
| CPU | 512 (0.5 vCPU) |
| Memory | 1024 MB (1 GB) |
| Network mode | `awsvpc` |
| Launch type | `FARGATE` |
| Container image | `013523127218.dkr.ecr.us-east-1.amazonaws.com/anchoralpha-trading:latest` |

### Environment Variables (injected by task definition)

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `prod` |
| `S3_BUCKET` | `anchor-alpha-momentum-data-prod-013523127218` |
| `AWS_DEFAULT_REGION` | `us-east-1` |
| `CLAUDE_SECRET_NAME` | `anchoralpha/claude` |
| `ALPACA_PAPER_SECRET_NAME` | `anchoralpha/alpaca-paper` |
| `ALPHAVANTAGE_SECRET_NAME` | `anchoralpha/alphavantage` |
| `FMP_SECRET_NAME` | `anchor-alpha/fmp-api-key-prod` |
| `DASHBOARD_SECRET_NAME` | `anchoralpha/dashboard` |
| `ALPACA_PAPER_BASE_URL` | `https://paper-api.alpaca.markets/v2` |

### IAM Roles

**Execution Role** (`AnchorAlpha-ECS-ExecutionRole-prod`):
- `AmazonECSTaskExecutionRolePolicy` (managed) — pull ECR image, write CloudWatch logs
- `secretsmanager:GetSecretValue` on `anchoralpha/*` and `anchor-alpha/*`

**Task Role** (`AnchorAlpha-ECS-TaskRole-prod`):
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on data bucket
- `secretsmanager:GetSecretValue` on `anchoralpha/*` and `anchor-alpha/*`
- `logs:CreateLogStream`, `logs:PutLogEvents` on `/ecs/anchoralpha-trading`

### Schedule

| Schedule | Time | Action |
|---|---|---|
| `anchoralpha-start-trading-prod` | 8:30 AM ET, Mon–Fri | ECS RunTask |
| Self-shutdown | 4:30 PM ET | Task checks time and exits loop |

---

## S3 Data Structure

```
s3://anchor-alpha-momentum-data-prod-013523127218/
│
├── momentum-data/                        ← existing nightly Lambda output
│   └── YYYY-MM-DD/
│       └── processed_data.json
│
├── research/
│   ├── configs/
│   │   ├── config_1.json                 ← ResearchConfig JSON
│   │   └── ...config_8.json
│   ├── positions/
│   │   └── {config_id}/open.json         ← open paper positions per config
│   ├── trades/
│   │   └── {config_id}/YYYY-MM-DD/{ticker}.json
│   └── scores/
│       └── {config_id}/YYYY-MM-DD/{ticker}.json
│
└── live/
    ├── configs/
    │   └── {profile_id}.json             ← LiveProfile JSON
    ├── positions/
    │   └── open.json                     ← global open position registry
    ├── trades/
    │   └── {profile_id}/YYYY-MM-DD/{ticker}.json
    └── global_settings.json              ← emergency stop, market filter
```

---

## Source Code Structure

```
src/AnchorAlpha/
├── trading/                              ← NEW: trading bot module
│   ├── __init__.py
│   ├── secrets.py                        ← loads all API keys from Secrets Manager
│   ├── claude_scorer.py                  ← Claude API scoring (Haiku/Sonnet)
│   ├── alpaca_client.py                  ← Alpaca broker (orders, positions, quotes)
│   ├── dip_detector.py                   ← 10-day high drawdown detection
│   ├── config_manager.py                 ← S3 config read/write, seeds defaults
│   ├── earnings_guard.py                 ← Alpha Vantage earnings calendar
│   ├── position_manager.py               ← S3 position registry, conflict check
│   ├── order_manager.py                  ← exit logic, trade logging, analytics
│   └── trading_engine.py                 ← main loop (research + live)
│
├── api/
│   └── fmp_client.py                     ← existing FMP client (nightly Lambda)
│
├── lambda_function/
│   └── handler.py                        ← existing nightly Lambda entry point
│
├── streamlit_app/                        ← 3-tab unified dashboard
│   ├── app.py                            ← entry point: set_page_config + 3 tabs
│   ├── momentum_dashboard.py             ← Tab 1: existing momentum screener
│   ├── research_dashboard.py             ← Tab 2: paper trading configs, analytics
│   ├── live_dashboard.py                 ← Tab 3: live profiles, P&L, admin controls
│   ├── styling.py                        ← dark/black professional theme CSS
│   ├── data_loader.py                    ← S3 data loading with cache
│   └── ...
│
├── momentum_engine.py                    ← existing momentum calculations
├── models.py                             ← existing Stock / MomentumCalculation
└── storage/
    └── s3_client.py                      ← existing S3 operations
```

---

## API Integrations

### FMP (Financial Modeling Prep)

- **Base URL:** `https://financialmodelingprep.com/stable`
- **Plan:** Starter ($29/month, 300 req/min)
- **Auth:** `?apikey={key}` query parameter on every request
- **Important:** Ticker symbol always passed as `?symbol=TICKER` query param, NOT as a path segment

| Endpoint | Method | Purpose |
|---|---|---|
| `/quote?symbol=NVDA` | GET | Current price, volume |
| `/profile?symbol=NVDA` | GET | Market cap (`marketCap`), sector, company name |
| `/historical-price-eod/full?symbol=NVDA&timeseries=15` | GET | Daily closing prices for dip detection |
| `/stock-price-change?symbol=NVDA` | GET | 1D, 5D, 1M, 3M momentum |
| `/news/stock?tickers=NVDA&limit=5` | GET | Recent news headlines |
| `/analyst-stock-ratings?symbol=NVDA` | GET | Buy/hold/sell consensus |
| `/income-statement?symbol=NVDA&limit=2` | GET | Revenue + EPS trend |
| `/company-screener` | GET | Bulk stock screener (existing Lambda) |

> **Field name**: Market cap is `marketCap` (not `mktCap`) in `/stable/profile` response.

---

### Claude API (Anthropic)

- **Models:**
  - Research configs: `claude-haiku-4-5` (faster, cheaper)
  - Live profiles: `claude-sonnet-4-6` (higher quality)
- **Max tokens:** 512 output
- **Auth:** `anthropic.Anthropic(api_key=key)`

**Input (11 signals):**

| # | Signal | FMP Source |
|---|---|---|
| 1 | Momentum 7d/30d/60d/90d | `stock-price-change` |
| 2 | Volume anomaly vs 20-day avg | `historical-price-eod/full` |
| 3 | News sentiment (5 headlines) | `news/stock` |
| 4 | Analyst consensus | `analyst-stock-ratings` |
| 5 | Revenue trend (2 quarters YoY) | `income-statement` |
| 6 | Earnings trend (EPS beat/miss) | `income-statement` |
| 7 | Relative strength vs SPY | `stock-price-change` |
| 8 | Distance from 52-week high | `profile` (range field) |
| 9 | Market cap tier | `profile` (marketCap field) |
| 10 | Sector ETF momentum | `stock-price-change` (SPY/SOXX/XLK) |
| 11 | Insider activity (net buy/sell) | `income-statement` proxy |

**Output JSON schema:**
```json
{
  "score": 0.82,
  "confidence": "high",
  "buy_signal": true,
  "key_positives": ["Strong revenue growth", "Analyst upgrades"],
  "key_risks": ["Near 52-week high"],
  "reasoning": "One paragraph explanation."
}
```

---

### Alpaca (Broker)

- **One account, two environments:**

| Environment | Base URL | Keys |
|---|---|---|
| Paper trading | `https://paper-api.alpaca.markets/v2` | `ALPACA_KEY`, `ALPACA_SECRET` from `anchoralpha/alpaca-paper` |
| Live trading | `https://api.alpaca.markets/v2` | Not yet created (Month 4) |
| Market data | `https://data.alpaca.markets/v2` | Same keys as above |

- **Auth:** HTTP headers `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`
- **Strategy:** Polling (not webhooks) — no inbound connectivity required

| Endpoint | Method | Purpose |
|---|---|---|
| `/account` | GET | Portfolio value, buying power |
| `/positions` | GET | All open positions |
| `/positions/{ticker}` | GET | Single position |
| `/positions/{ticker}` | DELETE | Close position (market sell) |
| `/orders` | POST | Place bracket order (entry + TP + SL) |
| `/orders/{id}` | GET | Check order status |
| `/clock` | GET | Market open/closed status |
| `data.alpaca.markets/v2/stocks/quotes/latest?symbols=NVDA` | GET | Real-time ask price |

**Bracket order structure:**
```json
{
  "symbol": "NVDA",
  "qty": "10",
  "side": "buy",
  "type": "market",
  "time_in_force": "day",
  "order_class": "bracket",
  "take_profit": {"limit_price": "233.79"},
  "stop_loss": {"stop_price": "175.35"}
}
```

---

### Alpha Vantage (Earnings Calendar)

- **Base URL:** `https://www.alphavantage.co/query`
- **Plan:** Free (25 calls/day — sufficient, we check weekly)
- **Auth:** `?apikey={key}` query parameter

| Endpoint | Params | Purpose |
|---|---|---|
| `EARNINGS_CALENDAR` | `symbol=NVDA&horizon=3month` | Next earnings date |

Response: CSV format — `symbol, name, reportDate, fiscalDateEnding, estimate, currency`

---

## Config Schemas

### ResearchConfig (stored in `research/configs/{id}.json`)

```json
{
  "config_id": "config_1",
  "name": "AI Semis — Low (0.60)",
  "active": true,
  "sectors": ["AI/Semiconductors"],
  "score_threshold": 0.60,
  "max_positions": 5,
  "capital_pct": 30.0,
  "take_profit_pct": 20.0,
  "stop_loss_pct": 10.0,
  "max_hold_days": 20,
  "earnings_protection": true,
  "dip_threshold_pct": 10.0,
  "use_sonnet": false
}
```

### LiveProfile (stored in `live/configs/{id}.json`)

```json
{
  "profile_id": "ai_core",
  "name": "AI Core",
  "sector": "AI/Semiconductors",
  "active": true,
  "capital_usd": 50000.0,
  "score_threshold": 0.75,
  "max_positions": 5,
  "take_profit_pct": 20.0,
  "stop_loss_pct": 10.0,
  "max_hold_days": 20,
  "earnings_protection": true,
  "use_sonnet": true
}
```

### GlobalSettings (stored in `live/global_settings.json`)

```json
{
  "emergency_stop": false,
  "market_filter_active": true,
  "spy_ma_days": 200,
  "soxx_ma_days": 200
}
```

### OpenPosition (stored in `research/positions/{config_id}/open.json` or `live/positions/open.json`)

```json
{
  "ticker": "NVDA",
  "profile_id": "config_1",
  "mode": "research",
  "entry_price": 194.83,
  "qty": 25.66,
  "entry_date": "2026-07-05",
  "alpaca_order_id": "abc123",
  "take_profit_pct": 20.0,
  "stop_loss_pct": 10.0,
  "max_hold_days": 20,
  "score_at_entry": 0.82,
  "consecutive_down_score_days": 0
}
```

---

## Trading Logic

### Entry Rules (all must pass)

```
1. Market filter:        SPY AND SOXX both above 200-day MA
2. Market cap filter:    Paper trading: market cap >= $500B
                         Live trading:  market cap >= $800B
                         (fetched live from FMP /profile each cycle)
3. Score threshold:      Claude score >= config.score_threshold (e.g. 0.75)
4. Dip detected:         Stock drawdown >= -10% from 10-day high
5. Dip confirmed:
     Single-day:         Day+1 additional drop is 0% to -5% (deceleration)
     Multi-day:          Most recent day's drop decelerates vs average daily drop
6. Earnings protection:  No earnings within 3 days
7. Position limit:       Open positions < max_positions for this config/profile
8. Conflict check:       (Live only) No other live profile holds this ticker
```

### Exit Rules (checked every 5 minutes, in priority order)

```
1. Stop-loss:            P&L <= -stop_loss_pct from entry    → exit immediately
2. Take-profit:          P&L >= +take_profit_pct from entry  → exit immediately
   (per-position values from config/profile, e.g. -10% / +20%)
3. Score decline:        Claude score declined 3 consecutive days → exit
4. Max hold:             Age >= max_hold_days AND score < threshold → exit
5. Friday review:        Score < threshold OR P&L < 0 OR age >= 18 days → exit
   (3:30 PM ET Fri)      Score >= threshold AND P&L >= 0 AND age < 18 → hold weekend
6. Earnings pre-close:   Earnings within 2 days              → exit
```

### Dip Detection Algorithm

```python
# 1. Get last 11+ daily closing prices (oldest first, today last)
# 2. Calculate 10-day high from window[-11:-1]
# 3. Drawdown = (today - 10d_high) / 10d_high
# 4. If drawdown < -10%: dip detected

# Single-day dip:
#   yesterday-to-today drop >= -10%
#   Confirmed if: day+1 drop is between 0% and -5%

# Multi-day dip:
#   Gradual decline over multiple days totalling >= -10%
#   Confirmed if: most recent day's drop < average daily drop (deceleration)
```

---

## Default Research Configs (8 configs, seeded on first run)

| Config | Sector | Score Threshold |
|---|---|---|
| config_1 | AI/Semiconductors | 0.60 |
| config_2 | AI/Semiconductors | 0.75 |
| config_3 | Cloud/SaaS | 0.60 |
| config_4 | Cloud/SaaS | 0.75 |
| config_5 | Fintech | 0.75 |
| config_6 | Healthcare/Biotech | 0.75 |
| config_7 | Energy | 0.75 |
| config_8 | Broad Large-cap | 0.65 |

All configs: TP +20%, SL -10%, max 5 positions, 30% capital, 20-day max hold, earnings protection ON.

---

## Stock Universe (~35 large-cap AI sector stocks)

```python
AI_SECTOR_STOCKS = [
    # Semiconductors
    "NVDA", "AMD", "INTC", "AVGO", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "MRVL",
    # Cloud / Hyperscalers
    "MSFT", "GOOGL", "AMZN", "META", "AAPL",
    # Chip manufacturers / Equipment
    "TSM", "ASML", "ARM",
    # Enterprise AI / SaaS
    "ORCL", "CRM", "SNOW", "PLTR", "DDOG", "NET", "ZS",
    # Networking
    "ANET", "CSCO",
    # Data center infrastructure
    "SMCI", "DELL", "HPE",
    # AI pure-plays
    "AI", "SOUN", "BBAI",
    # Cybersecurity AI
    "PANW", "CRWD",
]
```

---

## Deployment Commands

```bash
# Install dependencies
make install

# Run all tests
make test

# Run API connection tests
venv/bin/python tst/test_api_connections.py

# Deploy CloudFormation (ECS, ECR, IAM, EventBridge)
make deploy-infra

# Build + push trading engine Docker image to ECR
make push

# Build + deploy Streamlit dashboard to Lightsail
make deploy-dashboard

# Deploy Lambda code update (nightly momentum pipeline)
make deploy

# Run dashboard locally
make dev
```

---

## Monthly Cost Breakdown

| Component | Cost |
|---|---|
| AWS Lightsail (dashboard) | $7 |
| AWS ECS Fargate (1 task, Mon–Fri market hours only) | ~$9 |
| AWS Lambda (nightly momentum pipeline) | ~$0.50 |
| AWS S3 (data storage) | ~$1 |
| AWS Secrets Manager (5 secrets) | ~$2 |
| AWS CloudWatch (logs) | ~$1 |
| AWS ECR (Docker images) | ~$0.15 |
| AWS EventBridge (schedules) | ~$0 |
| FMP API — Starter plan | $29 |
| Claude API — Haiku (research) + Sonnet (live) | ~$43 |
| Alpha Vantage — free tier | $0 |
| Alpaca — paper + live trading | $0 |
| **Total (paper trading phase)** | **~$75/month** |
| **Total (paper + live trading)** | **~$93/month** |

---

## Key Files Reference

| File | Purpose |
|---|---|
| `TRADING_BOT_DISCUSSION.md` | Full strategy spec and decision log |
| `IMPLEMENTATION_PLAN.md` | Build plan, prerequisites, delivery sequence |
| `TECHNICAL_DETAILS.md` | This file — all technical implementation details |
| `infrastructure/cloudformation/anchor-alpha-infrastructure.yaml` | All AWS resources as code |
| `Dockerfile` | Container image for trading engine |
| `Makefile` | Build, deploy, push commands |
| `src/AnchorAlpha/trading/trading_engine.py` | Main loop: research + live, market filter |
| `src/AnchorAlpha/trading/claude_scorer.py` | Claude API scoring (Haiku/Sonnet) |
| `src/AnchorAlpha/trading/alpaca_client.py` | Alpaca broker (orders, positions, quotes) |
| `src/AnchorAlpha/trading/dip_detector.py` | 10-day high drawdown detection |
| `src/AnchorAlpha/trading/config_manager.py` | S3 config management + 8 default seeds |
| `src/AnchorAlpha/trading/earnings_guard.py` | Alpha Vantage earnings calendar |
| `src/AnchorAlpha/trading/position_manager.py` | Position registry + global conflict check |
| `src/AnchorAlpha/trading/order_manager.py` | Exit rules (per-position TP/SL) + trade log |
| `src/AnchorAlpha/trading/secrets.py` | Secrets Manager loader (paper + optional live) |
| `src/AnchorAlpha/streamlit_app/app.py` | 3-tab dashboard entry point |
| `src/AnchorAlpha/streamlit_app/momentum_dashboard.py` | Tab 1: momentum screener |
| `src/AnchorAlpha/streamlit_app/research_dashboard.py` | Tab 2: paper configs, trade log |
| `src/AnchorAlpha/streamlit_app/live_dashboard.py` | Tab 3: live profiles, admin panel |
| `src/AnchorAlpha/streamlit_app/styling.py` | Dark/black professional theme CSS |
| `scripts/deploy-dashboard.sh` | Lightsail deploy (injects ADMIN_PASSWORD) |
| `tst/test_api_connections.py` | API connection tests (15/15 passing) |

---

## Build Status

| Item | Status |
|---|---|
| CloudFormation (ECS, ECR, IAM, EventBridge) | ✅ Deployed — `anchor-alpha-infrastructure-prod` |
| Trading engine Docker image in ECR | ✅ Pushed — `anchoralpha-trading:latest` |
| Research loop (8 paper configs, Haiku scoring) | ✅ Done |
| Live loop (market filter, conflict check, Sonnet scoring) | ✅ Done — activates when live Alpaca keys added |
| Streamlit 3-tab dashboard | ✅ Live — Lightsail deployment 13 |
| Research tab (configs, controls, trade log, Promote) | ✅ Done |
| Live tab (profiles, P&L, admin login, capital bar) | ✅ Done |
| Admin login (ADMIN_PASSWORD from Secrets Manager) | ✅ Done |
| Integration testing on paper accounts | ⏳ Week 7 — start ECS task, monitor first paper trades |
| Live Alpaca keys | ⏳ Month 4 — after 60-day paper validation |
| 13F institutional signals | Deferred to v2 |
| Short interest signals | Deferred to v2 |
| Unusual Whales API | Deferred to v2 |
