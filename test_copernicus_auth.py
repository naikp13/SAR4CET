#!/usr/bin/env python3
"""
Copernicus Dataspace API Authentication Test

This script tests the authentication with the new Copernicus Dataspace API
using OAuth2 access tokens to help diagnose 403 Forbidden errors during 
Sentinel-1 data download.
"""

import os
import sys
import requests
from sentinelsat import SentinelAPI
from datetime import datetime, timedelta

def get_access_token(username, password):
    """
    Get OAuth2 access token for Copernicus Dataspace API using password grant
    """
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    
    data = {
        'client_id': 'cdse-public',
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get access token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return None

def test_credentials():
    """Test if Copernicus Dataspace credentials are properly configured using OAuth2."""
    print("🔍 Testing Copernicus Dataspace Authentication (OAuth2)...\n")
    
    # Check environment variables
    user = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    print("1. Environment Variables Check:")
    if user:
        print(f"   ✅ COPERNICUS_USER: {user}")
    else:
        print("   ❌ COPERNICUS_USER: Not set")
        
    if password:
        print(f"   ✅ COPERNICUS_PASSWORD: {'*' * len(password)} (hidden)")
    else:
        print("   ❌ COPERNICUS_PASSWORD: Not set")
    
    if not user or not password:
        print("\n🚨 Missing Credentials!")
        print("Please set your environment variables:")
        print("   export COPERNICUS_USER='your_username'")
        print("   export COPERNICUS_PASSWORD='your_password'")
        print("\n📝 Register at: https://dataspace.copernicus.eu/")
        return False
    
    print("\n2. OAuth2 Token Request:")
    try:
        # Get OAuth2 access token
        access_token = get_access_token(user, password)
        print("   ✅ OAuth2 access token obtained successfully!")
        
        # Test connection to Copernicus Dataspace with token
        print("\n3. API Connection Test:")
        api = SentinelAPI('token', access_token, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
        print("   ✅ Successfully connected to Copernicus Dataspace API")
        
        # Test a simple query
        print("\n4. Simple Query Test:")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Small area around Rome for testing
        footprint = "POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))"
        
        products = api.query(
            footprint,
            date=(start_date, end_date),
            platformname='Sentinel-1',
            producttype='GRD',
            limit=1  # Only get 1 result for testing
        )
        
        print(f"   ✅ Query successful! Found {len(products)} products")
        
        if products:
            product_id, product_info = next(iter(products.items()))
            print(f"   📡 Sample product: {product_info['title']}")
            print(f"   📅 Date: {product_info['beginposition']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        
        error_str = str(e).lower()
        
        if "403" in error_str or "forbidden" in error_str:
            print("\n🔐 403 Forbidden Error Troubleshooting:")
            print("   1. Verify your username and password are correct")
            print("   2. Check if your account is activated (check email)")
            print("   3. Try logging into the web interface: https://dataspace.copernicus.eu/")
            print("   4. Ensure your account has been activated for at least 24 hours")
            print("   5. If you can log in to the website but API fails, contact support")
            print("   6. Consider resetting your password")
        elif "401" in error_str or "unauthorized" in error_str:
            print("\n🔑 401 Unauthorized Error:")
            print("   1. Double-check your username and password")
            print("   2. Ensure there are no extra spaces in your credentials")
            print("   3. Try resetting your password on the website")
            print("   4. Make sure your account is fully activated")
        elif "token" in error_str:
            print("\n🔍 OAuth2 Token Error:")
            print("   1. Your credentials might be correct but the OAuth2 flow failed")
            print("   2. Try logging into the website first to ensure your account is active")
            print("   3. Wait a few minutes and try again")
            print("   4. Check if there are any special characters in your password")
        else:
            print("\n🌐 Network/API Error:")
            print("   - Check your internet connection")
            print("   - The API might be temporarily unavailable")
            print("   - Ensure you're using the latest version of sentinelsat (>=1.2.1)")
        
        return False

def main():
    print("🛰️  SAR4CET - Copernicus Dataspace Authentication Test\n")
    print("This script will help diagnose authentication issues with the new")
    print("Copernicus Dataspace API that replaced the old SciHub service.\n")
    
    success = test_credentials()
    
    if success:
        print("\n🎉 Authentication test passed!")
        print("Your SAR4CET package should now work correctly with OAuth2 authentication.")
    else:
        print("\n❌ Authentication test failed.")
        print("Please follow the troubleshooting steps above.")
    
    print("\n📚 For more help, visit: https://dataspace.copernicus.eu/")

if __name__ == "__main__":
    main()