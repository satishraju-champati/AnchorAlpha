# Trading Bot - Strategy & Requirements

**Status**: Strategy validated (0.79/1.0). Two-app architecture confirmed. Ready for technical design.
_Last updated: 2026-06-14_

---

## Core Idea

A **thematic swing trading bot** focused exclusively on the AI sector that:
- Scores stocks 0–1 using financial data, news, social media, and documents via Claude API
- Buys large-cap AI stocks when score > 0.75 AND a confirmed dip is detected
- Manages exits with hard take-profit, stop-loss, max-hold, and intelligent Friday review
- Uses FMP for market data, Alpaca for order execution
- Runs on ECS Fargate (long-running service, not Lambda)

---

## Confirmed Strategy Rules

| Rule | Value | Reasoning |
|---|---|---|
| **Universe** | Large-cap AI sector only (~35 stocks) | Large-caps absorb bad news; AI has decade-long tailwind |
| **Score threshold** | > 0.75 via Claude API | Multi-signal composite scoring |
| **Dip detection** | Drawdown ≥ -10% from 10-day high | Captures both single-day crashes and multi-day gradual declines |
| **Entry condition** | Score > 0.75 AND dip confirmed AND confirmation check passed | Buy quality at a discount, selling pressure slowing |
| **Take-profit** | +20% from entry price | Risk/reward 1:2 — need only >33% win rate to profit |
| **Stop-loss** | -10% from entry price | ~-19% from peak — signals real fundamental problem |
| **Risk/reward** | 1:2 (risk 10%, target 20%) | Large-cap AI stocks regularly make 20% swing moves |
| **Market condition filter** | Only enter when SPY AND SOXX above 200-day MA | No new trades in bear markets or sector downturns |
| **Max hold** | 20 trading days — re-score and decide | Prevents dead-money positions |
| **Hold extension** | Extendable past 20 days if score still > 0.75 | Only extend on confirmed strength |
| **Max open positions** | 5 simultaneously | Concentrated but controlled |
| **Capital deployed** | 30% of net worth total | 70% kept as dry powder |
| **Per position size** | 6% of net worth (30% ÷ 5, equal split) | No single position dominates |
| **Friday review** | Re-score all positions, close selectively (see below) | Balance weekend gap risk with holding winners |
| **Worst case** | -3% of net worth (all 5 stop out) | Acceptable v1 risk |
| **Best case** | +6% of net worth (all 5 hit target) | 5 × 6% × 20% gain |

---

## AI Sector Universe (~35 Stocks)

| Sub-sector | Stocks |
|---|---|
| **Semiconductors (design)** | NVDA, AMD, AVGO, QCOM, MRVL, ASML |
| **Semiconductors (manufacturing)** | TSM, INTC |
| **Memory** | MU |
| **Cloud / hyperscalers** | MSFT, AMZN, GOOGL, META |
| **Networking** | ANET, CSCO |
| **Data center hardware** | DELL, HPE, VRT, ETN |
| **AI software / platforms** | NOW, CRM, ORCL, PLTR |
| **EDA / design tools** | SNPS, CDNS |
| **Storage** | PSTG, WDC |

All large-cap ($100B+). All have abundant public data. All heavily covered by analysts and news.

---

## Scoring Model (0 to 1 via Claude API)

Claude receives a structured input per stock and returns a score + reasoning.

### Input Signals

| Signal | Source | Weight | Version |
|---|---|---|---|
| Revenue growth YoY | FMP financials | High | v1 |
| Earnings surprise (beat/miss) | FMP earnings | High | v1 |
| Analyst consensus (% Buy, avg target) | FMP analyst data | High | v1 |
| Price momentum (7d/30d/60d/90d) | FMP + existing engine | Medium | v1 |
| Recent news sentiment | FMP news API | Medium | v1 |
| Insider trading activity | FMP insider data | Medium | v1 |
| SEC filing signals (10-K/10-Q) | SEC EDGAR | Medium | v1 |
| Proximity to 52-week high/low | FMP price data | Medium | v1 |
| **Volume anomaly** (2.5× avg volume, flat price = accumulation) | FMP — existing data | Medium | v1 |
| **Institutional ownership change** QoQ (13F-equivalent) | FMP institutional API | Medium | v1 |
| **Short interest change** (declining short interest = bullish) | FMP short interest | Medium | v1 |
| **Unusual options flow** (OTM calls, short expiry, outsized volume) | Unusual Whales API | Medium-High | v2 |
| **Dark pool ratio spike** (institutional off-exchange accumulation) | Specialized API (CBOE/Quandl) | Low-Medium | v2 |
| Social media sentiment | Twitter/X, Reddit | Low | v2 |

