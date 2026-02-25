#!/usr/bin/env python3
"""
Simple test to verify our models work without external dependencies.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from AnchorAlpha.models import Stock, MomentumCalculation

def test_models():
    """Test our core models."""
    print("Testing Stock model...")
    
    # Test Stock creation
    stock = Stock(
        ticker="AAPL",
        company_name="Apple Inc.",
        current_price=150.25,
        market_cap=2_400_000_000_000,  # $2.4T
        momentum_7d=0.05,
        momentum_30d=0.12
    )
    
    print(f"✅ Created stock: {stock.ticker} - {stock.company_name}")
    print(f"   Market cap: ${stock.market_cap:,}")
    print(f"   Tier: {stock.get_tier()}")
    print(f"   7-day momentum: {stock.get_momentum(7)}")
    
    # Test MomentumCalculation
    print("\nTesting MomentumCalculation...")
    
    calc = MomentumCalculation(
        ticker="AAPL",
        current_price=150.0,
        historical_prices={
            7: 140.0,
            30: 130.0,
            60: 145.0,
            90: 120.0
        }
    )
    
    momentum_7d = calc.calculate_momentum(7)
    momentum_30d = calc.calculate_momentum(30)
    
    print(f"✅ Momentum calculations for {calc.ticker}:")
    print(f"   7-day: {momentum_7d:.4f} ({momentum_7d*100:.2f}%)")
    print(f"   30-day: {momentum_30d:.4f} ({momentum_30d*100:.2f}%)")
    
    # Test all momentum calculations
    all_momentum = calc.calculate_all_momentum()
    print(f"   All momentum: {all_momentum}")
    
    print("\n🎉 All model tests passed!")

if __name__ == "__main__":
    test_models()