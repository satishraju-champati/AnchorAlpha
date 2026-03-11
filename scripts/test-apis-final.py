#!/usr/bin/env python3
"""
AnchorAlpha Final API Testing Script
Tests all external APIs with correct endpoints before deployment.
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m", 
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}{status}: {message}{colors['RESET']}")

def test_fmp_api():
    """Test Financial Modeling Prep API with new /stable/ endpoints"""
    print_status("Testing Financial Modeling Prep API (New /stable/ endpoints)...")
    
    # Check if API key is set
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print_status("FMP_API_KEY not set in environment", "WARNING")
        return False
    
    if api_key in ['your_fmp_api_key_here', 'YOUR_FMP_API_KEY_HERE']:
        print_status("FMP_API_KEY is still placeholder value", "WARNING")
        return False
    
    try:
        # Test 1: Company Profile (basic connectivity)
        print_status("  Testing company profile endpoint...")
        url = f"https://financialmodelingprep.com/stable/profile?symbol=AAPL&apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                company = data[0]
                print_status(f"  ✅ Company profile: SUCCESS", "SUCCESS")
                print_status(f"    Company: {company.get('companyName', 'N/A')}", "INFO")
                print_status(f"    Market Cap: ${company.get('marketCap', 0):,.0f}", "INFO")
                print_status(f"    Price: ${company.get('price', 0):.2f}", "INFO")
            else:
                print_status("  ❌ Company profile: Empty response", "ERROR")
                return False
        else:
            print_status(f"  ❌ Company profile error: HTTP {response.status_code}", "ERROR")
            print_status(f"    Response: {response.text[:200]}", "ERROR")
            return False
        
        # Test 2: Stock Quote
        print_status("  Testing stock quote endpoint...")
        quote_url = f"https://financialmodelingprep.com/stable/quote?symbol=MSFT&apikey={api_key}"
        response = requests.get(quote_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                quote = data[0]
                print_status(f"  ✅ Stock quote: SUCCESS", "SUCCESS")
                print_status(f"    Symbol: {quote.get('symbol')} - ${quote.get('price', 0):.2f}", "INFO")
                print_status(f"    Change: {quote.get('changePercentage', 0):.2f}%", "INFO")
            else:
                print_status("  ❌ Stock quote: Empty response", "ERROR")
                return False
        else:
            print_status(f"  ❌ Stock quote error: HTTP {response.status_code}", "ERROR")
            return False
        
        # Test 3: Multiple stock quotes (simulate screener functionality)
        print_status("  Testing multiple stock quotes (screener simulation)...")
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        successful_quotes = 0
        
        for symbol in symbols:
            try:
                symbol_url = f"https://financialmodelingprep.com/stable/quote?symbol={symbol}&apikey={api_key}"
                response = requests.get(symbol_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        successful_quotes += 1
                time.sleep(0.2)  # Rate limiting
            except:
                continue
        
        if successful_quotes >= 3:
            print_status(f"  ✅ Multiple quotes: SUCCESS ({successful_quotes}/{len(symbols)} stocks)", "SUCCESS")
        else:
            print_status(f"  ❌ Multiple quotes: Only {successful_quotes}/{len(symbols)} successful", "ERROR")
            return False
        
        print_status("FMP API: ALL TESTS PASSED ✅", "SUCCESS")
        print_status("  Note: Using /stable/ endpoints with profile and quote data", "INFO")
        return True
        
    except requests.exceptions.Timeout:
        print_status("  ❌ FMP API timeout", "ERROR")
        return False
    except requests.exceptions.ConnectionError:
        print_status("  ❌ FMP API connection error", "ERROR")
        return False
    except Exception as e:
        print_status(f"  ❌ FMP API error: {str(e)}", "ERROR")
        return False

def test_perplexity_api():
    """Test Perplexity Sonar API"""
    print_status("Testing Perplexity Sonar API...")
    
    # Check if API key is set
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print_status("PERPLEXITY_API_KEY not set in environment", "WARNING")
        return False
    
    if api_key in ['your_perplexity_api_key_here', 'YOUR_PERPLEXITY_API_KEY_HERE']:
        print_status("PERPLEXITY_API_KEY is still placeholder value", "WARNING")
        return False
    
    try:
        # Test basic API connectivity with correct model name
        print_status("  Testing basic connectivity...")
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar",  # Using the correct model name from our codebase
            "messages": [
                {
                    "role": "user",
                    "content": "What is Apple Inc? Keep response under 30 words."
                }
            ],
            "max_tokens": 50,
            "temperature": 0.2
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content']
                print_status("  ✅ Basic connectivity: SUCCESS", "SUCCESS")
                print_status(f"    Sample response: {content[:100]}...", "INFO")
            else:
                print_status("  ❌ Basic connectivity: Invalid response format", "ERROR")
                return False
        elif response.status_code == 401:
            print_status("  ❌ Authentication failed - Invalid API key", "ERROR")
            return False
        elif response.status_code == 429:
            print_status("  ❌ Rate limit exceeded", "ERROR")
            return False
        else:
            print_status(f"  ❌ API error: HTTP {response.status_code}", "ERROR")
            print_status(f"    Response: {response.text[:200]}", "ERROR")
            return False
        
        print_status("Perplexity API: ALL TESTS PASSED ✅", "SUCCESS")
        return True
        
    except requests.exceptions.Timeout:
        print_status("  ❌ Perplexity API timeout", "ERROR")
        return False
    except requests.exceptions.ConnectionError:
        print_status("  ❌ Perplexity API connection error", "ERROR")
        return False
    except Exception as e:
        print_status(f"  ❌ Perplexity API error: {str(e)}", "ERROR")
        return False

def test_aws_connectivity():
    """Test AWS connectivity (basic check)"""
    print_status("Testing AWS connectivity...")
    
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        
        # Test STS (basic AWS connectivity)
        print_status("  Testing AWS credentials...")
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print_status("  ✅ AWS credentials: SUCCESS", "SUCCESS")
        print_status(f"    Account: {identity.get('Account')}", "INFO")
        print_status(f"    User/Role: {identity.get('Arn', 'N/A').split('/')[-1]}", "INFO")
        
        # Test basic AWS services (don't require specific permissions)
        print_status("  Testing basic AWS service access...")
        
        # Test regions (should always work)
        ec2 = boto3.client('ec2')
        regions = ec2.describe_regions()
        print_status(f"  ✅ AWS service access: SUCCESS ({len(regions['Regions'])} regions available)", "SUCCESS")
        
        print_status("AWS connectivity: BASIC TESTS PASSED ✅", "SUCCESS")
        print_status("  Note: Full S3/Lambda permissions will be tested during deployment", "INFO")
        return True
        
    except NoCredentialsError:
        print_status("  ❌ AWS credentials not configured", "ERROR")
        print_status("    Run: aws configure", "INFO")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            print_status("  ❌ AWS access denied - insufficient permissions", "ERROR")
        else:
            print_status(f"  ❌ AWS error: {error_code}", "ERROR")
        return False
    except Exception as e:
        print_status(f"  ❌ AWS error: {str(e)}", "ERROR")
        return False

def test_internet_connectivity():
    """Test basic internet connectivity"""
    print_status("Testing internet connectivity...")
    
    test_urls = [
        ("Google DNS", "https://dns.google"),
        ("GitHub", "https://api.github.com"),
        ("AWS", "https://aws.amazon.com")
    ]
    
    for name, url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 400:
                print_status(f"  ✅ {name}: SUCCESS", "SUCCESS")
            else:
                print_status(f"  ❌ {name}: HTTP {response.status_code}", "WARNING")
        except Exception as e:
            print_status(f"  ❌ {name}: {str(e)}", "ERROR")
            return False
    
    print_status("Internet connectivity: ALL TESTS PASSED ✅", "SUCCESS")
    return True

def main():
    """Run all API tests"""
    print_status("🧪 AnchorAlpha Final API Testing Suite", "INFO")
    print_status("=" * 50, "INFO")
    
    # Load environment variables from .env if it exists
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_file):
        print_status(f"Loading environment from {env_file}", "INFO")
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    results = []
    
    # Test internet connectivity first
    results.append(("Internet Connectivity", test_internet_connectivity()))
    
    # Test AWS connectivity
    results.append(("AWS Connectivity", test_aws_connectivity()))
    
    # Test FMP API
    results.append(("FMP API", test_fmp_api()))
    
    # Test Perplexity API
    results.append(("Perplexity API", test_perplexity_api()))
    
    # Summary
    print_status("=" * 50, "INFO")
    print_status("🎯 FINAL TEST RESULTS", "INFO")
    print_status("=" * 50, "INFO")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        color = "SUCCESS" if result else "ERROR"
        print_status(f"{test_name}: {status}", color)
        if result:
            passed += 1
    
    print_status("=" * 50, "INFO")
    print_status(f"TOTAL: {passed}/{total} tests passed", "SUCCESS" if passed == total else "ERROR")
    
    if passed == total:
        print_status("🎉 ALL APIS READY FOR DEPLOYMENT!", "SUCCESS")
        print_status("", "INFO")
        print_status("✅ DEPLOYMENT READINESS:", "SUCCESS")
        print_status("  • Internet connectivity: Working", "INFO")
        print_status("  • AWS credentials: Configured", "INFO")
        print_status("  • FMP API: Working with /stable/ endpoints", "INFO")
        print_status("  • Perplexity API: Working with 'sonar' model", "INFO")
        print_status("", "INFO")
        print_status("🚀 READY TO DEPLOY! Run: ./scripts/deploy-prod.sh", "SUCCESS")
        return True
    else:
        print_status("⚠️  Some APIs need configuration before deployment", "WARNING")
        print_status("Please fix the failing tests and run again", "INFO")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)