### Hedge Fund Signal Details

**Volume Anomaly** — derivable from existing FMP data, no new API needed:
```
Signal fires when:
  - Today's volume > 2.5× 30-day average daily volume
  - AND price move < 1% (flat price despite heavy volume)
Meaning: large buyer absorbing all selling without moving price = accumulation
Negative signal: high volume + price DOWN sharply = distribution (institutions exiting)
```

**Institutional Ownership Change** — FMP `/stable/institutional-ownership/{symbol}`:
```
Positive signal: institutional ownership % increased QoQ
Strong signal:   top hedge funds (Citadel, Druckenmiller, etc.) added to position
Negative signal: institutional ownership % declined QoQ (smart money leaving)
```

**Short Interest Change** — FMP short interest endpoint:
```
Positive signal: short interest % of float declining (short sellers losing conviction)
Negative signal: short interest rising sharply (smart money betting against the stock)
```

**Unusual Options Flow** — Unusual Whales API (paid, ~$50–100/month):
```
Signal fires when:
  - Out-of-the-money calls bought in size (volume > 3× open interest)
  - Short expiry (1–3 weeks)
  - Before any public catalyst
Meaning: someone with conviction is making a directional bet ahead of a move
```

**Dark Pool Ratio** — v2, specialized data source needed:
```
Signal fires when: dark pool volume as % of total volume spikes above baseline
Meaning: institutions accumulating quietly off-exchange
```

### Claude Output Format
```json
{
  "score": 0.87,
  "direction": "positive",
  "dip_type": "macro",
  "reasoning": "Dip appears macro-driven, not fundamental. Revenue trajectory
                 intact. Analyst targets imply 28% upside. No insider selling.
                 Volume anomaly detected (3.1× avg volume, price flat) — accumulation.
                 Institutional ownership up 4% QoQ. Short interest declining.
                 Unusual call flow detected (2-week OTM calls, 5× avg volume).",
  "flags": [
    "earnings beat last 3 quarters",
    "sector leadership confirmed",
    "volume anomaly — likely institutional accumulation",
    "short interest declining — shorts covering"
  ],
  "risks": ["macro rate sensitivity", "customer concentration"],
  "recommendation": "BUY"
}
```

### Critical Rule
If the news behind the dip is **fundamental** (lost customer, earnings miss, regulatory action) — Claude must drop the score below 0.75 regardless of momentum or hedge fund signals. Distinguishing noise dips from fundamental dips is the most important Claude task.

---

## Earnings Calendar Rule

Earnings are binary events — a stock with a great thesis can still gap ±15% on a single quarter miss. The bot must be aware of the earnings calendar at all times.

**Data source**: FMP `/stable/earnings-calendar` and `/stable/historical/earning_calendar/{symbol}` — already accessible via existing FMP client.

### Rules

**New entries — blocked:**
```
Before placing any bracket order:
  Check: does this stock have earnings within the next 3 trading days?
  Yes → skip, do not enter. Re-evaluate after earnings + 1 day.
  No  → proceed normally.
```

**Existing positions — pre-earnings close:**
```
Daily pre-market check (runs before scoring):
  For each open position:
    Check: does this stock have earnings in the next 2 trading days?
    Yes → CLOSE the position today at market open
    No  → proceed to normal re-score
```

**Why 2 days for close vs 3 days for entry block:**
- 3-day block on new entries: conservative buffer, no reason to enter ahead of uncertainty
- 2-day close on existing positions: gives 1 extra day to exit cleanly after the block triggers, avoids holding through an overnight earnings gap

