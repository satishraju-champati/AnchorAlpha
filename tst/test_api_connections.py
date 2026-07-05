"""
API connection tests — run locally to verify all external APIs are reachable.
Reads secrets from AWS Secrets Manager (requires configured AWS CLI).

Usage:
    python tst/test_api_connections.py
"""

import json
import sys

import boto3
import requests

AWS_REGION = "us-east-1"
RESULTS = []


def ok(name, detail=""):
    RESULTS.append(("PASS", name, detail))
    print(f"  ✓  {name}" + (f" — {detail}" if detail else ""))


def fail(name, detail=""):
    RESULTS.append(("FAIL", name, detail))
    print(f"  ✗  {name}" + (f" — {detail}" if detail else ""))


# ── Secrets Manager ────────────────────────────────────────────────────────────

def load_secrets():
    print("\n[1] Loading secrets from AWS Secrets Manager...")
    client = boto3.client("secretsmanager", region_name=AWS_REGION)

    def get(name):
        raw = client.get_secret_value(SecretId=name)["SecretString"]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_value": raw}  # plain string secret (FMP is stored this way)

    try:
        claude = get("anchoralpha/claude")
        ok("Secrets Manager: anchoralpha/claude")
    except Exception as e:
        fail("Secrets Manager: anchoralpha/claude", str(e))
        claude = {}

    try:
        alpaca = get("anchoralpha/alpaca-paper")
        ok("Secrets Manager: anchoralpha/alpaca-paper")
    except Exception as e:
        fail("Secrets Manager: anchoralpha/alpaca-paper", str(e))
        alpaca = {}

    try:
        av = get("anchoralpha/alphavantage")
        ok("Secrets Manager: anchoralpha/alphavantage")
    except Exception as e:
        fail("Secrets Manager: anchoralpha/alphavantage", str(e))
        av = {}

    try:
        fmp = get("anchor-alpha/fmp-api-key-prod")
        ok("Secrets Manager: anchor-alpha/fmp-api-key-prod")
    except Exception as e:
        fail("Secrets Manager: anchor-alpha/fmp-api-key-prod", str(e))
        fmp = {}

    return {
        "claude_key": claude.get("CLAUDE_API_KEY", ""),
        "alpaca_key": alpaca.get("ALPACA_KEY", ""),
        "alpaca_secret": alpaca.get("ALPACA_SECRET", ""),
        "av_key": av.get("ALPHAVANTAGE_API_KEY", ""),
        "fmp_key": fmp.get("FMP_API_KEY") or fmp.get("_value", ""),
    }


# ── FMP API ────────────────────────────────────────────────────────────────────

