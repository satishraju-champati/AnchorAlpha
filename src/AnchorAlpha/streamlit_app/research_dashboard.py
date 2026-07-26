"""
Research tab — paper trading configs, open positions, trade history, and analytics.
Reads all data from S3. No write operations from the dashboard.
"""

import json
import logging
import os
from datetime import date, datetime
from typing import Optional

import boto3
import pandas as pd
import streamlit as st
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "anchor-alpha-momentum-data-prod-013523127218")
RESEARCH_CONFIG_PREFIX = "research/configs/"
RESEARCH_POSITIONS_PREFIX = "research/positions/"
RESEARCH_TRADES_PREFIX = "research/trades/"


# ── S3 helpers ─────────────────────────────────────────────────────────────────

def _s3():
    return boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))


@st.cache_data(ttl=60)
def load_research_configs() -> list[dict]:
    try:
        client = _s3()
        resp = client.list_objects_v2(Bucket=S3_BUCKET, Prefix=RESEARCH_CONFIG_PREFIX)
        configs = []
        for obj in resp.get("Contents", []):
            if not obj["Key"].endswith(".json"):
                continue
            raw = client.get_object(Bucket=S3_BUCKET, Key=obj["Key"])
            configs.append(json.loads(raw["Body"].read()))
        return sorted(configs, key=lambda c: c.get("config_id", ""))
    except Exception as e:
        logger.warning(f"Could not load research configs: {e}")
        return []


