#!/usr/bin/env python3
"""
Check FMP API status and try to find working endpoints.
"""

import requests

def check_api_status():
    """Check what's available with the current API key."""
    
    api_key = "zGnf89XHdjXeCKtYEswNXxB2UT51iBBP"
    
    print("Checking FMP API key status...")
    print(f"API Key: {api_key}")
    
    # Try the most basic endpoint - API status/info
    basic_urls = [
        f"https://financialmodelingprep.com/api/v3/company/stock/list?apikey={api_key}",
        f"https://financialmodelingprep.com/api/v4/company/stock/list?apikey={api_key}",
        f"https://site.financialmodelingprep.com/api/v3/company/stock/list?apikey={api_key}",
        f"https://site.financialmodelingprep.com/api/v4/company/stock/list?apikey={api_key}",
        
        # Try without version
        f"https://financialmodelingprep.com/api/company/stock/list?apikey={api_key}",
        f"https://site.financialmodelingprep.com/api/company/stock/list?apikey={api_key}",
        
        # Try different base URLs
        f"https://fmpcloud.io/api/v3/company/stock/list?apikey={api_key}",
        f"https://fmpcloud.io/api/v4/company/stock/list?apikey={api_key}",
    ]
    
    for url in basic_urls:
        try:
            print(f"\nTrying: {url.split('?')[0]}")
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! This endpoint works!")
                data = response.json()
                if data:
                    print(f"Data type: {type(data)}")
                    if isinstance(data, list) and len(data) > 0:
                        print(f"Items: {len(data)}")
                        print(f"Sample item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
                    elif isinstance(data, dict):
                        print(f"Response keys: {list(data.keys())}")
                return True
            else:
                try:
                    error_data = response.json()
                    if "Error Message" in error_data:
                        print(f"Error: {error_data['Error Message'][:100]}...")
                    else:
                        print(f"Response: {response.text[:100]}...")
                except:
                    print(f"Raw response: {response.text[:100]}...")
                    
        except Exception as e:
            print(f"Exception: {e}")
    
    print("\n" + "="*60)
    print("RECOMMENDATION:")
    print("It appears the FMP API key may be for an older version")
    print("or the free tier has very limited access.")
    print("\nOptions:")
    print("1. Check FMP documentation at: https://site.financialmodelingprep.com/developer/docs")
    print("2. Try a different financial data provider (Alpha Vantage, Yahoo Finance, etc.)")
    print("3. Use mock data for development and testing")
    
    return False

if __name__ == "__main__":
    check_api_status()