def test_fmp(fmp_key: str):
    print("\n[2] Testing FMP API...")
    if not fmp_key:
        fail("FMP: skipped — no key")
        return

    base = "https://financialmodelingprep.com/stable"

    # Quote (current price)
    try:
        resp = requests.get(f"{base}/quote", params={"symbol": "NVDA", "apikey": fmp_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data[0]["price"] if data else None
        ok("FMP: quote NVDA", f"price=${price}")
    except Exception as e:
        fail("FMP: quote NVDA", str(e))

    # Historical price EOD (for dip detection)
    try:
        resp = requests.get(
            f"{base}/historical-price-eod/full",
            params={"symbol": "NVDA", "timeseries": 15, "apikey": fmp_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        days = len(data) if isinstance(data, list) else len(data.get("historical", []))
        ok("FMP: historical-price-eod/full NVDA", f"{days} days returned")
    except Exception as e:
        fail("FMP: historical-price-eod/full NVDA", str(e))

    # Profile (market cap, sector)
    try:
        resp = requests.get(f"{base}/profile", params={"symbol": "NVDA", "apikey": fmp_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        mkt_cap = data[0].get("mktCap", 0) if data else 0
        ok("FMP: profile NVDA", f"mktCap=${mkt_cap/1e12:.1f}T")
    except Exception as e:
        fail("FMP: profile NVDA", str(e))

    # News
    try:
        resp = requests.get(
            f"{base}/news/stock",
            params={"tickers": "NVDA", "limit": 3, "apikey": fmp_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        ok("FMP: news/stock NVDA", f"{len(data)} articles")
    except Exception as e:
        fail("FMP: news/stock NVDA", str(e))

    # Stock price change (momentum signals)
    try:
        resp = requests.get(
            f"{base}/stock-price-change",
            params={"symbol": "NVDA", "apikey": fmp_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        ok("FMP: stock-price-change NVDA", f"keys={list(data[0].keys())[:4]}" if data else "no data")
    except Exception as e:
        fail("FMP: stock-price-change NVDA", str(e))


# ── Claude API ─────────────────────────────────────────────────────────────────

def test_claude(claude_key: str):
    print("\n[3] Testing Claude API...")
    if not claude_key:
        fail("Claude: skipped — no key")
        return

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=claude_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": 'Reply with exactly: {"score": 0.75, "ok": true}'}],
        )
        raw = msg.content[0].text.strip()
        data = json.loads(raw)
        ok("Claude: Haiku scoring test", f"score={data.get('score')} ok={data.get('ok')}")
    except Exception as e:
        fail("Claude: Haiku scoring test", str(e))


# ── Alpha Vantage ──────────────────────────────────────────────────────────────

def test_alphavantage(av_key: str):
    print("\n[4] Testing Alpha Vantage API...")
    if not av_key:
        fail("Alpha Vantage: skipped — no key")
        return

    try:
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "EARNINGS_CALENDAR",
                "symbol": "NVDA",
                "horizon": "3month",
                "apikey": av_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        ok("Alpha Vantage: EARNINGS_CALENDAR/NVDA", f"{len(lines)-1} earnings entries")
    except Exception as e:
        fail("Alpha Vantage: EARNINGS_CALENDAR/NVDA", str(e))


# ── Alpaca Paper API ───────────────────────────────────────────────────────────

def test_alpaca(alpaca_key: str, alpaca_secret: str):
    print("\n[5] Testing Alpaca Paper API...")
    if not alpaca_key or not alpaca_secret:
        fail("Alpaca: skipped — no key/secret")
        return

    headers = {
        "APCA-API-KEY-ID": alpaca_key,
        "APCA-API-SECRET-KEY": alpaca_secret,
    }
    base = "https://paper-api.alpaca.markets/v2"

    # Account
    try:
        resp = requests.get(f"{base}/account", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        portfolio = float(data.get("portfolio_value", 0))
        ok("Alpaca Paper: account", f"portfolio=${portfolio:,.0f}")
    except Exception as e:
        fail("Alpaca Paper: account", str(e))

    # Clock (market status)
    try:
        resp = requests.get(f"{base}/clock", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ok("Alpaca Paper: clock", f"market_open={data.get('is_open')}")
    except Exception as e:
        fail("Alpaca Paper: clock", str(e))

    # Positions
    try:
        resp = requests.get(f"{base}/positions", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ok("Alpaca Paper: positions", f"{len(data)} open positions")
    except Exception as e:
        fail("Alpaca Paper: positions", str(e))

    # Latest quote — market data is on data.alpaca.markets, not paper-api
    try:
        resp = requests.get(
            "https://data.alpaca.markets/v2/stocks/quotes/latest",
            headers=headers,
            params={"symbols": "NVDA"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        ask = data.get("quotes", {}).get("NVDA", {}).get("ap", "n/a")
        ok("Alpaca: market data quotes/latest NVDA", f"ask=${ask}")
    except Exception as e:
        fail("Alpaca: market data quotes/latest NVDA", str(e))


# ── Summary ────────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    passes = [r for r in RESULTS if r[0] == "PASS"]
    failures = [r for r in RESULTS if r[0] == "FAIL"]
    print(f"  PASSED: {len(passes)}")
    print(f"  FAILED: {len(failures)}")
    if failures:
        print("\nFailed tests:")
        for _, name, detail in failures:
            print(f"  ✗ {name}: {detail}")
    print("=" * 55)
    return len(failures) == 0


if __name__ == "__main__":
    print("=" * 55)
    print("AnchorAlpha API Connection Tests")
    print("=" * 55)

    secrets = load_secrets()
    test_fmp(secrets["fmp_key"])
    test_claude(secrets["claude_key"])
    test_alphavantage(secrets["av_key"])
    test_alpaca(secrets["alpaca_key"], secrets["alpaca_secret"])

    all_passed = print_summary()
    sys.exit(0 if all_passed else 1)