@st.cache_data(ttl=60)
def load_open_positions(config_id: str) -> list[dict]:
    key = f"{RESEARCH_POSITIONS_PREFIX}{config_id}/open.json"
    try:
        raw = _s3().get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(raw["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return []
        logger.warning(f"Could not load positions for {config_id}: {e}")
        return []
    except Exception as e:
        logger.warning(f"Could not load positions for {config_id}: {e}")
        return []


@st.cache_data(ttl=120)
def load_all_trades(config_id: str) -> list[dict]:
    prefix = f"{RESEARCH_TRADES_PREFIX}{config_id}/"
    trades = []
    try:
        client = _s3()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                raw = client.get_object(Bucket=S3_BUCKET, Key=obj["Key"])
                trades.append(json.loads(raw["Body"].read()))
    except Exception as e:
        logger.warning(f"Could not load trades for {config_id}: {e}")
    return trades


# ── Analytics ──────────────────────────────────────────────────────────────────

def compute_analytics(trades: list[dict]) -> dict:
    if not trades:
        return {}
    wins = [t for t in trades if t.get("pnl_pct", 0) > 0]
    losses = [t for t in trades if t.get("pnl_pct", 0) <= 0]
    return {
        "total": len(trades),
        "win_rate": len(wins) / len(trades) * 100,
        "avg_pnl_pct": sum(t.get("pnl_pct", 0) for t in trades) / len(trades) * 100,
        "total_pnl_usd": sum(t.get("pnl_usd", 0) for t in trades),
        "avg_win_pct": sum(t.get("pnl_pct", 0) for t in wins) / len(wins) * 100 if wins else 0,
        "avg_loss_pct": sum(t.get("pnl_pct", 0) for t in losses) / len(losses) * 100 if losses else 0,
    }


# ── UI components ──────────────────────────────────────────────────────────────

def _pnl_color(pnl: float) -> str:
    return "🟢" if pnl > 0 else "🔴"


def _render_config_card(cfg: dict, positions: list[dict], trades: list[dict]):
    analytics = compute_analytics(trades)
    status = "🟢 Active" if cfg.get("active", True) else "⚫ Inactive"
    with st.expander(f"**{cfg.get('name', cfg.get('config_id'))}** — {status}", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Score threshold", f"{cfg.get('score_threshold', 0.75):.0%}")
        col2.metric("Max positions", cfg.get("max_positions", 5))
        col3.metric("Open now", len(positions))
        col4.metric("Trades closed", analytics.get("total", 0))

        if analytics.get("total", 0) > 0:
            st.markdown("**Performance**")
            m1, m2, m3, m4 = st.columns(4)
            wr = analytics["win_rate"]
            pnl = analytics["avg_pnl_pct"]
            m1.metric("Win rate", f"{wr:.1f}%")
            m2.metric("Avg P&L / trade", f"{pnl:+.1f}%")
            m3.metric("Total P&L", f"${analytics['total_pnl_usd']:+,.0f}")
            m4.metric("Avg win / Avg loss",
                      f"{analytics['avg_win_pct']:.1f}% / {analytics['avg_loss_pct']:.1f}%")

        if positions:
            st.markdown("**Open positions**")
            rows = []
            for p in positions:
                entry = p.get("entry_price", 0)
                age = (date.today() - date.fromisoformat(p["entry_date"])).days
                rows.append({
                    "Ticker": p["ticker"],
                    "Entry price": f"${entry:.2f}",
                    "Entry date": p["entry_date"],
                    "Age (days)": age,
                    "Score at entry": f"{p.get('score_at_entry', 0):.2f}",
                    "Qty": f"{p.get('qty', 0):.4f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if trades:
            st.markdown("**Closed trades**")
            rows = []
            for t in sorted(trades, key=lambda x: x.get("exit_date", ""), reverse=True)[:50]:
                pnl = t.get("pnl_pct", 0) * 100
                rows.append({
                    "Ticker": t["ticker"],
                    "Entry": t.get("entry_date", ""),
                    "Exit": t.get("exit_date", ""),
                    "Entry $": f"${t.get('entry_price', 0):.2f}",
                    "Exit $": f"${t.get('exit_price', 0):.2f}",
                    "P&L %": f"{_pnl_color(pnl)} {pnl:+.1f}%",
                    "P&L $": f"${t.get('pnl_usd', 0):+,.0f}",
                    "Reason": t.get("exit_reason", ""),
                    "Score in/out": f"{t.get('score_at_entry', 0):.2f} → {t.get('score_at_exit', 0):.2f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_summary_header(configs: list[dict], all_positions: list[dict], all_trades: list[dict]):
    total_open = len(all_positions)
    analytics = compute_analytics(all_trades)

    st.markdown("### 🔬 Research — Paper Trading")
    st.caption(f"8 configs · {total_open} open positions · {len(all_trades)} trades closed")

    if analytics.get("total", 0) > 0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total trades", analytics["total"])
        c2.metric("Win rate", f"{analytics['win_rate']:.1f}%")
        c3.metric("Avg P&L / trade", f"{analytics['avg_pnl_pct']:+.1f}%")
        c4.metric("Total P&L (all configs)", f"${analytics['total_pnl_usd']:+,.0f}")
    else:
        st.info("No closed trades yet. The trading engine will start placing paper orders during market hours.")


# ── Entry point ────────────────────────────────────────────────────────────────

def render():
    configs = load_research_configs()

    if not configs:
        st.markdown("### 🔬 Research — Paper Trading")
        st.info(
            "No research configs found in S3 yet. "
            "They are created automatically when the trading engine starts for the first time."
        )
        st.caption(f"Looking in: `s3://{S3_BUCKET}/{RESEARCH_CONFIG_PREFIX}`")
        return

    # Load all positions and trades once
    all_positions: list[dict] = []
    positions_by_config: dict[str, list[dict]] = {}
    trades_by_config: dict[str, list[dict]] = {}

    for cfg in configs:
        cid = cfg["config_id"]
        positions = load_open_positions(cid)
        trades = load_all_trades(cid)
        positions_by_config[cid] = positions
        trades_by_config[cid] = trades
        all_positions.extend(positions)

    all_trades = [t for trades in trades_by_config.values() for t in trades]

    _render_summary_header(configs, all_positions, all_trades)
    st.divider()

    for cfg in configs:
        cid = cfg["config_id"]
        _render_config_card(cfg, positions_by_config[cid], trades_by_config[cid])

    st.caption(f"Data refreshes every 60s · S3 bucket: `{S3_BUCKET}`")
