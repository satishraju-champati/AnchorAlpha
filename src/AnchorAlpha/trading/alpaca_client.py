"""
Alpaca broker client.
Handles paper and live order placement, position polling, and bracket orders.
Uses polling (not webhooks) — no inbound connectivity required.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PAPER_BASE_URL = "https://paper-api.alpaca.markets/v2"
LIVE_BASE_URL = "https://api.alpaca.markets/v2"
MARKET_DATA_URL = "https://data.alpaca.markets/v2"  # quotes/bars — separate from broker API


@dataclass
class AlpacaPosition:
    ticker: str
    qty: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float  # percent as decimal e.g. 0.05 = 5%

    @property
    def pnl_pct(self) -> float:
        return self.unrealized_plpc


@dataclass
class AlpacaOrder:
    order_id: str
    ticker: str
    side: str         # "buy" or "sell"
    qty: float
    status: str       # "new", "filled", "canceled", etc.
    filled_avg_price: Optional[float] = None


class AlpacaClient:
    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        self.base_url = PAPER_BASE_URL if paper else LIVE_BASE_URL
        self.paper = paper
        self.headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "Content-Type": "application/json",
        }
        logger.info(f"AlpacaClient initialized (paper={paper})")

    def _get(self, path: str, params: dict = None) -> dict:
        resp = requests.get(f"{self.base_url}{path}", headers=self.headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        resp = requests.post(f"{self.base_url}{path}", headers=self.headers, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> None:
        resp = requests.delete(f"{self.base_url}{path}", headers=self.headers, timeout=10)
        resp.raise_for_status()

    # ── Account ────────────────────────────────────────────────────────────

    def get_account(self) -> dict:
        return self._get("/account")

    def get_buying_power(self) -> float:
        account = self.get_account()
        return float(account["buying_power"])

    def get_portfolio_value(self) -> float:
        account = self.get_account()
        return float(account["portfolio_value"])

    # ── Positions ──────────────────────────────────────────────────────────

    def get_positions(self) -> list[AlpacaPosition]:
        raw = self._get("/positions")
        positions = []
        for p in raw:
            positions.append(AlpacaPosition(
                ticker=p["symbol"],
                qty=float(p["qty"]),
                avg_entry_price=float(p["avg_entry_price"]),
                current_price=float(p["current_price"]),
                unrealized_pl=float(p["unrealized_pl"]),
                unrealized_plpc=float(p["unrealized_plpc"]),
            ))
        return positions

    def get_position(self, ticker: str) -> Optional[AlpacaPosition]:
        try:
            p = self._get(f"/positions/{ticker}")
            return AlpacaPosition(
                ticker=p["symbol"],
                qty=float(p["qty"]),
                avg_entry_price=float(p["avg_entry_price"]),
                current_price=float(p["current_price"]),
                unrealized_pl=float(p["unrealized_pl"]),
                unrealized_plpc=float(p["unrealized_plpc"]),
            )
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def has_position(self, ticker: str) -> bool:
        return self.get_position(ticker) is not None

    # ── Orders ─────────────────────────────────────────────────────────────

    def place_bracket_order(
        self,
        ticker: str,
        qty: float,
        take_profit_pct: float = 0.20,
        stop_loss_pct: float = 0.10,
    ) -> AlpacaOrder:
        """
        Place a market buy with attached take-profit and stop-loss legs.
        take_profit_pct: 0.20 = +20% above entry
        stop_loss_pct:   0.10 = -10% below entry
        """
        resp = requests.get(
            f"{MARKET_DATA_URL}/stocks/quotes/latest",
            headers=self.headers,
            params={"symbols": ticker},
            timeout=10,
        )
        resp.raise_for_status()
        quote = resp.json()
        ask = float(quote["quotes"][ticker]["ap"])
        take_profit_price = round(ask * (1 + take_profit_pct), 2)
        stop_loss_price = round(ask * (1 - stop_loss_pct), 2)

        body = {
            "symbol": ticker,
            "qty": str(round(qty, 6)),
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit": {"limit_price": str(take_profit_price)},
            "stop_loss": {"stop_price": str(stop_loss_price)},
        }
        raw = self._post("/orders", body)
        logger.info(
            f"Bracket order placed: {ticker} qty={qty} "
            f"tp={take_profit_price} sl={stop_loss_price} order_id={raw['id']}"
        )
        return AlpacaOrder(
            order_id=raw["id"],
            ticker=ticker,
            side="buy",
            qty=qty,
            status=raw["status"],
        )

    def close_position(self, ticker: str) -> None:
        """Market-sell entire position."""
        try:
            self._delete(f"/positions/{ticker}")
            logger.info(f"Closed position: {ticker}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"No position to close for {ticker}")
            else:
                raise

    def cancel_open_orders(self, ticker: str) -> None:
        """Cancel all open orders for a ticker (cleans up bracket legs)."""
        orders = self._get("/orders", params={"status": "open", "symbols": ticker})
        for order in orders:
            try:
                self._delete(f"/orders/{order['id']}")
                logger.info(f"Cancelled order {order['id']} for {ticker}")
            except Exception as e:
                logger.warning(f"Could not cancel order {order['id']}: {e}")

    def get_order(self, order_id: str) -> AlpacaOrder:
        raw = self._get(f"/orders/{order_id}")
        return AlpacaOrder(
            order_id=raw["id"],
            ticker=raw["symbol"],
            side=raw["side"],
            qty=float(raw["qty"]),
            status=raw["status"],
            filled_avg_price=float(raw["filled_avg_price"]) if raw.get("filled_avg_price") else None,
        )

    def wait_for_fill(self, order_id: str, timeout_seconds: int = 60) -> AlpacaOrder:
        """Poll until order is filled or timeout."""
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            order = self.get_order(order_id)
            if order.status in ("filled", "canceled", "expired", "rejected"):
                return order
            time.sleep(2)
        return self.get_order(order_id)

    # ── Market status ──────────────────────────────────────────────────────

    def is_market_open(self) -> bool:
        clock = self._get("/clock")
        return bool(clock["is_open"])
