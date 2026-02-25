#!/usr/bin/env python3
"""
Test new FMP API endpoints based on their current documentation.
"""

import requests
import json

def test_new_endpoints():
    """Test new FMP API endpoints."""
    
    api_key = "zGnf89XHdjXeCKtYEswNXxB2UT51iBBP"
    
    print("Testing new FMP API endpoints...")
    
    # New API structure uses v4 for some endpoints
    endpoints_to_try = [
        # v3 endpoints that might still work
        ("v3/search", {"query": "Apple", "limit": 10}),
        ("v3/quote/AAPL", {}),
        ("v3/quote-short/AAPL", {}),
        ("v3/market-capitalization/AAPL", {}),
        
        # v4 endpoints
        ("v4/search", {"query": "Apple", "limit": 10}),
        ("v4/quote/AAPL", {}),
        ("v4/historical-price-full/AAPL", {"from": "2024-01-01", "to": "2024-01-10"}),
        ("v4/profile/AAPL", {}),
        
        # Try some basic market data endpoints
        ("v3/quotes/nasdaq", {}),
        ("v3/quotes/nyse", {}),
        ("v4/quotes/nasdaq", {}),
        ("v4/quotes/nyse", {}),
    ]
    
    for endpoint, params in endpoints_to_try:
        try:
            base_url = f"https://financialmodelingprep.com/api/{endpoint}"
            params["apikey"] = api_key
            
            print(f"\nTesting: {endpoint}")
            response = requests.get(base_url, params=params, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    print(f"✅ Success! Data type: {type(data)}")
                    if isinstance(data, list):
                        print(f"   Items: {len(data)}")
                        if data:
                            print(f"   Sample: {list(data[0].keys())[:5] if isinstance(data[0], dict) else data[0]}")
                    elif isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())[:5]}")
                else:
                    print("   Empty response")
            elif response.status_code == 403:
                error_data = response.json()
                if "Error Message" in error_data:
                    print(f"❌ 403: {error_data['Error Message'][:100]}...")
                else:
                    print(f"❌ 403: Forbidden")
            else:
                print(f"❌ {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    # Test if we can get any basic market data
    print("\n" + "="*50)
    print("Testing basic market data access...")
    
    simple_endpoints = [
        "v3/symbol/available-indexes",
        "v4/symbol/available-indexes", 
        "v3/available-traded/list",
        "v4/available-traded/list",
        "v3/etf/list",
        "v4/etf/list"
    ]
    
    for endpoint in simple_endpoints:
        try:
            url = f"https://financialmodelingprep.com/api/{endpoint}?apikey={api_key}"
            response = requests.get(url, timeout=10)
            print(f"{endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    print(f"  ✅ {len(data)} items available")
                    break  # Found a working endpoint
        except Exception as e:
            print(f"  ❌ {endpoint}: {e}")

if __name__ == "__main__":
    test_new_endpoints()