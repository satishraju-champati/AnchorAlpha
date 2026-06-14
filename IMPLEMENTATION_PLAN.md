# AnchorAlpha Trading Bot — Implementation Plan

Last updated: 2026-06-14

---

## What You Already Have (No Action Needed)

| Asset | Status |
|---|---|
| AWS account | ✓ Active |
| Lightsail — Streamlit dashboard at anchoralpha.com | ✓ Running |
| Lambda + S3 + CloudWatch — nightly momentum pipeline | ✓ Running |
| FMP API — Starter plan $29/month | ✓ Sufficient for v1, no upgrade needed |
| Namecheap domain — anchoralpha.com | ✓ Pointing to Lightsail |
| GitHub repo — existing AnchorAlpha codebase | ✓ Active |

---

## YOUR Prerequisites — Complete These Before I Start Coding

### Step 1 — Create Alpaca Account (Free)

1. Go to **https://alpaca.markets** → Sign Up
2. Complete identity verification (required for live trading, takes 1–2 days)
3. In your Alpaca dashboard:
   - Go to **Paper Trading** → API Keys → Generate New Key
   - Go to **Live Trading** → API Keys → Generate New Key
4. Save all four values:
   ```
   Paper API Key:    PKXXXXXXXXXXXXXXXXXX
   Paper API Secret: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   Live API Key:     AKXXXXXXXXXXXXXXXXXX
   Live API Secret:  XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```
5. Do NOT fund the live account yet — that happens after 60 days of paper trading

---

### Step 2 — Create Anthropic Account (Claude API)

