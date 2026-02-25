"""
Mock data provider for development and testing when FMP API is not available.
Generates realistic stock data for large-cap US companies.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from AnchorAlpha.models import Stock

logger = logging.getLogger(__name__)


class MockDataProvider:
    """Mock data provider that simulates FMP API responses."""
    
    # Real large-cap US companies with approximate market caps (in billions)
    LARGE_CAP_COMPANIES = [
        # 1T+ tier
        ("AAPL", "Apple Inc.", 3000, 180.0),
        ("MSFT", "Microsoft Corporation", 2800, 380.0),
        ("GOOGL", "Alphabet Inc.", 1700, 140.0),
        ("AMZN", "Amazon.com Inc.", 1500, 150.0),
        ("NVDA", "NVIDIA Corporation", 1800, 750.0),
        ("TSLA", "Tesla Inc.", 1200, 380.0),
        ("META", "Meta Platforms Inc.", 1300, 520.0),
        
        # 500B-1T tier
        ("BRK.B", "Berkshire Hathaway Inc.", 900, 450.0),
        ("TSM", "Taiwan Semiconductor", 800, 155.0),
        ("LLY", "Eli Lilly and Company", 750, 800.0),
        ("V", "Visa Inc.", 700, 320.0),
        ("UNH", "UnitedHealth Group Inc.", 650, 680.0),
        ("XOM", "Exxon Mobil Corporation", 600, 140.0),
        ("JNJ", "Johnson & Johnson", 580, 240.0),
        ("WMT", "Walmart Inc.", 570, 220.0),
        ("JPM", "JPMorgan Chase & Co.", 560, 190.0),
        ("MA", "Mastercard Incorporated", 540, 550.0),
        ("PG", "Procter & Gamble Co.", 520, 220.0),
        ("HD", "The Home Depot Inc.", 510, 480.0),
        
        # 200B-500B tier
        ("AVGO", "Broadcom Inc.", 480, 1100.0),
        ("ORCL", "Oracle Corporation", 470, 170.0),
        ("COST", "Costco Wholesale Corp.", 460, 1040.0),
        ("ABBV", "AbbVie Inc.", 450, 255.0),
        ("CRM", "Salesforce Inc.", 440, 450.0),
        ("KO", "The Coca-Cola Company", 430, 100.0),
        ("NFLX", "Netflix Inc.", 420, 950.0),
        ("BAC", "Bank of America Corp.", 410, 52.0),
        ("TMO", "Thermo Fisher Scientific", 400, 1020.0),
        ("ACN", "Accenture plc", 390, 620.0),
        ("ADBE", "Adobe Inc.", 380, 820.0),
        ("MRK", "Merck & Co. Inc.", 370, 145.0),
        ("CVX", "Chevron Corporation", 360, 190.0),
        ("AMD", "Advanced Micro Devices", 350, 220.0),
        ("PEP", "PepsiCo Inc.", 340, 250.0),
        ("LIN", "Linde plc", 330, 680.0),
        ("CSCO", "Cisco Systems Inc.", 320, 78.0),
        ("TXN", "Texas Instruments Inc.", 310, 340.0),
        ("ABT", "Abbott Laboratories", 300, 170.0),
        ("DHR", "Danaher Corporation", 290, 410.0),
        ("QCOM", "QUALCOMM Incorporated", 280, 250.0),
        ("VZ", "Verizon Communications", 270, 65.0),
        ("WFC", "Wells Fargo & Company", 260, 65.0),
        ("INTC", "Intel Corporation", 250, 60.0),
        ("COP", "ConocoPhillips", 240, 185.0),
        ("PM", "Philip Morris International", 230, 150.0),
        ("UNP", "Union Pacific Corporation", 220, 340.0),
        ("NOW", "ServiceNow Inc.", 210, 1050.0),
        
        # 100B-200B tier
        ("NKE", "NIKE Inc.", 200, 130.0),
        ("T", "AT&T Inc.", 190, 26.0),
        ("HON", "Honeywell International", 180, 260.0),
        ("UPS", "United Parcel Service", 170, 200.0),
        ("LOW", "Lowe's Companies Inc.", 160, 240.0),
        ("MS", "Morgan Stanley", 150, 85.0),
        ("CAT", "Caterpillar Inc.", 140, 260.0),
        ("GS", "The Goldman Sachs Group", 130, 380.0),
        ("RTX", "Raytheon Technologies", 120, 80.0),
        ("SPGI", "S&P Global Inc.", 110, 460.0),
        ("BLK", "BlackRock Inc.", 105, 680.0),
    ]
    
    def __init__(self):
        """Initialize mock data provider."""
        self.companies = self.LARGE_CAP_COMPANIES.copy()
        random.shuffle(self.companies)  # Add some randomness
    
    def get_large_cap_stocks(self) -> List[Dict[str, Any]]:
        """Generate mock large-cap stock data."""
        stocks = []
        
        for ticker, name, market_cap_billions, base_price in self.companies:
            # Add some random variation to market cap and price
            market_cap = int(market_cap_billions * 1_000_000_000 * random.uniform(0.9, 1.1))
            current_price = base_price * random.uniform(0.95, 1.05)
            
            stock_data = {
                "symbol": ticker,
                "companyName": name,
                "price": round(current_price, 2),
                "marketCap": market_cap,
                "exchange": random.choice(["NASDAQ", "NYSE"]),
                "sector": random.choice([
                    "Technology", "Healthcare", "Financial Services", 
                    "Consumer Cyclical", "Communication Services", 
                    "Industrials", "Consumer Defensive", "Energy"
                ])
            }
            stocks.append(stock_data)
        
        logger.info(f"Generated {len(stocks)} mock large-cap stocks")
        return stocks
    
    def get_historical_prices(self, symbol: str, days: int = 100) -> Dict[str, Any]:
        """Generate mock historical price data."""
        # Find the company to get base price
        base_price = 100.0  # Default
        for ticker, _, _, price in self.companies:
            if ticker == symbol:
                base_price = price
                break
        
        # Generate historical prices with some realistic movement
        historical_data = []
        current_date = datetime.now()
        current_price = base_price
        
        for i in range(days):
            date = current_date - timedelta(days=i)
            
            # Add some random price movement (realistic daily changes)
            daily_change = random.uniform(-0.05, 0.05)  # -5% to +5%
            current_price *= (1 + daily_change)
            
            # Ensure price doesn't go too low
            if current_price < base_price * 0.5:
                current_price = base_price * 0.5
            elif current_price > base_price * 2.0:
                current_price = base_price * 2.0
            
            price_data = {
                "date": date.strftime("%Y-%m-%d"),
                "open": round(current_price * random.uniform(0.99, 1.01), 2),
                "high": round(current_price * random.uniform(1.00, 1.03), 2),
                "low": round(current_price * random.uniform(0.97, 1.00), 2),
                "close": round(current_price, 2),
                "volume": random.randint(1_000_000, 50_000_000)
            }
            historical_data.append(price_data)
        
        # Sort by date (most recent first)
        historical_data.sort(key=lambda x: x["date"], reverse=True)
        
        logger.info(f"Generated {len(historical_data)} historical prices for {symbol}")
        
        return {
            "symbol": symbol,
            "historical": historical_data
        }
    
    def create_stock_from_data(self, stock_data: Dict[str, Any]) -> Optional[Stock]:
        """Create Stock object from mock data."""
        try:
            ticker = stock_data.get("symbol", "").strip()
            company_name = stock_data.get("companyName", "").strip()
            current_price = stock_data.get("price", 0.0)
            market_cap = stock_data.get("marketCap", 0)
            
            if not ticker or not company_name or current_price <= 0 or market_cap < 10_000_000_000:
                return None
            
            return Stock(
                ticker=ticker,
                company_name=company_name,
                current_price=float(current_price),
                market_cap=int(market_cap)
            )
        except Exception as e:
            logger.error(f"Error creating stock from mock data: {e}")
            return None
    
    def get_stocks_by_market_cap_tier(self) -> Dict[str, List[Stock]]:
        """Get mock stocks organized by market cap tiers."""
        stock_data = self.get_large_cap_stocks()
        
        stocks = []
        for data in stock_data:
            stock = self.create_stock_from_data(data)
            if stock:
                stocks.append(stock)
        
        # Organize by tiers
        tiers = {
            "100B_200B": [],
            "200B_500B": [],
            "500B_1T": [],
            "1T_plus": []
        }
        
        for stock in stocks:
            tier = stock.get_tier()
            if tier in tiers:
                tiers[tier].append(stock)
        
        # Log tier distribution
        for tier, tier_stocks in tiers.items():
            logger.info(f"Mock tier {tier}: {len(tier_stocks)} stocks")
        
        return tiers