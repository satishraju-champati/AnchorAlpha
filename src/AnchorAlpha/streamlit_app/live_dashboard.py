"""
Live tab — real-money trading profiles with admin-gated controls.
Read-only: positions, P&L, trade history (open to all).
Write actions: enable/disable profiles, edit parameters, add profiles (admin only).
Admin session: password from ADMIN_PASSWORD env var, expires after 4 hours.
"""

import json
import logging
import os
import time
from datetime import date, datetime
from typing import Optional

import boto3
import pandas as pd
import streamlit as st
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "anchor-alpha-momentum-data-prod-013523127218")
LIVE_CONFIG_PREFIX = "live/configs/"
LIVE_POSITIONS_KEY = "live/positions/open.json"
LIVE_TRADES_PREFIX = "live/trades/"
GLOBAL_SETTINGS_KEY = "live/global_settings.json"
RESEARCH_CONFIG_PREFIX = "research/configs/"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ADMIN_SESSION_HOURS = 4

SECTORS = [
    "AI / Semiconductors",
    "Cloud / SaaS",
    "Fintech",
    "Healthcare / Biotech",
    "Energy",
    "Broad Large-cap",
]


# ── S3 helpers ─────────────────────────────────────────────────────────────────

def _s3():
    return boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))


@st.cache_data(ttl=30)
def load_live_profiles() -> list[dict]:
    try:
        client = _s3()
        resp = client.list_objects_v2(Bucket=S3_BUCKET, Prefix=LIVE_CONFIG_PREFIX)
        profiles = []
        for obj in resp.get("Contents", []):
            if not obj["Key"].endswith(".json"):
                continue
            raw = client.get_object(Bucket=S3_BUCKET, Key=obj["Key"])
            profiles.append(json.loads(raw["Body"].read()))
        return sorted(profiles, key=lambda p: (p.get("sector", ""), p.get("name", "")))
    except Exception as e:
        logger.warning(f"Could not load live profiles: {e}")
        return []