**After earnings:**
- Wait 1 trading day after earnings date before re-evaluating the stock
- Let the post-earnings volatility settle
- Re-score with the new earnings data baked in (beat/miss now known)
- If score still > 0.75 and a new dip formed → eligible for fresh entry

---

## API Failsafe Behaviour

The bot depends on three external APIs. Each can fail independently. Behaviour is defined for each scenario.

### Core Principle
> When in doubt, do not trade. Protect existing positions. Alert the user immediately via SNS.

### Claude API Down (scoring engine fails)

| Situation | Action |
|---|---|
| Morning scan | Skip entirely — no scoring, no new entries today |
| Daily re-score of open positions | Use last known score — do not close based on missing data |
| 3-day score decline check | Pause the counter — do not count a missing score as a decline |
| Friday review | Skip scoring — hold all positions, apply only price-based rules |
| Recovery | Resume normal operation next trading day |
| Alert | SNS notification immediately on first failure |

### Alpaca API Down (order execution fails)

| Situation | Action |
|---|---|
| New bracket orders | Block — no new entries while Alpaca is unreachable |
| Existing bracket orders | **Safe** — already live at Alpaca, execute autonomously even if our app is disconnected |
| Manual close attempts (Friday review, earnings close) | Retry with exponential backoff (3 attempts, 30s apart) → if all fail, SNS alert for manual intervention |
| Recovery | Resume normal operation, verify all open orders are in expected state |
| Alert | SNS notification immediately on first failure |

### FMP API Down (market data fails)

| Situation | Action |
|---|---|
| Morning scan (dip detection, scoring data) | Skip new entries — no data to score against |
| Daily re-score | Use S3-cached data from previous day if available — flag score as stale |
| Market condition check (SPY/SOXX MA) | Use cached MA values from previous day — conservative: if cache is >1 day old, treat as RED LIGHT |
| Recovery | Resume normal operation next trading day |
| Alert | SNS notification immediately on first failure |

### Combined / Cascading Failure

If two or more APIs are down simultaneously:
- Halt all trading activity completely
- Hold all existing positions (bracket orders still live at Alpaca)
- Send high-priority SNS alert with full status
- Resume only when all APIs are confirmed healthy

---

## Market Condition Filter

Before scanning any stocks, check the macro environment. If either condition fails, **stop all new entries**. Do not close existing positions — let their own exit rules handle them.

```
Check every morning (pre-market):
  1. SPY (S&P 500 ETF) closing price > 200-day moving average?
  2. SOXX (Semiconductor ETF) closing price > 200-day moving average?

  Both above 200-day MA → GREEN LIGHT, proceed to stock scan
  Either below 200-day MA → RED LIGHT, no new entries today

Resume entries only when both recover above their 200-day MA.
```

**Why SPY AND SOXX:**
- SPY filters out broad bear markets (2022, March 2020)
- SOXX specifically filters AI/semiconductor sector downturns
- Both must be healthy — a rising market with a broken semiconductor sector is still a no-entry signal

**Historical impact:**
- 2022: SOXX broke 200-day MA in January → filter would have kept you in cash all year while AI stocks dropped 40–65%
- March 2020: SPY broke 200-day MA → filter keeps you out of the crash, re-enters on recovery
- 2023–2025: both above 200-day MA most of the time → strategy runs freely

---

## Entry Flow