1. Go to **https://console.anthropic.com** → Sign Up or Log In
2. Go to **API Keys** → Create New Key → copy the key
3. Go to **Billing** → Add a payment method → Add $20–50 credit (enough for weeks of testing)
4. Save the key:
   ```
   Claude API Key: sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

---

### Step 3 — Create Alpha Vantage Account (Free — Earnings Calendar)

1. Go to **https://www.alphavantage.co/support/#api-key** → Get Free API Key
2. Fill in the form → copy the key
3. Save the key:
   ```
   Alpha Vantage API Key: XXXXXXXXXXXXXXXX
   ```

---

### Step 4 — Add New Secrets to AWS Secrets Manager

Go to **AWS Console → Secrets Manager → Store a new secret**
For each secret below: choose **"Other type of secret"** → add key/value pairs → use the exact secret name shown.

| Secret Name | Key | Value |
|---|---|---|
| `anchoralpha/claude` | `CLAUDE_API_KEY` | your Claude API key |
| `anchoralpha/alpaca-paper` | `ALPACA_KEY` | your Alpaca paper key |
| | `ALPACA_SECRET` | your Alpaca paper secret |
| `anchoralpha/alpaca-live` | `ALPACA_KEY` | your Alpaca live key |
| | `ALPACA_SECRET` | your Alpaca live secret |
| `anchoralpha/alphavantage` | `ALPHAVANTAGE_API_KEY` | your Alpha Vantage key |

(Your existing FMP secret stays unchanged.)

---

### Step 5 — Find Your Default VPC Subnet IDs

The Fargate task needs to know which subnets to run in. Your default VPC already has subnets — just look them up once.

1. Go to **AWS Console → VPC → Subnets**
2. Filter by **Default subnet = Yes**
3. Copy the Subnet IDs (there will be 2–3, one per availability zone)
   ```
   Example:
   subnet-0abc123456789
   subnet-0def987654321
   subnet-0ghi111222333
   ```

---

### Step 6 — Confirm Existing AWS Details

Look up these values from your existing AWS setup and note them down:

| Info Needed | Where to Find It |
|---|---|
| AWS Account ID | AWS Console → top-right corner → Account |
| AWS Region | AWS Console → top-right corner (e.g. us-east-1) |
| Existing S3 bucket name | S3 Console → your AnchorAlpha bucket name |
| Existing CloudFormation stack name | CloudFormation Console → Stacks → your stack name |
| Existing FMP secret name in Secrets Manager | Secrets Manager → find the FMP key secret name |
| Lightsail container service name | Lightsail Console → Containers → service name |
| Admin dashboard password (choose one now) | Any password you want for the Live tab |

---

## What to Send Me When Prerequisites Are Done

Once you've completed the steps above, share these details in our next session:

```
AWS Account ID:           123456789012
AWS Region:               us-east-1
S3 Bucket Name:           anchoralpha-data
CloudFormation Stack:     anchor-alpha-stack
FMP Secret Name:          anchoralpha/fmp  (or whatever it's called)
Lightsail Service Name:   anchoralpha-service
Default VPC Subnet IDs:   subnet-xxx, subnet-yyy, subnet-zzz
Admin Password (Live tab): (your chosen password)

Alpaca paper key:         confirmed created ✓
Claude API key:           confirmed created ✓
Alpha Vantage key:        confirmed created ✓
Secrets Manager:          confirmed 4 new secrets added ✓
```

That's all I need. I will handle everything else from code onwards.

---

## What I Will Build (Reference)

### Architecture

```
anchoralpha.com (Namecheap)
       ↓
  Lightsail → Streamlit dashboard (3 tabs)
              ├── 📈 Momentum  — existing dashboard (moved into tab)
              ├── 🔬 Research  — paper trading configs, analytics
              └── 🚀 Live      — real trading profiles, P&L (password protected)

  ONE ECS Fargate task (Mon–Fri 8:30 AM – 4:30 PM ET)
  ├── Research loop → Alpaca paper keys → 8 configs
  └── Live loop    → Alpaca live keys  → active profiles
         ↓ reads configs from / writes trades to
        S3 (configs, trades, positions, scores)
         ↓ calls outbound APIs
        FMP API        — price data, news, fundamentals
        Claude API     — 0–1 stock scoring
        Alpaca API     — order execution + position polling
        Alpha Vantage  — earnings calendar

  Existing Lambda (unchanged)
  → nightly momentum pipeline → S3 → momentum-data/
```

### Delivery Sequence (I handle all of this)

| Week | What Gets Built |
|---|---|
| 1 | CloudFormation update (ECS, ECR, IAM, EventBridge), Dockerfile |
| 2 | Core trading code: Claude scorer, Alpaca client, dip detector, config manager |
| 3 | Research engine: paper trading loop, S3 trade logging, 8 default configs |
| 4 | Streamlit: unified 3-tab dashboard, Research tab with config editor + analytics |
| 5 | Live engine: real order execution, emergency stop, position conflict check |
| 6 | Streamlit: Live tab with profiles, P&L, admin controls |
| 7 | Integration testing on paper accounts, fix issues |
| Month 2–3 | 60-day paper trading run (your job: monitor results) |
| Month 4 | Analysis, threshold selection, go live (your decision) |

### Monthly Cost

| Component | Cost |
|---|---|
| AWS Lightsail (existing) | $7 |
| AWS ECS Fargate (1 task) | ~$9 |
| AWS Lambda + S3 + CloudWatch (existing) | ~$3 |
| AWS Secrets Manager (4 new secrets) | ~$2 |
| AWS ECR + EventBridge | ~$0.15 |
| FMP API Starter (existing) | $29 |
| Claude API (Haiku for research, Sonnet for live) | ~$43 |
| Alpha Vantage | $0 |
| Alpaca | $0 |
| **Total** | **~$93/month** |

During paper trading only (months 2–3): ~$75/month (no live trading, fewer Claude calls).

### New Code Structure

```
src/AnchorAlpha/
  trading/
    claude_scorer.py      — Claude API scoring (replaces Perplexity)
    alpaca_client.py      — broker: orders, positions, polling
    dip_detector.py       — 10-day high drawdown detection
    position_manager.py   — open position registry, conflict check
    order_manager.py      — bracket orders, take-profit, stop-loss
    earnings_guard.py     — earnings calendar, entry block, pre-close
    config_manager.py     — read/write S3 config JSON
    trading_engine.py     — main evaluation loop
  streamlit_app/
    app.py                — unified 3-tab entry point (replaces current)
    momentum_dashboard.py — existing code wrapped in render() function
    research_dashboard.py — new: Research tab
    live_dashboard.py     — new: Live tab
```

### What Is NOT in v1 (Deferred to v2)

| Feature | Reason |
|---|---|
| 13F Institutional holdings signal | Requires FMP Ultimate ($139/month) |
| Short interest signal | Deferred to v2 |
| Unusual Whales API | Confirmed deferred to v2 |
| Automated Research → Live promotion | Human gate is intentional |
| SMS/mobile alerts | SNS email sufficient for v1 |