@st.cache_data(ttl=30)
def load_live_positions() -> list[dict]:
    try:
        raw = _s3().get_object(Bucket=S3_BUCKET, Key=LIVE_POSITIONS_KEY)
        return json.loads(raw["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return []
        return []
    except Exception:
        return []


@st.cache_data(ttl=120)
def load_live_trades(profile_id: str) -> list[dict]:
    prefix = f"{LIVE_TRADES_PREFIX}{profile_id}/"
    trades = []
    try:
        client = _s3()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                raw = client.get_object(Bucket=S3_BUCKET, Key=obj["Key"])
                trades.append(json.loads(raw["Body"].read()))
    except Exception as e:
        logger.warning(f"Could not load live trades for {profile_id}: {e}")
    return trades


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
    except Exception:
        return []


# ── S3 writers ─────────────────────────────────────────────────────────────────

def save_live_profile(profile: dict) -> bool:
    key = f"{LIVE_CONFIG_PREFIX}{profile['profile_id']}.json"
    try:
        _s3().put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps(profile, indent=2),
            ContentType="application/json",
        )
        load_live_profiles.clear()
        return True
    except Exception as e:
        logger.error(f"Failed to save live profile {profile['profile_id']}: {e}")
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


# ── Admin auth ─────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    if not ADMIN_PASSWORD:
        return False
    if not st.session_state.get("admin_authenticated"):
        return False
    elapsed = time.time() - st.session_state.get("admin_login_time", 0)
    if elapsed > ADMIN_SESSION_HOURS * 3600:
        st.session_state.admin_authenticated = False
        return False
    return True


def _render_admin_auth():
    admin = is_admin()
    if admin:
        col1, col2 = st.columns([8, 1])
        col1.success(f"🔐 Admin session active (expires in {_admin_minutes_left()} min)")
        if col2.button("Logout", key="live_admin_logout"):
            st.session_state.admin_authenticated = False
            st.rerun()
        return

    with st.expander("🔐 Admin Login (required to edit profiles)", expanded=False):
        pwd = st.text_input("Admin password", type="password", key="live_pwd_input")
        if st.button("Login", key="live_login_btn"):
            if not ADMIN_PASSWORD:
                st.error("ADMIN_PASSWORD env var not configured on this deployment.")
            elif pwd == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.session_state.admin_login_time = time.time()
                st.success("Logged in as admin.")
                st.rerun()
            else:
                st.error("Incorrect password.")


def _admin_minutes_left() -> int:
    elapsed = time.time() - st.session_state.get("admin_login_time", 0)
    return max(0, int((ADMIN_SESSION_HOURS * 3600 - elapsed) / 60))


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


# ── Capital allocation bar ─────────────────────────────────────────────────────

def _render_capital_bar(profiles: list[dict]):
    active = [p for p in profiles if p.get("active")]
    if not active:
        return

    total_capital = sum(p.get("capital_usd", 0) for p in active)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Deployed", f"${total_capital:,.0f}", help="Sum of capital_usd across all active profiles")
    c2.metric("Active Profiles", len(active))
    c3.metric("Total Profiles", len(profiles))
    c4.metric("Inactive", len(profiles) - len(active))

    if total_capital > 0:
        st.markdown("**Capital by profile:**")
        for p in sorted(active, key=lambda x: x.get("capital_usd", 0), reverse=True):
            cap = p.get("capital_usd", 0)
            bar_pct = cap / total_capital
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin:3px 0;">'
                f'<span style="width:200px;font-size:0.85rem;color:#e2e8f0;">{p.get("name","")}</span>'
                f'<div style="flex:1;background:#2d3748;border-radius:4px;height:14px;">'
                f'<div style="width:{bar_pct*100:.0f}%;background:#3b82f6;height:14px;border-radius:4px;"></div></div>'
                f'<span style="width:80px;text-align:right;font-size:0.85rem;color:#94a3b8;">'
                f'${cap:,.0f}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Profile card ──────────────────────────────────────────────────────────────

def _render_profile_card(profile: dict, positions: list[dict], trades: list[dict]):
    analytics = compute_analytics(trades)
    pid = profile["profile_id"]
    is_active = profile.get("active", True)
    status = "🟢 Active" if is_active else "⚫ Inactive"
    admin = is_admin()

    with st.expander(f"**{profile.get('name', pid)}** — {status}", expanded=False):

        # ── Metrics ────────────────────────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Open positions", len(positions))
        c2.metric("Trades closed", analytics.get("total", 0))
        if analytics.get("total", 0) > 0:
            c3.metric("Win rate", f"{analytics['win_rate']:.1f}%")
            c4.metric("Avg P&L", f"{analytics['avg_pnl_pct']:+.1f}%")
            c5.metric("Total P&L", f"${analytics['total_pnl_usd']:+,.0f}")

        # ── Profile parameters (read-only view always visible) ─────────────
        st.divider()
        p1, p2, p3, p4 = st.columns(4)
        p1.markdown(f"**Score threshold:** {profile.get('score_threshold', 0.75):.2f}")
        p2.markdown(f"**Max positions:** {profile.get('max_positions', 5)}")
        p3.markdown(f"**Take-profit:** {profile.get('take_profit_pct', 20)}%")
        p4.markdown(f"**Stop-loss:** {profile.get('stop_loss_pct', 10)}%")
        q1, q2, q3, q4 = st.columns(4)
        q1.markdown(f"**Max hold:** {profile.get('max_hold_days', 20)} days")
        q2.markdown(f"**Capital:** ${profile.get('capital_usd', 0):,.0f}")
        q3.markdown(f"**Sector:** {profile.get('sector', 'N/A')}")
        q4.markdown(f"**Earnings protection:** {'✅' if profile.get('earnings_protection', True) else '❌'}")

        # ── Admin edit form ────────────────────────────────────────────────
        if admin:
            st.divider()
            st.markdown("**⚙️ Edit Profile** _(admin)_")
            e1, e2 = st.columns(2)
            with e1:
                new_active = st.toggle("Active", value=is_active, key=f"live_{pid}_active")
                new_threshold = st.slider(
                    "Score threshold", 0.50, 0.95,
                    value=float(profile.get("score_threshold", 0.75)),
                    step=0.05, key=f"live_{pid}_threshold",
                )
                new_max_pos = st.number_input(
                    "Max positions", 1, 10,
                    value=int(profile.get("max_positions", 5)),
                    key=f"live_{pid}_max_pos",
                )
                new_capital = st.number_input(
                    "Capital ($)", min_value=1000, max_value=10_000_000,
                    value=int(profile.get("capital_usd", 50000)),
                    step=5000, key=f"live_{pid}_capital",
                )
            with e2:
                new_tp = st.slider(
                    "Take-profit %", 5, 50,
                    value=int(profile.get("take_profit_pct", 20)),
                    step=5, key=f"live_{pid}_tp",
                )
                new_sl = st.slider(
                    "Stop-loss %", 3, 25,
                    value=int(profile.get("stop_loss_pct", 10)),
                    step=1, key=f"live_{pid}_sl",
                )
                new_hold = st.number_input(
                    "Max hold days", 5, 60,
                    value=int(profile.get("max_hold_days", 20)),
                    key=f"live_{pid}_hold",
                )
                new_earnings = st.toggle(
                    "Earnings protection",
                    value=profile.get("earnings_protection", True),
                    key=f"live_{pid}_earnings",
                )

            if st.button("💾 Save", key=f"live_{pid}_save", type="primary"):
                updated = {**profile,
                    "active": new_active,
                    "score_threshold": round(new_threshold, 2),
                    "max_positions": int(new_max_pos),
                    "capital_usd": float(new_capital),
                    "take_profit_pct": float(new_tp),
                    "stop_loss_pct": float(new_sl),
                    "max_hold_days": int(new_hold),
                    "earnings_protection": new_earnings,
                }
                if save_live_profile(updated):
                    st.success("✅ Profile saved.")
                    st.rerun()
                else:
                    st.error("Failed to save — check AWS credentials.")

        # ── Open positions ─────────────────────────────────────────────────
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

        # ── Closed trades ──────────────────────────────────────────────────
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


# ── Add profile form ───────────────────────────────────────────────────────────

def _render_add_profile_form():
    with st.expander("➕ Add New Profile", expanded=False):
        st.markdown("Create a new live trading profile.")
        f1, f2 = st.columns(2)
        with f1:
            new_name = st.text_input("Profile name", key="new_profile_name",
                                     placeholder="e.g. AI Conservative")
            new_sector = st.selectbox("Sector", SECTORS, key="new_profile_sector")
            new_capital = st.number_input("Capital ($)", min_value=1000, max_value=10_000_000,
                                          value=50000, step=5000, key="new_profile_capital")
            new_threshold = st.slider("Score threshold", 0.50, 0.95, value=0.75,
                                      step=0.05, key="new_profile_threshold")
            new_max_pos = st.number_input("Max positions", 1, 10, value=5,
                                          key="new_profile_max_pos")
        with f2:
            new_tp = st.slider("Take-profit %", 5, 50, value=20, step=5, key="new_profile_tp")
            new_sl = st.slider("Stop-loss %", 3, 25, value=10, step=1, key="new_profile_sl")
            new_hold = st.number_input("Max hold days", 5, 60, value=20, key="new_profile_hold")
            new_earnings = st.toggle("Earnings protection", value=True, key="new_profile_earnings")
            new_active = st.toggle("Start active", value=False, key="new_profile_active",
                                   help="Keep inactive until you've reviewed the parameters.")

        if st.button("✅ Create Profile", key="new_profile_create", type="primary"):
            if not new_name.strip():
                st.error("Profile name is required.")
                return
            ts = int(time.time())
            slug = new_name.strip().lower().replace(" ", "_")[:20]
            pid = f"live_{slug}_{ts}"
            profile = {
                "profile_id": pid,
                "name": new_name.strip(),
                "sector": new_sector,
                "active": new_active,
                "capital_usd": float(new_capital),
                "score_threshold": round(new_threshold, 2),
                "max_positions": int(new_max_pos),
                "take_profit_pct": float(new_tp),
                "stop_loss_pct": float(new_sl),
                "max_hold_days": int(new_hold),
                "earnings_protection": new_earnings,
                "use_sonnet": True,
            }
            if save_live_profile(profile):
                st.success(f"✅ Profile '{new_name}' created.")
                st.rerun()
            else:
                st.error("Failed to create profile — check AWS credentials.")


# ── Promote from Research ──────────────────────────────────────────────────────

def _render_promote_section(live_profile_ids: set[str]):
    configs = load_research_configs()
    if not configs:
        return

    promotable = [c for c in configs if f"live_from_{c['config_id']}" not in live_profile_ids]
    if not promotable:
        st.caption("All research configs have already been promoted to live.")
        return

    st.markdown("**🔬 Promote from Research**")
    st.caption("Creates a new (inactive) live profile with the research config's parameters. Review and activate manually.")

    for cfg in promotable:
        cols = st.columns([5, 2])
        cols[0].markdown(
            f"`{cfg.get('name', cfg['config_id'])}` — "
            f"threshold {cfg.get('score_threshold', 0.75):.2f}, "
            f"TP {cfg.get('take_profit_pct', 20)}%, "
            f"SL {cfg.get('stop_loss_pct', 10)}%"
        )
        if cols[1].button("Promote →", key=f"promote_{cfg['config_id']}"):
            pid = f"live_from_{cfg['config_id']}"
            promoted = {
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
            if save_live_profile(promoted):
                st.success(f"✅ Promoted. Review and activate '{promoted['name']}' in the profiles list above.")
                st.rerun()
            else:
                st.error("Failed to promote — check AWS credentials.")


# ── Sector grouping ────────────────────────────────────────────────────────────

def _render_sector_group(sector: str, profiles: list[dict], positions_by_profile: dict, trades_by_profile: dict):
    active_count = sum(1 for p in profiles if p.get("active"))
    status = "🟢" if active_count > 0 else "⚫"
    header_cols = st.columns([5, 2, 2])
    header_cols[0].markdown(f"#### {status} {sector}")
    header_cols[1].markdown(f"<small style='color:#94a3b8;'>{active_count}/{len(profiles)} active</small>",
                            unsafe_allow_html=True)
    if is_admin() and len(profiles) > 0:
        sector_all_active = all(p.get("active") for p in profiles)
        label = "Disable All" if sector_all_active else "Enable All"
        if header_cols[2].button(label, key=f"sector_toggle_{sector.replace(' ', '_')}"):
            for p in profiles:
                p["active"] = not sector_all_active
                save_live_profile(p)
            st.rerun()

    for profile in profiles:
        pid = profile["profile_id"]
        _render_profile_card(
            profile,
            positions_by_profile.get(pid, []),
            trades_by_profile.get(pid, []),
        )


# ── Global controls (live tab — admin only write) ──────────────────────────────

def _render_live_global_controls(settings: dict):
    st.markdown("#### ⚙️ Global Controls")

    if settings.get("emergency_stop"):
        st.error("🛑 **EMERGENCY STOP IS ACTIVE** — all trading is halted.", icon="🛑")

    admin = is_admin()
    if not admin:
        col1, col2 = st.columns(2)
        col1.info(f"🛑 Emergency Stop: {'**ACTIVE**' if settings.get('emergency_stop') else 'Off'}")
        col2.info(f"📊 Market Filter: {'On' if settings.get('market_filter_active', True) else 'Off'} "
                  f"(SPY {settings.get('spy_ma_days', 200)}d / SOXX {settings.get('soxx_ma_days', 200)}d)")
        st.caption("Login as admin to change global settings.")
        return

    col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
    emergency_stop = col1.toggle(
        "🛑 Emergency Stop",
        value=settings.get("emergency_stop", False),
        key="live_emergency_stop",
        help="Halts ALL trading immediately across research and live engines.",
    )
    market_filter = col2.toggle(
        "📊 Market Filter (SPY/SOXX MA)",
        value=settings.get("market_filter_active", True),
        key="live_market_filter",
    )
    spy_days = col3.number_input("SPY MA days", 50, 500,
                                  value=int(settings.get("spy_ma_days", 200)),
                                  step=10, key="live_spy_days")
    soxx_days = col4.number_input("SOXX MA days", 50, 500,
                                   value=int(settings.get("soxx_ma_days", 200)),
                                   step=10, key="live_soxx_days")

    new_settings = {
        "emergency_stop": emergency_stop,
        "market_filter_active": market_filter,
        "spy_ma_days": int(spy_days),
        "soxx_ma_days": int(soxx_days),
    }
    if new_settings != {k: settings.get(k) for k in new_settings}:
        if save_global_settings(new_settings):
            if emergency_stop and not settings.get("emergency_stop"):
                st.error("🛑 Emergency stop ACTIVATED.")
            elif not emergency_stop and settings.get("emergency_stop"):
                st.success("✅ Emergency stop cleared.")
            else:
                st.success("Global settings saved.")
            st.rerun()


# ── Summary header ─────────────────────────────────────────────────────────────

def _render_summary_header(profiles: list[dict], all_positions: list[dict], all_trades: list[dict]):
    st.markdown("### 🚀 Live Trading")
    st.caption("Real-money trading with validated parameters from research. "
               "Admin login required to modify profiles.")

    active = sum(1 for p in profiles if p.get("active"))
    analytics = compute_analytics(all_trades)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Profiles", f"{active} / {len(profiles)} active")
    c2.metric("Open positions", len(all_positions))
    c3.metric("Trades closed", analytics.get("total", 0))
    if analytics.get("total", 0) > 0:
        c4.metric("Overall win rate", f"{analytics['win_rate']:.1f}%")
        c5.metric("Total P&L", f"${analytics['total_pnl_usd']:+,.0f}")

    if not profiles:
        st.info(
            "No live profiles configured yet. "
            "Complete 60 days of paper trading in the Research tab, then promote a winning "
            "config here and activate it. Login as admin to add profiles."
        )


# ── Entry point ────────────────────────────────────────────────────────────────

def render():
    _render_admin_auth()
    st.divider()

    settings = load_global_settings()
    _render_live_global_controls(settings)
    st.divider()

    profiles = load_live_profiles()
    all_positions = load_live_positions()

    profile_ids = {p["profile_id"] for p in profiles}
    positions_by_profile: dict[str, list[dict]] = {pid: [] for pid in profile_ids}
    for pos in all_positions:
        pid = pos.get("profile_id", "")
        if pid in positions_by_profile:
            positions_by_profile[pid].append(pos)

    trades_by_profile: dict[str, list[dict]] = {}
    for p in profiles:
        trades_by_profile[p["profile_id"]] = load_live_trades(p["profile_id"])

    all_trades = [t for trades in trades_by_profile.values() for t in trades]

    _render_summary_header(profiles, all_positions, all_trades)

    if profiles:
        st.divider()
        _render_capital_bar(profiles)
        st.divider()

        # Group by sector
        sectors_seen: dict[str, list[dict]] = {}
        for p in profiles:
            sector = p.get("sector", "Other")
            sectors_seen.setdefault(sector, []).append(p)

        for sector, sector_profiles in sectors_seen.items():
            _render_sector_group(sector, sector_profiles, positions_by_profile, trades_by_profile)
            st.markdown("")

    # Admin-only actions
    if is_admin():
        st.divider()
        st.markdown("#### 🔧 Admin Actions")
        _render_add_profile_form()
        st.markdown("")
        _render_promote_section(profile_ids)

    st.caption(f"Live profiles read from S3 every 30s · Bucket: `{S3_BUCKET}`")