```
Daily pre-market scan (9:00 AM ET, Mon–Fri):

STEP 0 — API health check:
  Claude, Alpaca, FMP all reachable? → proceed
  Any API down?                       → apply failsafe rules, stop new entries

STEP 1 — Earnings pre-close:
  For each OPEN position:
    Earnings within 2 trading days? → CLOSE at market open today

STEP 2 — Market condition check:
  SPY and SOXX both above 200-day MA? → proceed
  Either below 200-day MA?            → stop, no new entries today

For each stock in universe:
  1. Earnings check — earnings within 3 trading days? → skip this stock

  2. Score via Claude API — if score < 0.75 → skip

  3. Dip detection — measure drawdown from 10-day high:
     - Drawdown < -10% → dip detected, proceed
     - Drawdown ≥ -10% not reached → skip

  4. Confirmation check (differs by dip type):

     SINGLE-DAY drop (stock fell ≥ -10% in one day):
       - Wait 1 day after drop
       - Day-1 additional drop 0% to -5%  → BUY
       - Day-1 additional drop > -5%      → wait another day, re-score
       - Day-1 recovery > +2%            → re-evaluate, re-score

     MULTI-DAY gradual drop (-10% spread over 2–5 days):
       - Check if most recent day's drop < average daily drop during decline
       - Deceleration confirmed (e.g. avg -3.5%/day, last day -1.5%) → BUY
       - No deceleration (drop accelerating)                          → wait, re-score

  5. On BUY signal — place Alpaca bracket order:
     - Entry:       market order at open
     - Take-profit: +20% from fill price
     - Stop-loss:   -10% from fill price

  6. Log score, dip type, reasoning, trade thesis → S3
```

---

## Exit Flow

| Trigger | Action |
|---|---|
| Price hits +20% | Alpaca auto-executes take-profit (bracket order) |
| Price hits -10% | Alpaca auto-executes stop-loss (bracket order) |
| **Score declines 3 consecutive days AND falls below 0.75** | Close immediately — thesis breaking down |
| **Score declines 3 consecutive days, still above 0.75** | Flag as warning — monitor closely, do not close yet |
| Day 20 reached | Re-score. Exit if score < 0.75. Extend if score ≥ 0.75 |
| Position age ≥ 18 days on Friday | Close — end of cycle, don't extend into another week |
| **Friday 3:30 PM ET review** | See Friday Review Rule below |

### Daily Re-score Rule (every trading day, pre-market)

All open positions are re-scored via Claude API each morning. Score history is stored in S3.

```
For each open position:
  1. Generate new score via Claude API
  2. Append to score history: [day-3, day-2, day-1, today]
  3. Check 3-consecutive-day decline rule:
     - If score has declined for 3 straight days AND today's score < 0.75 → CLOSE
     - If score has declined for 3 straight days AND today's score ≥ 0.75  → FLAG warning
     - If score rebounds on any day → reset the consecutive counter
  4. Log score, reasoning, and any flags → S3
```

**Why practical over strict:**
A score of 0.90 → 0.88 → 0.86 is a strong position gently fading — thesis still intact, don't exit.
A score of 0.82 → 0.78 → 0.72 → 0.68 crossing below 0.75 on a downtrend → clear exit signal.

### Friday Review Rule (Option B — confirmed)

Every Friday at 3:30 PM ET, re-score all open positions and close selectively:

| Position state | Action | Reasoning |
|---|---|---|
| Score dropped below 0.75 | **CLOSE** | Thesis has weakened — don't carry into weekend |
| Score declining 3 days AND below 0.75 | **CLOSE** | Confirmed breakdown — exit before weekend |
| Score > 0.75 AND position in a loss | **CLOSE** | Don't carry losers into weekend gap risk |
| Score > 0.75 AND position in profit | **HOLD** through weekend | Momentum is with you — let it run |
| Position age ≥ 18 trading days | **CLOSE** | End of cycle regardless of P&L |

This means:
- Strong winning positions can run the full 20 days across multiple weekends
- Losing positions and weakening theses are cut before weekend gap risk
- The 20-day rule functions as designed (no conflict with Friday review)

---

## Two-App Architecture

The system is split into two fully independent applications sharing a common codebase core.

---

### App 1 — Research & Paper Trading Engine

**Purpose:** Discover optimal parameters. Test sectors. Validate scoring. No real money.

**Alpaca account:** Paper account only
**Login:** None required — open access
**S3 prefix:** `s3://anchoralpha-data/research/`

#### Configuration

Up to **8 simultaneous configs** running in parallel. Each config is independently defined:

| Parameter | Configurable Range |
|---|---|
| Score threshold | 0.50 → 0.90 |
| Sector | AI, Cloud/SaaS, Fintech, Healthcare, Energy, Broad Large-cap |
| Dip threshold | -6%, -8%, -10%, -12%, -15% |
| Dip measurement window | 5-day, 10-day, 15-day, 20-day high |
| Take-profit | +10%, +15%, +20%, +25%, +30% |
| Stop-loss | -7%, -10%, -12%, -15% |
| Max hold period | 10, 15, 20, 25 days |
| Position sizing | Equal weight or score-weighted |
| Capital per config | Fixed paper budget (e.g. $100K per config, standardised) |
| Max positions per config | 1 → 10 |
| Market condition filter | SPY only / SOXX only / both / neither |
| Earnings entry block | On / Off |
| Earnings pre-close | On / Off |

All other filters (API health, confirmation day logic, Friday review, daily re-score) apply to all configs by default.

#### Research Dashboard Tab

- Side-by-side comparison of all active configs
- Per-config metrics: P&L, win rate, trade frequency, avg hold days, max drawdown
- Score threshold calibration chart: win rate vs threshold for each sector
- Trade log: every paper trade with full detail (score, dip type, entry/exit reason)
- **"Promote to Live"** button per config → creates a Profile in the Live app with those parameters (requires Live app admin login to confirm)

---

### App 2 — Live Trading Engine

**Purpose:** Trade real money with validated, admin-controlled parameters.

**Alpaca account:** Live account (paper initially until research phase complete)
**Login:** Admin password required for any write action. Read-only (positions, P&L) is open.
**S3 prefix:** `s3://anchoralpha-data/live/`

#### Sector Layer

Sectors are the top-level on/off switch. Each sector is independently enabled or disabled. Disabling a sector pauses all its profiles without deleting them.

```
SECTORS                         STATUS      PROFILES
──────────────────────────────────────────────────────
AI / Semiconductors             🟢 ENABLED  2 active
Cloud / SaaS                    🟢 ENABLED  1 active
Fintech                         🔴 DISABLED 0 configured
Healthcare / Biotech            🔴 DISABLED 0 configured
Energy                          🔴 DISABLED 0 configured
Broad Large-cap (SPY top 50)    🔴 DISABLED 0 configured
```

Stocks are drawn from the sector's universe when that sector is enabled. Multiple sectors run in parallel.

#### Profile Layer (per sector)

Each sector can have **multiple profiles** active simultaneously. Each profile is a complete independent strategy with its own parameters, capital allocation, and risk rules.

```
AI / Semiconductors — Active Profiles:

┌─────────────────────────────────────────────────────────┐
│ Profile: Conservative               [🟢 ACTIVE] [Edit]  │
│   Score threshold:    ≥ 0.60                            │
│   Dip required:       -8% from 10-day high              │
│   Take-profit:        +15%                              │
│   Stop-loss:          -10%                              │
│   Max hold:           20 days                           │
│   Capital:            12% of net worth                  │
│   Max positions:      2                                 │
│   Expected success:   ~50%   (from research)            │
│   Expected profit:    10–15% (from research)            │
│   Earnings pre-close: ON                                │
│   Earnings entry block: ON                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Profile: Aggressive                 [🟢 ACTIVE] [Edit]  │
│   Score threshold:    ≥ 0.70                            │
│   Dip required:       -12% from 10-day high             │
│   Take-profit:        +25%                              │
│   Stop-loss:          -10%                              │
│   Max hold:           20 days                           │
│   Capital:            10% of net worth                  │
│   Max positions:      1                                 │
│   Expected success:   ~40%   (from research)            │
│   Expected profit:    20–25% (from research)            │
│   Earnings pre-close: OFF  ← hold through earnings      │
│   Earnings entry block: ON                              │
└─────────────────────────────────────────────────────────┘

[+ Add Profile]
```

#### Capital Allocation Rules

- **No global hard cap** — each profile has its own capital % set by the user
- Dashboard shows **total deployed capital** across all active profiles as a live warning
- User is responsible for not over-allocating (system warns, does not block)
- Each profile's capital is reserved at the profile level — other profiles cannot use it

```
Capital summary (live warning bar):
  AI Conservative:    12%
  AI Aggressive:      10%
  Cloud Moderate:      8%
  ────────────────────────
  Total allocated:    30%  ← shown prominently
  Net worth reserved: 70%
```

#### Stock Conflict Rule (One Position Per Stock Globally)

