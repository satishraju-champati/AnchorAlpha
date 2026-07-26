"""
Trading engine — main loop.
Runs Mon-Fri 8:30 AM to 4:30 PM ET.
Handles both Research (paper) and Live loops in one process.
Exits naturally at market close — EventBridge restarts it next morning.
"""

import json
import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import boto3
import requests

from .alpaca_client import AlpacaClient
from .claude_scorer import ClaudeScorer
from .config_manager import AI_SECTOR_STOCKS, ConfigManager
from .dip_detector import detect_dip
from .earnings_guard import EarningsGuard
from .order_manager import OrderManager, TradeLog
from .position_manager import OpenPosition, PositionManager
from .secrets import load_secrets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
MARKET_OPEN = (9, 30)
MARKET_CLOSE = (16, 30)
FRIDAY_REVIEW_TIME = (15, 30)
LOOP_INTERVAL_SECONDS = 300  # evaluate every 5 minutes


def now_et() -> datetime:
    return datetime.now(ET)


def is_market_hours() -> bool:
    t = now_et()
    if t.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    open_dt = t.replace(hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0)
    close_dt = t.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0, microsecond=0)
    return open_dt <= t <= close_dt


def is_friday_review_window() -> bool:
    t = now_et()
    return t.weekday() == 4 and t.hour == FRIDAY_REVIEW_TIME[0] and t.minute >= FRIDAY_REVIEW_TIME[1]


def should_shutdown() -> bool:
    t = now_et()
    if t.weekday() >= 5:
        return True
    close_dt = t.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0, microsecond=0)
    return t > close_dt


FMP_BASE = "https://financialmodelingprep.com/stable"


def _fmp_get(path: str, fmp_key: str, params: dict = None) -> any:
    """FMP stable API — ticker passed as ?symbol= query param, not path param."""
    r = requests.get(f"{FMP_BASE}/{path}", params={**(params or {}), "apikey": fmp_key}, timeout=10)
    r.raise_for_status()
    return r.json()


def get_price_history(ticker: str, fmp_key: str, days: int = 15) -> list[float]:
    """Fetch daily closing prices from FMP for dip detection (oldest first)."""
    data = _fmp_get("historical-price-eod/full", fmp_key, {"symbol": ticker, "timeseries": days})
    if isinstance(data, list):
        return [d["close"] for d in reversed(data)]
    return [d["close"] for d in reversed(data.get("historical", []))]


def build_stock_data(ticker: str, fmp_key: str) -> dict:
    """Collect all 11 signal inputs from FMP for Claude scoring."""
    try:
        quote = _fmp_get("quote", fmp_key, {"symbol": ticker})
        profile = _fmp_get("profile", fmp_key, {"symbol": ticker})
        changes = _fmp_get("stock-price-change", fmp_key, {"symbol": ticker})
        news = _fmp_get("news/stock", fmp_key, {"tickers": ticker, "limit": 5})
        ratings = _fmp_get("analyst-stock-ratings", fmp_key, {"symbol": ticker})
        income = _fmp_get("income-statement", fmp_key, {"symbol": ticker, "limit": 2})

        return {
            "ticker": ticker,
            "company_name": profile[0].get("companyName", "") if profile else "",
            "current_price": quote[0].get("price", 0) if quote else 0,
            "market_cap": profile[0].get("marketCap", 0) if profile else 0,
            "price_changes": changes[0] if changes else {},
            "news_headlines": [n.get("title", "") for n in (news or [])[:5]],
            "analyst_ratings": ratings[:3] if ratings else [],
            "revenue_growth": _revenue_growth(income),
            "volume_ratio": _volume_ratio(quote),
            "52w_high": profile[0].get("range", "").split("-")[-1].strip() if profile else "",
        }
    except Exception as e:
        logger.error(f"Failed to build stock data for {ticker}: {e}")
        return {"ticker": ticker}


def _revenue_growth(income: list) -> list:
    if len(income) < 2:
        return []
    results = []
    for stmt in income[:2]:
        rev = stmt.get("revenue", 0)
        prev = stmt.get("revenueGrowth", 0)
        results.append({"revenue": rev, "growth": prev})
    return results


def _volume_ratio(quote: list) -> float:
    if not quote:
        return 1.0
    q = quote[0]
    vol = q.get("volume", 0)
    avg = q.get("avgVolume", 1)
    return vol / avg if avg > 0 else 1.0


