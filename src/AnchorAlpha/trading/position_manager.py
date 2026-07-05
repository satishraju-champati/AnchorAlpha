"""
Position manager — tracks open positions in S3.
Enforces global stock conflict rule: one open position per ticker across all live profiles.
Research paper trades are exempt from the conflict check.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "anchor-alpha-momentum-data-prod-013523127218")
LIVE_POSITIONS_KEY = "live/positions/open.json"
RESEARCH_POSITIONS_PREFIX = "research/positions/"


@dataclass
class OpenPosition:
    ticker: str
    profile_id: str        # config_id for research, profile_id for live
    mode: str              # "research" or "live"
    entry_price: float
    qty: float
    entry_date: str        # ISO format YYYY-MM-DD
    alpaca_order_id: str
    take_profit_pct: float
    stop_loss_pct: float
    max_hold_days: int
    score_at_entry: float
    consecutive_down_score_days: int = 0  # for 3-day decline exit rule

    @property
    def age_days(self) -> int:
        return (date.today() - date.fromisoformat(self.entry_date)).days

    @property
    def is_max_hold_reached(self) -> bool:
        return self.age_days >= self.max_hold_days


class PositionManager:
    def __init__(self):
        self.s3 = boto3.client("s3")

    # ── Live positions ─────────────────────────────────────────────────────

    def load_live_positions(self) -> list[OpenPosition]:
        try:
            raw = self.s3.get_object(Bucket=S3_BUCKET, Key=LIVE_POSITIONS_KEY)
            data = json.loads(raw["Body"].read())
            return [OpenPosition(**p) for p in data]
        except self.s3.exceptions.NoSuchKey:
            return []
        except Exception as e:
            logger.error(f"Failed to load live positions: {e}")
            return []

    def save_live_positions(self, positions: list[OpenPosition]) -> None:
        self.s3.put_object(
            Bucket=S3_BUCKET, Key=LIVE_POSITIONS_KEY,
            Body=json.dumps([asdict(p) for p in positions], indent=2),
            ContentType="application/json",
        )

    def is_ticker_taken_live(self, ticker: str) -> bool:
        """Global conflict check: returns True if any live profile holds this ticker."""
        positions = self.load_live_positions()
        return any(p.ticker == ticker for p in positions)

    def add_live_position(self, position: OpenPosition) -> None:
        positions = self.load_live_positions()
        positions.append(position)
        self.save_live_positions(positions)
        logger.info(f"Added live position: {position.ticker} profile={position.profile_id}")

    def remove_live_position(self, ticker: str, profile_id: str) -> None:
        positions = self.load_live_positions()
        positions = [p for p in positions if not (p.ticker == ticker and p.profile_id == profile_id)]
        self.save_live_positions(positions)
        logger.info(f"Removed live position: {ticker} profile={profile_id}")

    def update_live_position(self, updated: OpenPosition) -> None:
        positions = self.load_live_positions()
        for i, p in enumerate(positions):
            if p.ticker == updated.ticker and p.profile_id == updated.profile_id:
                positions[i] = updated
                break
        self.save_live_positions(positions)

    def get_live_positions_for_profile(self, profile_id: str) -> list[OpenPosition]:
        return [p for p in self.load_live_positions() if p.profile_id == profile_id]

    # ── Research positions ─────────────────────────────────────────────────

    def load_research_positions(self, config_id: str) -> list[OpenPosition]:
        key = f"{RESEARCH_POSITIONS_PREFIX}{config_id}/open.json"
        try:
            raw = self.s3.get_object(Bucket=S3_BUCKET, Key=key)
            data = json.loads(raw["Body"].read())
            return [OpenPosition(**p) for p in data]
        except self.s3.exceptions.NoSuchKey:
            return []
        except Exception as e:
            logger.error(f"Failed to load research positions for {config_id}: {e}")
            return []

    def save_research_positions(self, config_id: str, positions: list[OpenPosition]) -> None:
        key = f"{RESEARCH_POSITIONS_PREFIX}{config_id}/open.json"
        self.s3.put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps([asdict(p) for p in positions], indent=2),
            ContentType="application/json",
        )

    def add_research_position(self, config_id: str, position: OpenPosition) -> None:
        positions = self.load_research_positions(config_id)
        positions.append(position)
        self.save_research_positions(config_id, positions)
        logger.info(f"Added research position: {position.ticker} config={config_id}")

    def remove_research_position(self, config_id: str, ticker: str) -> None:
        positions = self.load_research_positions(config_id)
        positions = [p for p in positions if p.ticker != ticker]
        self.save_research_positions(config_id, positions)

    def update_research_position(self, config_id: str, updated: OpenPosition) -> None:
        positions = self.load_research_positions(config_id)
        for i, p in enumerate(positions):
            if p.ticker == updated.ticker:
                positions[i] = updated
                break
        self.save_research_positions(config_id, positions)
