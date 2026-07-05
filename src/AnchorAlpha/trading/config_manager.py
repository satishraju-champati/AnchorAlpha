"""
Config manager — reads and writes research configs and live profiles from S3.
All trading parameters live in S3 JSON files. The engine polls these each cycle.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "anchor-alpha-momentum-data-prod-013523127218")

RESEARCH_CONFIG_PREFIX = "research/configs/"
LIVE_CONFIG_PREFIX = "live/configs/"
GLOBAL_SETTINGS_KEY = "live/global_settings.json"

AI_SECTOR_STOCKS = [
    "NVDA", "AMD", "INTC", "AVGO", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "MRVL",
    "MSFT", "GOOGL", "AMZN", "META", "AAPL",
    "TSM", "ASML", "ARM",
    "ORCL", "CRM", "SNOW", "PLTR", "DDOG", "NET", "ZS",
    "ANET", "CSCO",
    "SMCI", "DELL", "HPE",
    "AI", "SOUN", "BBAI",
    "PANW", "CRWD",
]


@dataclass
class ResearchConfig:
    config_id: str
    name: str
    active: bool = True
    sectors: list = field(default_factory=lambda: ["AI/Semiconductors"])
    score_threshold: float = 0.75
    max_positions: int = 5
    capital_pct: float = 30.0
    take_profit_pct: float = 20.0
    stop_loss_pct: float = 10.0
    max_hold_days: int = 20
    earnings_protection: bool = True
    dip_threshold_pct: float = 10.0
    use_sonnet: bool = False   # False = Haiku for research (cost saving)


@dataclass
class LiveProfile:
    profile_id: str
    name: str
    sector: str
    active: bool = True
    capital_usd: float = 50000.0
    score_threshold: float = 0.75
    max_positions: int = 5
    take_profit_pct: float = 20.0
    stop_loss_pct: float = 10.0
    max_hold_days: int = 20
    earnings_protection: bool = True
    use_sonnet: bool = True   # True = Sonnet for live (quality)


@dataclass
class GlobalSettings:
    emergency_stop: bool = False
    market_filter_active: bool = True
    spy_ma_days: int = 200
    soxx_ma_days: int = 200


class ConfigManager:
    def __init__(self):
        self.s3 = boto3.client("s3")

    # ── Research configs ───────────────────────────────────────────────────

    def load_research_configs(self) -> list[ResearchConfig]:
        configs = []
        try:
            resp = self.s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=RESEARCH_CONFIG_PREFIX)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                if not key.endswith(".json"):
                    continue
                raw = self.s3.get_object(Bucket=S3_BUCKET, Key=key)
                data = json.loads(raw["Body"].read())
                configs.append(ResearchConfig(**data))
        except Exception as e:
            logger.error(f"Failed to load research configs: {e}")
        return [c for c in configs if c.active]

    def save_research_config(self, config: ResearchConfig) -> None:
        key = f"{RESEARCH_CONFIG_PREFIX}{config.config_id}.json"
        self.s3.put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps(asdict(config), indent=2),
            ContentType="application/json",
        )
        logger.info(f"Saved research config: {config.config_id}")

    # ── Live profiles ──────────────────────────────────────────────────────

    def load_live_profiles(self) -> list[LiveProfile]:
        profiles = []
        try:
            resp = self.s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=LIVE_CONFIG_PREFIX)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                if not key.endswith(".json"):
                    continue
                raw = self.s3.get_object(Bucket=S3_BUCKET, Key=key)
                data = json.loads(raw["Body"].read())
                profiles.append(LiveProfile(**data))
        except Exception as e:
            logger.error(f"Failed to load live profiles: {e}")
        return [p for p in profiles if p.active]

    def save_live_profile(self, profile: LiveProfile) -> None:
        key = f"{LIVE_CONFIG_PREFIX}{profile.profile_id}.json"
        self.s3.put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps(asdict(profile), indent=2),
            ContentType="application/json",
        )
        logger.info(f"Saved live profile: {profile.profile_id}")

    # ── Global settings ────────────────────────────────────────────────────

    def load_global_settings(self) -> GlobalSettings:
        try:
            raw = self.s3.get_object(Bucket=S3_BUCKET, Key=GLOBAL_SETTINGS_KEY)
            data = json.loads(raw["Body"].read())
            return GlobalSettings(**data)
        except self.s3.exceptions.NoSuchKey:
            settings = GlobalSettings()
            self.save_global_settings(settings)
            return settings
        except Exception as e:
            logger.error(f"Failed to load global settings: {e}")
            return GlobalSettings()

    def save_global_settings(self, settings: GlobalSettings) -> None:
        self.s3.put_object(
            Bucket=S3_BUCKET, Key=GLOBAL_SETTINGS_KEY,
            Body=json.dumps(asdict(settings), indent=2),
            ContentType="application/json",
        )

    def is_emergency_stop(self) -> bool:
        return self.load_global_settings().emergency_stop

    # ── Seed default research configs ──────────────────────────────────────

    def seed_default_research_configs(self) -> None:
        """Write the 8 default research configs if none exist."""
        existing = self.load_research_configs()
        if existing:
            return
        defaults = [
            ResearchConfig("config_1", "AI Semis — Low (0.60)", score_threshold=0.60, sectors=["AI/Semiconductors"]),
            ResearchConfig("config_2", "AI Semis — Standard (0.75)", score_threshold=0.75, sectors=["AI/Semiconductors"]),
            ResearchConfig("config_3", "Cloud SaaS — Low (0.60)", score_threshold=0.60, sectors=["Cloud/SaaS"]),
            ResearchConfig("config_4", "Cloud SaaS — Standard (0.75)", score_threshold=0.75, sectors=["Cloud/SaaS"]),
            ResearchConfig("config_5", "Fintech — Standard (0.75)", score_threshold=0.75, sectors=["Fintech"]),
            ResearchConfig("config_6", "Healthcare — Standard (0.75)", score_threshold=0.75, sectors=["Healthcare/Biotech"]),
            ResearchConfig("config_7", "Energy — Standard (0.75)", score_threshold=0.75, sectors=["Energy"]),
            ResearchConfig("config_8", "Broad Large-cap — Mid (0.65)", score_threshold=0.65, sectors=["All"]),
        ]
        for config in defaults:
            self.save_research_config(config)
        logger.info("Seeded 8 default research configs")
