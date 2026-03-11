#!/usr/bin/env python3
"""
Test FMP API endpoints to find what's available with the new /stable/ API
"""

import requests
import json

API_KEY = "zGnf89XHdjXeCKtYEswNXxB2UT51iBBP"
BASE_URL = "https://financialmodelingprep.com/stable"

def test_endpoint(endpoint, description):
    """Test a specific endpoint"""
    # Fix URL parameter formatting
    if '?' in endpoint:
        url = f"{BASE_URL}/{endpoint}&apikey={API_KEY}"
    else:
        url = f"{BASE_URL}/{endpoint}?apikey={API_KEY}"
    
    print(f"\nTesting: {description}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"✅ SUCCESS - {len(data)} items returned")
                if isinstance(data, list) and len(data) > 0:
                    print(f"Sample keys: {list(data[0].keys())[:5]}")
                elif isinstance(data, dict):
                    print(f"Sample keys: {list(data.keys())[:5]}")
                return True
            else:
                print("❌ Empty response")
                return False
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🧪 Testing FMP /stable/ API Endpoints")
    print("=" * 50)
    
    # Test various endpoints that might be available
    endpoints = [
        ("income-statement?symbol=AAPL", "Income Statement (AAPL)"),
        ("balance-sheet-statement?symbol=AAPL", "Balance Sheet (AAPL)"),
        ("cash-flow-statement?symbol=AAPL", "Cash Flow (AAPL)"),
        ("profile?symbol=AAPL", "Company Profile (AAPL)"),
        ("quote?symbol=AAPL", "Stock Quote (AAPL)"),
        ("historical-price-full?symbol=AAPL", "Historical Prices (AAPL)"),
        ("stock-screener?marketCapMoreThan=1000000000&limit=10", "Stock Screener"),
        ("stock_list?limit=10", "Stock List"),
        ("available-traded/list", "Available Traded Stocks"),
        ("symbol/available-indexes", "Available Indexes"),
        ("quotes/index", "Index Quotes"),
        ("market-hours", "Market Hours"),
        ("sector_performance", "Sector Performance"),
    ]
    
    working_endpoints = []
    
    for endpoint, description in endpoints:
        if test_endpoint(endpoint, description):
            working_endpoints.append((endpoint, description))
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Working endpoints: {len(working_endpoints)}/{len(endpoints)}")
    
    if working_endpoints:
        print("\n✅ WORKING ENDPOINTS:")
        for endpoint, description in working_endpoints:
            print(f"  • {description}: {endpoint}")
    
    print(f"\nTotal tests: {len(endpoints)}")
    print(f"Success rate: {len(working_endpoints)/len(endpoints)*100:.1f}%")

if __name__ == "__main__":
    main()