class TradingEngine:
    def __init__(self, secrets: dict):
        self.secrets = secrets
        self.config_mgr = ConfigManager()
        self.position_mgr = PositionManager()
        self.order_mgr = OrderManager()
        self.earnings_guard = EarningsGuard(secrets["alphavantage_key"])
        self.alpaca_paper = AlpacaClient(
            api_key=secrets["alpaca_paper_key"],
            api_secret=secrets["alpaca_paper_secret"],
            paper=True,
        )
        self.fmp_key = secrets["fmp_key"]

        self.alpaca_live = None
        if "alpaca_live_key" in secrets and "alpaca_live_secret" in secrets:
            self.alpaca_live = AlpacaClient(
                api_key=secrets["alpaca_live_key"],
                api_secret=secrets["alpaca_live_secret"],
                paper=False,
            )
            logger.info("Live Alpaca client initialized")
        else:
            logger.info("No live Alpaca keys — live loop disabled until Month 4")

        logger.info("TradingEngine initialised")

    def _check_market_conditions(self, settings) -> bool:
        """Returns True (GREEN) if both SPY and SOXX are above their configured MAs."""
        try:
            spy_days = settings.spy_ma_days
            soxx_days = settings.soxx_ma_days
            spy_prices = get_price_history("SPY", self.fmp_key, days=spy_days + 5)
            soxx_prices = get_price_history("SOXX", self.fmp_key, days=soxx_days + 5)

            if len(spy_prices) < spy_days or len(soxx_prices) < soxx_days:
                logger.warning("Insufficient price history for MA check — treating as RED LIGHT")
                return False

            spy_ma = sum(spy_prices[-spy_days:]) / spy_days
            soxx_ma = sum(soxx_prices[-soxx_days:]) / soxx_days
            spy_ok = spy_prices[-1] > spy_ma
            soxx_ok = soxx_prices[-1] > soxx_ma

            logger.info(
                f"Market filter: SPY {spy_prices[-1]:.2f} vs MA{spy_days} {spy_ma:.2f} "
                f"({'OK' if spy_ok else 'FAIL'}) | "
                f"SOXX {soxx_prices[-1]:.2f} vs MA{soxx_days} {soxx_ma:.2f} "
                f"({'OK' if soxx_ok else 'FAIL'})"
            )
            return spy_ok and soxx_ok
        except Exception as e:
            logger.error(f"Market condition check failed: {e} — treating as RED LIGHT")
            return False

    def run(self):
        logger.info("Trading engine started")
        self.config_mgr.seed_default_research_configs()

        while True:
            if should_shutdown():
                logger.info("Market closed — engine shutting down")
                break

            if not is_market_hours():
                logger.info("Pre-market or post-market — waiting")
                time.sleep(60)
                continue

            try:
                settings = self.config_mgr.load_global_settings()
                if settings.emergency_stop:
                    logger.warning("EMERGENCY STOP active — skipping all trading")
                    time.sleep(LOOP_INTERVAL_SECONDS)
                    continue

                friday_review = is_friday_review_window()

                market_ok = True
                if settings.market_filter_active:
                    market_ok = self._check_market_conditions(settings)
                    if not market_ok:
                        logger.info("Market filter RED LIGHT — exits still run, new entries blocked")

                self._run_research_loop(friday_review, market_ok)
                self._run_live_loop(friday_review, market_ok)

            except Exception as e:
                logger.error(f"Engine loop error: {e}", exc_info=True)

            time.sleep(LOOP_INTERVAL_SECONDS)

    # ── Research loop ──────────────────────────────────────────────────────

    def _run_research_loop(self, friday_review: bool, market_ok: bool = True):
        configs = self.config_mgr.load_research_configs()
        scorer_cache: dict[str, ClaudeScorer] = {}

        for config in configs:
            scorer_key = "haiku" if not config.use_sonnet else "sonnet"
            if scorer_key not in scorer_cache:
                scorer_cache[scorer_key] = ClaudeScorer(
                    api_key=self.secrets["claude_key"],
                    use_sonnet=config.use_sonnet,
                )
            scorer = scorer_cache[scorer_key]

            try:
                self._evaluate_research_config(config, scorer, friday_review, market_ok)
            except Exception as e:
                logger.error(f"Error in research config {config.config_id}: {e}", exc_info=True)

    def _evaluate_research_config(self, config, scorer: ClaudeScorer, friday_review: bool, market_ok: bool = True):
        positions = self.position_mgr.load_research_positions(config.config_id)

        # ── Exit check on open positions ───────────────────────────────────
        for position in list(positions):
            try:
                prices = get_price_history(position.ticker, self.fmp_key)
                current_price = prices[-1] if prices else position.entry_price
                stock_data = build_stock_data(position.ticker, self.fmp_key)
                result = scorer.score_stock(position.ticker, stock_data)
                current_score = result.score if result else position.score_at_entry

                # Earnings pre-close
                if config.earnings_protection and self.earnings_guard.should_pre_close(position.ticker):
                    self._close_research_position(config, position, current_price, current_score, "earnings_pre_close")
                    continue

                should_exit, reason = self.order_mgr.should_exit(
                    position=position,
                    current_price=current_price,
                    current_score=current_score,
                    score_threshold=config.score_threshold,
                    is_friday_review=friday_review,
                )
                if should_exit:
                    self._close_research_position(config, position, current_price, current_score, reason)
                else:
                    # Update score streak
                    updated = self.order_mgr.update_score_streak(position, current_score, position.score_at_entry)
                    updated.score_at_entry = current_score
                    self.position_mgr.update_research_position(config.config_id, updated)

            except Exception as e:
                logger.error(f"Exit check failed for {position.ticker} config={config.config_id}: {e}")

        # ── Entry check for new positions ──────────────────────────────────
        if not market_ok:
            return  # market filter active, no new entries

        positions = self.position_mgr.load_research_positions(config.config_id)
        open_tickers = {p.ticker for p in positions}
        if len(positions) >= config.max_positions:
            return

        for ticker in AI_SECTOR_STOCKS:
            if ticker in open_tickers:
                continue
            if len(positions) >= config.max_positions:
                break
            try:
                self._evaluate_entry_research(config, scorer, ticker, positions)
            except Exception as e:
                logger.error(f"Entry check failed for {ticker} config={config.config_id}: {e}")

    def _evaluate_entry_research(self, config, scorer: ClaudeScorer, ticker: str, positions: list):
        # Earnings block
        if config.earnings_protection and self.earnings_guard.blocks_entry(ticker):
            return

        # Dip check
        prices = get_price_history(ticker, self.fmp_key)
        if not prices:
            return
        dip = detect_dip(ticker, prices)
        if not dip or not dip.entry_ready:
            return

        # Build full data (market cap + scoring signals)
        stock_data = build_stock_data(ticker, self.fmp_key)

        # Market cap filter: $1T+ only
        if stock_data.get("market_cap", 0) < 1_000_000_000_000:
            logger.debug(f"Skipping {ticker} — market cap below $1T")
            return

        result = scorer.score_stock(ticker, stock_data)
        if not result or result.score < config.score_threshold:
            return

        # Place paper order
        current_price = prices[-1]
        portfolio_value = self.alpaca_paper.get_portfolio_value()
        capital = portfolio_value * (config.capital_pct / 100) / config.max_positions
        qty = capital / current_price

        order = self.alpaca_paper.place_bracket_order(
            ticker=ticker,
            qty=qty,
            take_profit_pct=config.take_profit_pct / 100,
            stop_loss_pct=config.stop_loss_pct / 100,
        )

        position = OpenPosition(
            ticker=ticker,
            profile_id=config.config_id,
            mode="research",
            entry_price=current_price,
            qty=qty,
            entry_date=date.today().isoformat(),
            alpaca_order_id=order.order_id,
            take_profit_pct=config.take_profit_pct,
            stop_loss_pct=config.stop_loss_pct,
            max_hold_days=config.max_hold_days,
            score_at_entry=result.score,
        )
        self.position_mgr.add_research_position(config.config_id, position)
        logger.info(f"Opened research position: {ticker} config={config.config_id} score={result.score:.2f}")

    def _close_research_position(self, config, position: OpenPosition, current_price: float, current_score: float, reason: str):
        self.alpaca_paper.close_position(position.ticker)
        pnl_pct = (current_price - position.entry_price) / position.entry_price
        pnl_usd = pnl_pct * position.entry_price * position.qty
        trade = TradeLog(
            ticker=position.ticker,
            config_or_profile_id=config.config_id,
            mode="research",
            entry_date=position.entry_date,
            exit_date=date.today().isoformat(),
            entry_price=position.entry_price,
            exit_price=current_price,
            qty=position.qty,
            pnl_pct=pnl_pct,
            pnl_usd=pnl_usd,
            exit_reason=reason,
            score_at_entry=position.score_at_entry,
            score_at_exit=current_score,
        )
        self.order_mgr.log_trade(trade)
        self.position_mgr.remove_research_position(config.config_id, position.ticker)
        logger.info(f"Closed research position: {position.ticker} reason={reason} pnl={pnl_pct:.1%}")

    # ── Live loop ──────────────────────────────────────────────────────────

    def _run_live_loop(self, friday_review: bool, market_ok: bool = True):
        if self.alpaca_live is None:
            return

        profiles = self.config_mgr.load_live_profiles()
        if not profiles:
            return

        scorer = ClaudeScorer(api_key=self.secrets["claude_key"], use_sonnet=True)

        for profile in profiles:
            try:
                self._evaluate_live_profile(profile, scorer, friday_review, market_ok)
            except Exception as e:
                logger.error(f"Error in live profile {profile.profile_id}: {e}", exc_info=True)

    def _evaluate_live_profile(self, profile, scorer: ClaudeScorer, friday_review: bool, market_ok: bool):
        positions = self.position_mgr.get_live_positions_for_profile(profile.profile_id)

        # ── Exit check on open positions ───────────────────────────────────
        for position in list(positions):
            try:
                prices = get_price_history(position.ticker, self.fmp_key)
                current_price = prices[-1] if prices else position.entry_price
                stock_data = build_stock_data(position.ticker, self.fmp_key)
                result = scorer.score_stock(position.ticker, stock_data)
                current_score = result.score if result else position.score_at_entry

                if profile.earnings_protection and self.earnings_guard.should_pre_close(position.ticker):
                    self._close_live_position(profile, position, current_price, current_score, "earnings_pre_close")
                    continue

                should_exit, reason = self.order_mgr.should_exit(
                    position=position,
                    current_price=current_price,
                    current_score=current_score,
                    score_threshold=profile.score_threshold,
                    is_friday_review=friday_review,
                )
                if should_exit:
                    self._close_live_position(profile, position, current_price, current_score, reason)
                else:
                    updated = self.order_mgr.update_score_streak(position, current_score, position.score_at_entry)
                    updated.score_at_entry = current_score
                    self.position_mgr.update_live_position(updated)
            except Exception as e:
                logger.error(f"Exit check failed for {position.ticker} profile={profile.profile_id}: {e}")

        # ── Entry check for new positions ──────────────────────────────────
        if not market_ok:
            return

        positions = self.position_mgr.get_live_positions_for_profile(profile.profile_id)
        if len(positions) >= profile.max_positions:
            return

        open_tickers = {p.ticker for p in positions}

        for ticker in AI_SECTOR_STOCKS:
            if len(positions) >= profile.max_positions:
                break
            if ticker in open_tickers:
                continue
            if self.position_mgr.is_ticker_taken_live(ticker):
                continue
            try:
                self._evaluate_entry_live(profile, scorer, ticker, positions)
            except Exception as e:
                logger.error(f"Live entry check failed for {ticker} profile={profile.profile_id}: {e}")

    def _evaluate_entry_live(self, profile, scorer: ClaudeScorer, ticker: str, positions: list):
        if profile.earnings_protection and self.earnings_guard.blocks_entry(ticker):
            return

        prices = get_price_history(ticker, self.fmp_key)
        if not prices:
            return
        dip = detect_dip(ticker, prices)
        if not dip or not dip.entry_ready:
            return

        stock_data = build_stock_data(ticker, self.fmp_key)

        # Market cap filter: $1T+ only
        if stock_data.get("market_cap", 0) < 1_000_000_000_000:
            logger.debug(f"Skipping {ticker} (live) — market cap below $1T")
            return

        result = scorer.score_stock(ticker, stock_data)
        if not result or result.score < profile.score_threshold:
            return

        # Double-check conflict (another profile may have just entered)
        if self.position_mgr.is_ticker_taken_live(ticker):
            return

        current_price = prices[-1]
        capital_per_slot = profile.capital_usd / profile.max_positions
        qty = capital_per_slot / current_price

        order = self.alpaca_live.place_bracket_order(
            ticker=ticker,
            qty=qty,
            take_profit_pct=profile.take_profit_pct / 100,
            stop_loss_pct=profile.stop_loss_pct / 100,
        )

        position = OpenPosition(
            ticker=ticker,
            profile_id=profile.profile_id,
            mode="live",
            entry_price=current_price,
            qty=qty,
            entry_date=date.today().isoformat(),
            alpaca_order_id=order.order_id,
            take_profit_pct=profile.take_profit_pct,
            stop_loss_pct=profile.stop_loss_pct,
            max_hold_days=profile.max_hold_days,
            score_at_entry=result.score,
        )
        self.position_mgr.add_live_position(position)
        logger.info(f"Opened LIVE position: {ticker} profile={profile.profile_id} score={result.score:.2f}")

    def _close_live_position(self, profile, position: OpenPosition, current_price: float, current_score: float, reason: str):
        self.alpaca_live.close_position(position.ticker)
        pnl_pct = (current_price - position.entry_price) / position.entry_price
        pnl_usd = pnl_pct * position.entry_price * position.qty
        trade = TradeLog(
            ticker=position.ticker,
            config_or_profile_id=profile.profile_id,
            mode="live",
            entry_date=position.entry_date,
            exit_date=date.today().isoformat(),
            entry_price=position.entry_price,
            exit_price=current_price,
            qty=position.qty,
            pnl_pct=pnl_pct,
            pnl_usd=pnl_usd,
            exit_reason=reason,
            score_at_entry=position.score_at_entry,
            score_at_exit=current_score,
        )
        self.order_mgr.log_trade(trade)
        self.position_mgr.remove_live_position(position.ticker, profile.profile_id)
        logger.info(f"Closed LIVE position: {position.ticker} reason={reason} pnl={pnl_pct:.1%}")


def main():
    secrets = load_secrets()
    engine = TradingEngine(secrets)
    engine.run()


if __name__ == "__main__":
    main()
