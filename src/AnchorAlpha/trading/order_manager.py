"""
Order manager — trade logging and exit decision logic.
Handles take-profit, stop-loss, max-hold, Friday review, and 3-day score decline exit.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "anchor-alpha-momentum-data-prod-013523127218")
RESEARCH_TRADES_PREFIX = "research/trades/"
LIVE_TRADES_PREFIX = "live/trades/"

TAKE_PROFIT_PCT = 0.20   # +20%
STOP_LOSS_PCT = 0.10     # -10%
MAX_SCORE_DECLINE_DAYS = 3  # close if score drops 3 consecutive days


@dataclass
class TradeLog:
    ticker: str
    config_or_profile_id: str
    mode: str              # "research" or "live"
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    qty: float
    pnl_pct: float
    pnl_usd: float
    exit_reason: str       # "take_profit" | "stop_loss" | "max_hold" | "friday_review" |
                           # "score_decline" | "earnings_pre_close" | "emergency_stop"
    score_at_entry: float
    score_at_exit: float


class OrderManager:
    def __init__(self):
        self.s3 = boto3.client("s3")

    # ── Exit decisions ─────────────────────────────────────────────────────

    def should_exit(
        self,
        position,
        current_price: float,
        current_score: float,
        score_threshold: float,
        is_friday_review: bool = False,
    ) -> tuple[bool, str]:
        """
        Returns (should_exit, reason).
        Checks all exit rules in priority order.
        """
        pnl_pct = (current_price - position.entry_price) / position.entry_price

        # 1. Stop-loss
        if pnl_pct <= -STOP_LOSS_PCT:
            return True, "stop_loss"

        # 2. Take-profit
        if pnl_pct >= TAKE_PROFIT_PCT:
            return True, "take_profit"

        # 3. Score declined 3 consecutive days
        if position.consecutive_down_score_days >= MAX_SCORE_DECLINE_DAYS:
            return True, "score_decline"

        # 4. Max hold reached and score below threshold
        if position.is_max_hold_reached and current_score < score_threshold:
            return True, "max_hold"

        # 5. Friday review — close if score below threshold OR at a loss
        if is_friday_review:
            if current_score < score_threshold:
                return True, "friday_review"
            if pnl_pct < 0:
                return True, "friday_review"
            if position.age_days >= 18:
                return True, "friday_review"

        return False, ""

    def update_score_streak(self, position, current_score: float, previous_score: float):
        """Increment or reset the consecutive down-score counter."""
        if current_score < previous_score:
            position.consecutive_down_score_days += 1
        else:
            position.consecutive_down_score_days = 0
        return position

    # ── Trade logging ──────────────────────────────────────────────────────

    def log_trade(self, trade: TradeLog) -> None:
        today = date.today().isoformat()
        prefix = LIVE_TRADES_PREFIX if trade.mode == "live" else RESEARCH_TRADES_PREFIX
        key = f"{prefix}{trade.config_or_profile_id}/{today}/{trade.ticker}.json"
        self.s3.put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps(asdict(trade), indent=2),
            ContentType="application/json",
        )
        logger.info(
            f"Trade logged: {trade.ticker} {trade.mode} "
            f"pnl={trade.pnl_pct:.1%} reason={trade.exit_reason}"
        )

    def load_trades(self, mode: str, config_or_profile_id: str) -> list[TradeLog]:
        prefix = LIVE_TRADES_PREFIX if mode == "live" else RESEARCH_TRADES_PREFIX
        key_prefix = f"{prefix}{config_or_profile_id}/"
        trades = []
        try:
            resp = self.s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=key_prefix)
            for obj in resp.get("Contents", []):
                raw = self.s3.get_object(Bucket=S3_BUCKET, Key=obj["Key"])
                data = json.loads(raw["Body"].read())
                trades.append(TradeLog(**data))
        except Exception as e:
            logger.error(f"Failed to load trades: {e}")
        return trades

    def compute_analytics(self, trades: list[TradeLog]) -> dict:
        if not trades:
            return {"total_trades": 0}
        wins = [t for t in trades if t.pnl_pct > 0]
        losses = [t for t in trades if t.pnl_pct <= 0]
        return {
            "total_trades": len(trades),
            "win_rate": len(wins) / len(trades),
            "avg_pnl_pct": sum(t.pnl_pct for t in trades) / len(trades),
            "avg_win_pct": sum(t.pnl_pct for t in wins) / len(wins) if wins else 0,
            "avg_loss_pct": sum(t.pnl_pct for t in losses) / len(losses) if losses else 0,
            "total_pnl_usd": sum(t.pnl_usd for t in trades),
            "exit_reasons": _count_reasons(trades),
        }


def _count_reasons(trades: list[TradeLog]) -> dict:
    counts: dict = {}
    for t in trades:
        counts[t.exit_reason] = counts.get(t.exit_reason, 0) + 1
    return counts
