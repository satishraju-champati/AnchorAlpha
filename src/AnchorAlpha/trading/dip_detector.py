"""
Dip detection logic.
Detects drawdown >= -10% from 10-day high (single-day and multi-day).
Applies confirmation logic before signalling entry.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DIP_THRESHOLD = -0.10        # -10% drawdown from 10-day high triggers watch
SINGLE_DAY_MAX_CONT = -0.05  # single-day dip: day+1 additional drop must be 0% to -5%
MIN_HISTORY_DAYS = 10


@dataclass
class DipSignal:
    ticker: str
    dip_type: str              # "single_day" or "multi_day"
    drawdown_pct: float        # total drawdown from 10-day high (negative)
    entry_ready: bool          # True = confirmation passed, ok to buy
    ten_day_high: float
    current_price: float
    days_in_dip: int


def detect_dip(ticker: str, prices: list[float]) -> Optional[DipSignal]:
    """
    Analyse a list of daily closing prices (oldest first, today last).
    Returns a DipSignal if a dip is detected, None otherwise.
    prices must have at least 11 elements (10 history days + today).
    """
    if len(prices) < MIN_HISTORY_DAYS + 1:
        logger.warning(f"{ticker}: not enough price history ({len(prices)} days)")
        return None

    today = prices[-1]
    window = prices[-MIN_HISTORY_DAYS - 1: -1]  # 10 days before today
    ten_day_high = max(window)
    drawdown = (today - ten_day_high) / ten_day_high  # negative number

    if drawdown >= DIP_THRESHOLD:
        return None  # no dip

    yesterday = prices[-2]
    day_before = prices[-3] if len(prices) >= 3 else None

    single_day_drop = (today - yesterday) / yesterday if yesterday > 0 else 0
    is_single_day = single_day_drop <= DIP_THRESHOLD

    if is_single_day:
        # Single-day dip: entered all at once yesterday-to-today
        # Confirmation: today's additional drop is between 0% and -5%
        # (already happened — price decelerated or stabilised)
        entry_ready = SINGLE_DAY_MAX_CONT <= single_day_drop <= 0.0
        days_in_dip = 1
    else:
        # Multi-day dip: gradual decline over multiple days
        # Find how many consecutive days the stock has been falling
        days_in_dip = _count_consecutive_down_days(prices)

        if days_in_dip < 2:
            return None  # not enough data for multi-day confirmation

        # Confirmation: most recent day's drop has decelerated vs average daily drop
        avg_daily_drop = drawdown / days_in_dip
        entry_ready = single_day_drop > avg_daily_drop  # deceleration = less negative

    dip_type = "single_day" if is_single_day else "multi_day"
    logger.info(
        f"{ticker}: {dip_type} dip detected "
        f"drawdown={drawdown:.1%} entry_ready={entry_ready}"
    )
    return DipSignal(
        ticker=ticker,
        dip_type=dip_type,
        drawdown_pct=drawdown,
        entry_ready=entry_ready,
        ten_day_high=ten_day_high,
        current_price=today,
        days_in_dip=days_in_dip,
    )


def _count_consecutive_down_days(prices: list[float]) -> int:
    """Count how many consecutive days (ending today) price has been below 10-day high."""
    if len(prices) < MIN_HISTORY_DAYS + 1:
        return 0
    window_start = len(prices) - MIN_HISTORY_DAYS - 1
    ten_day_high = max(prices[window_start: len(prices) - 1])
    count = 0
    for price in reversed(prices):
        if price < ten_day_high:
            count += 1
        else:
            break
    return count
