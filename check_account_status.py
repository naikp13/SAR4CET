#!/usr/bin/env python3
"""
Script to check Copernicus Dataspace account status and troubleshoot common issues.
Based on official documentation: https://documentation.dataspace.copernicus.eu/
"""

import requests
import os
import json
from datetime import datetime

def check_account_status():
    """Check account status and provide troubleshooting steps."""
    
    print("=== Copernicus Dataspace Account Status Checker ===")
    print(f"Timestamp: {datetime.now()}\n")
    
    # Get credentials
    username = os.getenv('COPERNICUS_USER')
    password = os.getenv('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ ERROR: Environment variables not set")
        print("Please set COPERNICUS_USER and COPERNICUS_PASSWORD")
        return False
    
    print(f"✓ Username: {username}")
    print(f"✓ Password: {'*' * len(password)}\n")
    
    # Test 1: Basic token request
    print("🔍 Test 1: Basic OAuth2 Token Request")
    print("-" * 50)
    
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    
    token_data = {
        'client_id': 'cdse-public',
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(token_url, data=token_data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            token_info = response.json()
            print("✅ SUCCESS: Token obtained successfully!")
            print(f"Token Type: {token_info.get('token_type', 'N/A')}")
            print(f"Expires In: {token_info.get('expires_in', 'N/A')} seconds")
            access_token = token_info.get('access_token')
            if access_token:
                print(f"Access Token (first 20 chars): {access_token[:20]}...")
                return test_api_access(access_token)
            
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            try:
                error_info = response.json()
                print(f"Error Details: {json.dumps(error_info, indent=2)}")
                
                # Specific error handling
                if response.status_code == 401:
                    error_desc = error_info.get('error_description', '')
                    if 'Invalid user credentials' in error_desc:
                        print("\n🚨 ACCOUNT ISSUE DETECTED:")
                        print("This error typically indicates:")
                        print("1. ❌ Email not verified - Check your email for verification link")
                        print("2. ❌ Terms & Conditions not accepted - Log into the web portal")
                        print("3. ❌ Account not fully activated - May take up to 24 hours")
                        print("4. ❌ Incorrect password - Try resetting password")
                        print("5. ❌ Account suspended or restricted")
                        
                elif response.status_code == 403:
                    print("\n🚨 PERMISSION ISSUE DETECTED:")
                    print("This error typically indicates:")
                    print("1. ❌ Account lacks necessary permissions")
                    print("2. ❌ Need to upgrade to higher tier account")
                    print("3. ❌ Geographic or usage restrictions")
                    
            except json.JSONDecodeError:
                print(f"Raw Response: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ NETWORK ERROR: {e}")
        return False
    
    print("\n📋 TROUBLESHOOTING STEPS:")
    print("1. 🌐 Log into https://dataspace.copernicus.eu/ with your credentials")
    print("2. ✅ Verify your email address if you haven't already")
    print("3. 📜 Accept all Terms & Conditions and Privacy Policy")
    print("4. ⏰ Wait 24 hours after registration for full activation")
    print("5. 🔄 Try resetting your password if login fails")
    print("6. 📧 Contact help-login@dataspace.copernicus.eu if issues persist")
    
    return False

def test_api_access(access_token):
    """Test API access with the obtained token."""
    
    print("\n🔍 Test 2: API Access Test")
    print("-" * 50)
    
    # Test catalogue access
    catalogue_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$top=1"
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        response = requests.get(catalogue_url, headers=headers, timeout=30)
        
        print(f"Catalogue API Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Catalogue API access working!")
            data = response.json()
            print(f"Total products available: {data.get('@odata.count', 'Unknown')}")
            return True
        else:
            print(f"❌ FAILED: Catalogue API returned {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ NETWORK ERROR: {e}")
    
    return False

if __name__ == "__main__":
    success = check_account_status()
    
    if success:
        print("\n🎉 ACCOUNT STATUS: FULLY FUNCTIONAL")
        print("Your account is properly set up and ready to use!")
    else:
        print("\n⚠️  ACCOUNT STATUS: NEEDS ATTENTION")
        print("Please follow the troubleshooting steps above.")