#!/usr/bin/env python3
"""
AnchorAlpha API Testing Script - Fixed Version
Tests all external APIs before deployment to ensure they're working properly.
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
    """Test Financial Modeling Prep API"""
    print_status("Testing Financial Modeling Prep API...")
    
    # Check if API key is set
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print_status("FMP_API_KEY not set in environment", "WARNING")
        return False
    
    if api_key in ['your_fmp_api_key_here', 'YOUR_FMP_API_KEY_HERE']:
        print_status("FMP_API_KEY is still placeholder value", "WARNING")
        return False
    
    try:
        # Test 1: Basic API connectivity with a simple stock profile
        print_status("  Testing basic connectivity with AAPL profile...")
        url = f"https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                print_status(f"  ✅ Basic connectivity: SUCCESS (Company: {data[0].get('companyName', 'N/A')})", "SUCCESS")
            else:
                print_status("  ❌ Basic connectivity: Empty response", "ERROR")
                return False
        elif response.status_code == 401:
            print_status("  ❌ Authentication failed - Invalid API key", "ERROR")
            return False
        elif response.status_code == 403:
            print_status("  ❌ Access forbidden - Check API key permissions", "ERROR")
            return False
        elif response.status_code == 429:
            print_status("  ❌ Rate limit exceeded", "ERROR")
            return False
        else:
            print_status(f"  ❌ API error: HTTP {response.status_code}", "ERROR")
            print_status(f"    Response: {response.text[:200]}", "ERROR")
            return False
        
        # Test 2: Stock screener endpoint (main functionality)
        print_status("  Testing stock screener endpoint...")
        screener_url = f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=10000000000&limit=5&apikey={api_key}"
        response = requests.get(screener_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                print_status(f"  ✅ Stock screener: SUCCESS ({len(data)} stocks found)", "SUCCESS")
                # Show sample stock
                sample = data[0]
                print_status(f"    Sample: {sample.get('symbol')} - {sample.get('companyName')} (${sample.get('marketCap', 0):,.0f})", "INFO")
            else:
                print_status("  ❌ Stock screener: No stocks returned", "ERROR")
                return False
        else:
            print_status(f"  ❌ Stock screener error: HTTP {response.status_code}", "ERROR")
            return False
        
        print_status("FMP API: ALL TESTS PASSED ✅", "SUCCESS")
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
    print_status("🧪 AnchorAlpha API Testing Suite (Fixed)", "INFO")
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
    print_status("🎯 TEST RESULTS SUMMARY", "INFO")
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
        return True
    else:
        print_status("⚠️  Some APIs need configuration before deployment", "WARNING")
        print_status("Please fix the failing tests and run again", "INFO")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)