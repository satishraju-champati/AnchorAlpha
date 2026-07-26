"""
Research tab — paper trading configs with inline editors, open positions, trade history, analytics.
Config edits write directly to S3 (no password required for research).
Global settings (emergency stop, market filter) also saved to S3.
"""

import json
import logging
import os
import time
from datetime import date
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
GLOBAL_SETTINGS_KEY = "live/global_settings.json"


LIVE_CONFIG_PREFIX = "live/configs/"


# ── S3 helpers ─────────────────────────────────────────────────────────────────

def _s3():
    return boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))


@st.cache_data(ttl=30)
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


@st.cache_data(ttl=30)
def load_global_settings() -> dict:
    try:
        raw = _s3().get_object(Bucket=S3_BUCKET, Key=GLOBAL_SETTINGS_KEY)
        return json.loads(raw["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return {"emergency_stop": False, "market_filter_active": True,
                    "spy_ma_days": 200, "soxx_ma_days": 200}
        return {}
    except Exception:
        return {}


@st.cache_data(ttl=60)
def load_open_positions(config_id: str) -> list[dict]:
    key = f"{RESEARCH_POSITIONS_PREFIX}{config_id}/open.json"
    try:
        raw = _s3().get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(raw["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return []
        return []
    except Exception:
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


# ── S3 writers ─────────────────────────────────────────────────────────────────

def save_config(cfg: dict) -> bool:
    key = f"{RESEARCH_CONFIG_PREFIX}{cfg['config_id']}.json"
    try:
        _s3().put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps(cfg, indent=2),
            ContentType="application/json",
        )
        load_research_configs.clear()
        return True
    except Exception as e:
        logger.error(f"Failed to save config {cfg['config_id']}: {e}")
        return False


def save_global_settings(settings: dict) -> bool:
    try:
        _s3().put_object(
            Bucket=S3_BUCKET, Key=GLOBAL_SETTINGS_KEY,
            Body=json.dumps(settings, indent=2),
            ContentType="application/json",
        )
        load_global_settings.clear()
        return True
    except Exception as e:
        logger.error(f"Failed to save global settings: {e}")
        return False


# ── Promote to Live ────────────────────────────────────────────────────────────

def _promote_to_live(cfg: dict):
    pid = f"live_from_{cfg['config_id']}"
    profile = {
        "profile_id": pid,
        "name": f"From Research: {cfg.get('name', cfg['config_id'])}",
        "sector": cfg.get("sectors", ["AI / Semiconductors"])[0] if cfg.get("sectors") else "AI / Semiconductors",
        "active": False,
        "capital_usd": 50000.0,
        "score_threshold": cfg.get("score_threshold", 0.75),
        "max_positions": cfg.get("max_positions", 5),
        "take_profit_pct": cfg.get("take_profit_pct", 20.0),
        "stop_loss_pct": cfg.get("stop_loss_pct", 10.0),
        "max_hold_days": cfg.get("max_hold_days", 20),
        "earnings_protection": cfg.get("earnings_protection", True),
        "use_sonnet": True,
    }
    key = f"{LIVE_CONFIG_PREFIX}{pid}.json"
    try:
        _s3().put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps(profile, indent=2),
            ContentType="application/json",
        )
        st.success(f"✅ Promoted to Live. Go to the Live tab to review and activate '{profile['name']}'.")
    except Exception as e:
        st.error(f"Promote failed: {e}")


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


# ── Global controls ────────────────────────────────────────────────────────────

def _render_global_controls(settings: dict):
    st.markdown("#### ⚙️ Global Controls")
    col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])

    emergency_stop = col1.toggle(
        "🛑 Emergency Stop",
        value=settings.get("emergency_stop", False),
        key="global_emergency_stop",
        help="Halts ALL trading immediately across research and live engines.",
    )
    market_filter = col2.toggle(
        "📊 Market Filter (SPY/SOXX MA)",
        value=settings.get("market_filter_active", True),
        key="global_market_filter",
        help="Only allow entries when SPY and SOXX are above their moving averages.",
    )
    spy_days = col3.number_input(
        "SPY MA days", min_value=50, max_value=500,
        value=int(settings.get("spy_ma_days", 200)),
        step=10, key="global_spy_days",
    )
    soxx_days = col4.number_input(
        "SOXX MA days", min_value=50, max_value=500,
        value=int(settings.get("soxx_ma_days", 200)),
        step=10, key="global_soxx_days",
    )

    new_settings = {
        "emergency_stop": emergency_stop,
        "market_filter_active": market_filter,
        "spy_ma_days": int(spy_days),
        "soxx_ma_days": int(soxx_days),
    }

    if new_settings != {k: settings.get(k) for k in new_settings}:
        if save_global_settings(new_settings):
            if emergency_stop and not settings.get("emergency_stop"):
                st.error("🛑 Emergency stop ACTIVATED — all trading halted.")
            elif not emergency_stop and settings.get("emergency_stop"):
                st.success("✅ Emergency stop cleared — trading can resume.")
            else:
                st.success("Global settings saved.")
            st.rerun()

    if settings.get("emergency_stop"):
        st.error("🛑 **EMERGENCY STOP IS ACTIVE** — all trading is halted.", icon="🛑")


