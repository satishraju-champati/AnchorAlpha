"""
Claude API scoring client.
Scores stocks 0-1 based on 11 signals. Uses Sonnet for live, Haiku for research.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5"

SCORING_PROMPT = """You are a quantitative stock analyst scoring a large-cap stock for a swing trading strategy.

Score the stock from 0.0 to 1.0 based on these 11 signals:

1. Momentum (7d, 30d, 60d, 90d returns)
2. Volume anomaly (today vs 20-day average)
3. News sentiment (recent headlines)
4. Analyst consensus (buy/hold/sell counts + price targets)
5. Revenue trend (YoY growth last 2 quarters)
6. Earnings trend (EPS beat/miss last 2 quarters)
7. Relative strength vs SPY (last 30 days)
8. Distance from 52-week high (% below peak)
9. Market cap tier (larger = more stable)
10. Sector momentum (sector ETF 30d return)
11. Insider activity (net buy/sell last 90 days)

Score guidelines:
- 0.85+: Exceptional setup, strong buy signals across most factors
- 0.75-0.84: Good setup, buy signal
- 0.60-0.74: Moderate, below threshold for entry
- Below 0.60: Weak or negative signals, avoid

Stock data:
{stock_data}

Return ONLY valid JSON in this exact format:
{{
  "score": 0.82,
  "confidence": "high",
  "buy_signal": true,
  "key_positives": ["reason1", "reason2"],
  "key_risks": ["risk1"],
  "reasoning": "One paragraph explanation of the score."
}}"""


@dataclass
class ScoreResult:
    ticker: str
    score: float
    confidence: str
    buy_signal: bool
    key_positives: list
    key_risks: list
    reasoning: str

    @property
    def is_actionable(self) -> bool:
        return self.buy_signal and self.score >= 0.60


class ClaudeScorer:
    def __init__(self, api_key: str, use_sonnet: bool = True):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = SONNET if use_sonnet else HAIKU
        logger.info(f"ClaudeScorer initialized with model={self.model}")

    def score_stock(self, ticker: str, stock_data: dict) -> Optional[ScoreResult]:
        """Score a single stock. Returns None on failure."""
        try:
            prompt = SCORING_PROMPT.format(
                stock_data=json.dumps(stock_data, indent=2)
            )
            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return ScoreResult(
                ticker=ticker,
                score=float(data["score"]),
                confidence=data.get("confidence", "medium"),
                buy_signal=bool(data.get("buy_signal", False)),
                key_positives=data.get("key_positives", []),
                key_risks=data.get("key_risks", []),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.error(f"Failed to score {ticker}: {e}")
            return None

    def score_batch(self, stocks: list[dict]) -> dict[str, ScoreResult]:
        """Score a list of stocks. Each dict must have 'ticker' key."""
        results = {}
        for stock in stocks:
            ticker = stock["ticker"]
            result = self.score_stock(ticker, stock)
            if result:
                results[ticker] = result
                logger.info(f"{ticker}: score={result.score:.2f} buy={result.buy_signal}")
        return results
