"""
Earnings calendar guard.
Blocks new entries 3 days before earnings, closes positions 2 days before.
Uses Alpha Vantage free tier for earnings dates.
"""

import logging
from datetime import date, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ENTRY_BLOCK_DAYS = 3    # block new entries this many days before earnings
PRE_CLOSE_DAYS = 2      # close open position this many days before earnings
AV_EARNINGS_URL = "https://www.alphavantage.co/query"


class EarningsGuard:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._cache: dict[str, Optional[date]] = {}

    def next_earnings_date(self, ticker: str) -> Optional[date]:
        """Return the next earnings date for the ticker, or None if unknown."""
        if ticker in self._cache:
            return self._cache[ticker]
        try:
            resp = requests.get(
                AV_EARNINGS_URL,
                params={
                    "function": "EARNINGS_CALENDAR",
                    "symbol": ticker,
                    "horizon": "3month",
                    "apikey": self.api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            # Alpha Vantage returns CSV: symbol,name,reportDate,fiscalDateEnding,estimate,currency
            lines = resp.text.strip().splitlines()
            earnings_date = None
            today = date.today()
            for line in lines[1:]:  # skip header
                parts = line.split(",")
                if len(parts) < 3:
                    continue
                symbol = parts[0].strip()
                if symbol.upper() != ticker.upper():
                    continue
                try:
                    report_date = date.fromisoformat(parts[2].strip())
                    if report_date >= today:
                        earnings_date = report_date
                        break
                except ValueError:
                    continue
            self._cache[ticker] = earnings_date
            return earnings_date
        except Exception as e:
            logger.warning(f"Could not fetch earnings date for {ticker}: {e}")
            self._cache[ticker] = None
            return None

    def blocks_entry(self, ticker: str) -> bool:
        """True if earnings are within ENTRY_BLOCK_DAYS — do not open new position."""
        earnings = self.next_earnings_date(ticker)
        if not earnings:
            return False
        days_until = (earnings - date.today()).days
        blocked = 0 <= days_until <= ENTRY_BLOCK_DAYS
        if blocked:
            logger.info(f"{ticker}: entry blocked — earnings in {days_until} days ({earnings})")
        return blocked

    def should_pre_close(self, ticker: str) -> bool:
        """True if earnings are within PRE_CLOSE_DAYS — close existing position."""
        earnings = self.next_earnings_date(ticker)
        if not earnings:
            return False
        days_until = (earnings - date.today()).days
        close = 0 <= days_until <= PRE_CLOSE_DAYS
        if close:
            logger.info(f"{ticker}: pre-close triggered — earnings in {days_until} days ({earnings})")
        return close