Across ALL active profiles and sectors, **each stock can only be held in one position at a time.**

```
Rule: Before placing any order, check global open positions.
  Stock already held by ANY active profile? → skip, do not enter.
  Stock not held anywhere?                  → first qualifying profile wins.

When a position closes (take-profit, stop-loss, or other exit):
  Stock becomes available again for any profile to enter.
```

This prevents unintended double-exposure when two profiles scan the same stock simultaneously.

#### Earnings Toggle (Per Profile)

Each profile independently controls its earnings behaviour:

| Toggle | Options | Default |
|---|---|---|
| Earnings entry block | ON / OFF | ON — block new entries 3 days before earnings |
| Earnings pre-close | ON / OFF | ON — close existing position 2 days before earnings |

Aggressive profiles may turn pre-close OFF to hold through earnings for potential beat upside.

#### Admin Login

- **Password-protected** actions: enable/disable sector, enable/disable profile, edit profile parameters, promote research config to live
- **Open (no login)**: view positions, P&L, trade history, score history
- Simple username/password via Streamlit `st.secrets` + session state
- Admin session expires after 4 hours of inactivity

---

### Shared Dashboard — Two Tabs

**Tab 1: Research**
- Config comparison table (all 8 configs, side by side)
- Win rate vs score threshold chart
- Trade log per config
- "Promote to Live" button (requires Live admin login to confirm)
- Paper P&L by config

**Tab 2: Live**
- Sector overview (enabled / disabled)
- Per-profile P&L, win rate, actual vs expected success rate
- All open positions across all profiles (with which profile owns each)
- Total capital deployed (warning bar)
- Trade history per profile
- Score history for open positions
- Admin panel (password-gated): sector toggles, profile editor, parameter updates

---

### How Parameters Flow — Research → Live

```
Step 1: Research app runs 60 days, 8 configs across sectors
Step 2: Research tab shows Config C has best risk-adjusted return
Step 3: User clicks "Promote to Live" on Config C
Step 4: System pre-fills a new Profile in Live app with Config C parameters
         + expected success/profit from research results
Step 5: Admin reviews, adjusts capital allocation, clicks Confirm
Step 6: Profile activates in Live app on next trading day
```

No automatic promotion — always requires human review and admin confirmation.

---

### Shared Codebase — Two Deployment Modes

```
Core (shared):
  ├── Claude scoring engine
  ├── FMP data client
  ├── Momentum / dip detection engine
  ├── Alpaca order client (paper + live)
  └── S3 storage client

Research mode:
  ├── Multi-config runner (up to 8 parallel)
  ├── Config store (S3 JSON, open to edit)
  ├── Paper Alpaca account
  └── Research dashboard tab

Live mode:
  ├── Multi-profile runner (sector × profile matrix)
  ├── Profile store (S3 JSON, admin-only edit)
  ├── Stock conflict checker (global position registry)
  ├── Capital allocation tracker
  ├── Live Alpaca account
  └── Live dashboard tab
```

Two separate ECS Fargate tasks. Two separate Alpaca accounts. Same S3 bucket, different prefixes.

---

### Infrastructure

| Component | Research App | Live App |
|---|---|---|
| Hosting | ECS Fargate task | ECS Fargate task |
| Alpaca account | Paper account | Live account |
| S3 prefix | `research/` | `live/` |
| Config storage | S3 JSON (open) | S3 JSON (admin-only) |
| Claude API | Shared | Shared |
| FMP API | Shared | Shared |
| Dashboard | Tab 1 (Research) | Tab 2 (Live) |
| Login | None | Admin password for write actions |

---

## Phased Delivery

| Phase | App | What |
|---|---|---|
| 1 | Both | Claude API scoring model — replace Perplexity, build 0–1 scorer |
| 2 | Research | Multi-config paper trading engine, 8 configs, all parameters configurable |
| 3 | Research | Research dashboard tab — config comparison, win rate charts, trade log |
| 4 | Both | Lightsail → ECS Fargate migration, two-tab dashboard |
| 5 | Live | Live app — sector layer, profile layer, stock conflict rule, admin login |
| 6 | Live | Promote research findings → live profiles. Start live trading (small allocation) |