# ── Config editor ──────────────────────────────────────────────────────────────

def _render_config_card(cfg: dict, positions: list[dict], trades: list[dict]):
    analytics = compute_analytics(trades)
    cid = cfg["config_id"]
    is_active = cfg.get("active", True)
    status_label = "🟢 Active" if is_active else "⚫ Inactive"

    with st.expander(f"**{cfg.get('name', cid)}** — {status_label}", expanded=False):

        # ── Performance summary ────────────────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Open positions", len(positions))
        c2.metric("Trades closed", analytics.get("total", 0))
        if analytics.get("total", 0) > 0:
            c3.metric("Win rate", f"{analytics['win_rate']:.1f}%")
            c4.metric("Avg P&L / trade", f"{analytics['avg_pnl_pct']:+.1f}%")
            c5.metric("Total P&L", f"${analytics['total_pnl_usd']:+,.0f}")

        st.divider()

        # ── Config editor ──────────────────────────────────────────────────────
        st.markdown("**⚙️ Config Parameters**")
        e1, e2 = st.columns(2)

        with e1:
            new_active = st.toggle("Active", value=is_active, key=f"{cid}_active",
                                   help="Disable to pause this config without deleting it.")
            new_threshold = st.slider(
                "Score threshold", 0.50, 0.95,
                value=float(cfg.get("score_threshold", 0.75)),
                step=0.05, key=f"{cid}_threshold",
                help="Minimum Claude score required to open a new position.",
            )
            new_max_pos = st.number_input(
                "Max open positions", 1, 10,
                value=int(cfg.get("max_positions", 5)),
                key=f"{cid}_max_pos",
            )
            new_capital = st.slider(
                "Capital % of portfolio", 5.0, 80.0,
                value=float(cfg.get("capital_pct", 30.0)),
                step=5.0, key=f"{cid}_capital",
                help="Percentage of paper portfolio allocated to this config.",
            )

        with e2:
            new_tp = st.slider(
                "Take-profit %", 5, 50,
                value=int(cfg.get("take_profit_pct", 20)),
                step=5, key=f"{cid}_tp",
            )
            new_sl = st.slider(
                "Stop-loss %", 3, 25,
                value=int(cfg.get("stop_loss_pct", 10)),
                step=1, key=f"{cid}_sl",
            )
            new_hold = st.number_input(
                "Max hold days", 5, 60,
                value=int(cfg.get("max_hold_days", 20)),
                key=f"{cid}_hold",
            )
            new_earnings = st.toggle(
                "Earnings protection",
                value=cfg.get("earnings_protection", True),
                key=f"{cid}_earnings",
                help="Block entries 3 days before earnings; close positions 2 days before.",
            )

        btn_col1, btn_col2 = st.columns([2, 1])
        if btn_col1.button("💾 Save changes", key=f"{cid}_save", type="primary"):
            updated = {**cfg,
                "active": new_active,
                "score_threshold": round(new_threshold, 2),
                "max_positions": int(new_max_pos),
                "capital_pct": float(new_capital),
                "take_profit_pct": float(new_tp),
                "stop_loss_pct": float(new_sl),
                "max_hold_days": int(new_hold),
                "earnings_protection": new_earnings,
            }
            if save_config(updated):
                st.success(f"✅ {cfg['name']} saved.")
                st.rerun()
            else:
                st.error("Failed to save — check AWS credentials.")

        if st.session_state.get("admin_authenticated"):
            if btn_col2.button("🚀 Promote to Live", key=f"{cid}_promote"):
                _promote_to_live(cfg)
        else:
            btn_col2.caption("🔐 Login as admin in the Live tab to promote")

        # ── Open positions ─────────────────────────────────────────────────────
        if positions:
            st.divider()
            st.markdown("**📂 Open Positions**")
            rows = []
            for p in positions:
                age = (date.today() - date.fromisoformat(p["entry_date"])).days
                rows.append({
                    "Ticker": p["ticker"],
                    "Entry $": f"${p.get('entry_price', 0):.2f}",
                    "Entry date": p["entry_date"],
                    "Age (days)": age,
                    "Score at entry": f"{p.get('score_at_entry', 0):.2f}",
                    "Qty": f"{p.get('qty', 0):.4f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Closed trades ──────────────────────────────────────────────────────
        if trades:
            st.divider()
            st.markdown("**📋 Closed Trades**")
            rows = []
            for t in sorted(trades, key=lambda x: x.get("exit_date", ""), reverse=True)[:50]:
                pnl = t.get("pnl_pct", 0) * 100
                rows.append({
                    "Ticker": t["ticker"],
                    "Entry": t.get("entry_date", ""),
                    "Exit": t.get("exit_date", ""),
                    "Entry $": f"${t.get('entry_price', 0):.2f}",
                    "Exit $": f"${t.get('exit_price', 0):.2f}",
                    "P&L %": f"{'▲' if pnl > 0 else '▼'} {pnl:+.1f}%",
                    "P&L $": f"${t.get('pnl_usd', 0):+,.0f}",
                    "Reason": t.get("exit_reason", ""),
                    "Score in → out": f"{t.get('score_at_entry', 0):.2f} → {t.get('score_at_exit', 0):.2f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Summary header ─────────────────────────────────────────────────────────────

def _render_summary_header(configs: list[dict], all_positions: list[dict], all_trades: list[dict]):
    st.markdown("### 🔬 Research — Paper Trading")

    active = sum(1 for c in configs if c.get("active", True))
    analytics = compute_analytics(all_trades)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Configs", f"{active} / {len(configs)} active")
    c2.metric("Open positions", len(all_positions))
    c3.metric("Trades closed", analytics.get("total", 0))
    if analytics.get("total", 0) > 0:
        c4.metric("Overall win rate", f"{analytics['win_rate']:.1f}%")
        c5.metric("Total P&L", f"${analytics['total_pnl_usd']:+,.0f}")

    if analytics.get("total", 0) == 0:
        st.info(
            "No closed trades yet. The trading engine places paper orders during market hours "
            "(Mon–Fri 9:30 AM – 4:30 PM ET). Configs are seeded automatically on first run."
        )


# ── Entry point ────────────────────────────────────────────────────────────────

def render():
    settings = load_global_settings()
    _render_global_controls(settings)
    st.divider()

    configs = load_research_configs()

    if not configs:
        st.markdown("### 🔬 Research — Paper Trading")
        st.info(
            "No research configs in S3 yet. "
            "They are created automatically when the trading engine starts for the first time."
        )
        st.caption(f"Looking in: `s3://{S3_BUCKET}/{RESEARCH_CONFIG_PREFIX}`")
        return

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

    st.caption(f"Config edits save immediately to S3 and take effect on the next engine cycle · Bucket: `{S3_BUCKET}`")
