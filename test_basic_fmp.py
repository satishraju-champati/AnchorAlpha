#!/usr/bin/env python3
"""
Test basic FMP API endpoints to verify API key works.
"""

import requests
import json

def test_basic_endpoints():
    """Test basic FMP API endpoints."""
    
    api_key = "zGnf89XHdjXeCKtYEswNXxB2UT51iBBP"
    base_url = "https://financialmodelingprep.com/api/v3"
    
    print("Testing FMP API key with basic endpoints...")
    
    # Test 1: Company profile (usually available on free tier)
    print("\n1. Testing company profile for AAPL...")
    try:
        url = f"{base_url}/profile/AAPL?apikey={api_key}"
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data:
                company = data[0]
                print(f"✅ Company: {company.get('companyName', 'N/A')}")
                print(f"   Market Cap: ${company.get('mktCap', 0):,}")
                print(f"   Price: ${company.get('price', 0)}")
            else:
                print("❌ No data returned")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Historical prices (usually available on free tier)
    print("\n2. Testing historical prices for AAPL...")
    try:
        url = f"{base_url}/historical-price-full/AAPL?apikey={api_key}&from=2024-01-01&to=2024-01-10"
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "historical" in data and data["historical"]:
                print(f"✅ Retrieved {len(data['historical'])} historical prices")
                recent = data["historical"][0]
                print(f"   Recent: {recent.get('date')} - ${recent.get('close', 0)}")
            else:
                print("❌ No historical data returned")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Stock list (alternative to screener)
    print("\n3. Testing stock list...")
    try:
        url = f"{base_url}/stock/list?apikey={api_key}"
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"✅ Retrieved {len(data)} stocks from list")
                # Show first few
                for i, stock in enumerate(data[:3]):
                    print(f"   {i+1}. {stock.get('symbol', 'N/A')} - {stock.get('name', 'N/A')}")
            else:
                print("❌ No stock list data returned")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 4: Check what endpoints are available
    print("\n4. Testing available endpoints...")
    endpoints_to_try = [
        "available-traded/list",
        "symbol/available-indexes", 
        "stock_market/actives"
    ]
    
    for endpoint in endpoints_to_try:
        try:
            url = f"{base_url}/{endpoint}?apikey={api_key}"
            response = requests.get(url, timeout=10)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data:
                    print(f"     ✅ Data available ({len(data)} items)")
        except Exception as e:
            print(f"     ❌ {endpoint}: {e}")

if __name__ == "__main__":
    test_basic_endpoints()