**Gate between Phase 5 and 6:** 60-day research phase must show at least one config with positive expected value before live trading begins.

---

## Open Questions (For Technical Session)

- [x] Unusual options flow → deferred to v2
- [x] Re-score frequency → daily, with 3-consecutive-day declining score rule
- [x] Take-profit → raised to +20% (risk/reward 1:2)
- [x] Market condition filter → SPY AND SOXX above 200-day MA required
- [x] Paper trading duration → 60 days minimum before going live
- [x] Two-app architecture confirmed (Research + Live, shared codebase)
- [x] Research app: 8 configs max, all parameters configurable, no login
- [x] Live app: sector layer + profile layer, admin password for writes
- [x] Capital allocation: per-profile, no global hard cap, dashboard warning
- [x] Stock conflict: one position per stock globally across all profiles
- [x] Earnings toggle: per-profile (not global)
- [x] Dashboard: single shared Streamlit, two tabs (Research | Live)
- [x] S3: separate prefixes (research/ and live/)
- [ ] Social media signals: include Twitter/X (paid API) in v1 or defer to v2?
- [ ] Alpaca account setup: paper account ready?
- [ ] 10-day high for dip detection: or use 15-day / 20-day high?
- [x] Research phase sectors: all six confirmed — AI/Semiconductors, Cloud/SaaS, Fintech, Healthcare/Biotech, Energy, Broad Large-cap (SPY top 50)

---

## Strategy Validation (Independent Professional Assessment)

_Fresh independent validation — 2026-06-14_

### Score: **0.79 / 1.0**

| Dimension | Score | Notes |
|---|---|---|
| Macro thesis & sector choice | 0.88 | AI capex cycle real and multi-year — institutional backing |
| Entry architecture | 0.87 | Five-layer stack is professional grade |
| Earnings protection | 0.90 | Entry block + pre-close = both angles covered |
| Exit architecture | 0.86 | Three independent mechanisms catching different failure modes |
| Risk/reward ratio | 0.85 | 1:2, break-even at 33% win rate |
| Risk management & sizing | 0.88 | Conservative, -3% worst case on net worth |
| Operational resilience | 0.83 | Per-API failsafes fully defined |
| Score calibration | 0.48 | Central unknown — untested assumption, not evidence |
| Sector concentration | 0.58 | All positions correlated, inherent to thematic strategy |
| Trade frequency | 0.55 | Five filters may produce only 1–3 trades/month |
| API cost drag | 0.70 | ~$500–2,000/year, meaningful on small accounts |
| **Overall** | **0.79** | Strong architecture, one critical untested assumption |

### Can It Make Profit? Yes — Under Three Conditions

1. AI sector macro tailwind continues (currently strong, 2–3 year runway)
2. Claude score threshold at 0.75 validated by paper trading to produce >40% win rate
3. Trade frequency achieves minimum 2 qualifying trades per month

| Win rate | Annual return on deployed capital | Net worth impact (30% deployed) |
|---|---|---|
| 34% | Break-even | 0% |
| 40% | ~5–8% | ~1.5–2.4% |
| 45% | ~10–14% | ~3–4.2% |
| 50% | ~15–18% | ~4.5–5.4% |
| 55%+ | 20%+ | 6%+ |

### Key Remaining Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Score calibration untested | High | 60-day paper trading mandatory — this is the only fix |
| Sector correlation | Medium | Market filter + 30% cap — mitigated, not eliminated |
| Trade frequency too low | Medium | Measure during paper trading — may need to loosen filters |
| Choppy market churn | Medium | 20% target in sideways markets often times out at day 20 |
| API cost drag | Low | Real but manageable on accounts >$100K |

### What Would Push It to 0.87+

1. Paper trade 60 days → validate 0.75 threshold is correctly calibrated *(closes biggest gap)*
2. Add SOXX 50-day MA trending upward as a 6th entry filter *(eliminates choppy market entries)*
3. Monitor Claude score consistency day-to-day *(catch LLM variance before it drives bad decisions)*
4. Factor API costs into profitability target *(sets realistic expectations)*
