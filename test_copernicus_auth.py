#!/usr/bin/env python3
"""
Copernicus Dataspace Authentication Test Script

This script helps diagnose 403 Forbidden errors when accessing Sentinel-1 data
through the new Copernicus Dataspace API.
"""

import os
import sys
from sentinelsat import SentinelAPI
from datetime import datetime, timedelta

def test_credentials():
    """Test if Copernicus Dataspace credentials are properly configured."""
    print("🔍 Testing Copernicus Dataspace Authentication...\n")
    
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
    
    print("\n2. API Connection Test:")
    try:
        # Test connection to Copernicus Dataspace
        api = SentinelAPI(user, password, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
        print("   ✅ Successfully connected to Copernicus Dataspace API")
        
        # Test a simple query
        print("\n3. Simple Query Test:")
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
        print(f"   ❌ Connection failed: {e}")
        
        if "403" in str(e) or "Forbidden" in str(e):
            print("\n🔐 403 Forbidden Error Troubleshooting:")
            print("   1. Verify your username and password are correct")
            print("   2. Check if your account is activated (check email)")
            print("   3. Try logging into the web interface: https://dataspace.copernicus.eu/")
            print("   4. Wait a few minutes if you just registered")
            print("   5. Ensure you're using the new Dataspace credentials, not old SciHub ones")
        elif "401" in str(e) or "Unauthorized" in str(e):
            print("\n🔑 401 Unauthorized Error:")
            print("   - Your credentials are incorrect")
            print("   - Double-check your username and password")
        else:
            print("\n🌐 Network/API Error:")
            print("   - Check your internet connection")
            print("   - The API might be temporarily unavailable")
        
        return False

def main():
    print("🛰️  SAR4CET - Copernicus Dataspace Authentication Test\n")
    print("This script will help diagnose authentication issues with the new")
    print("Copernicus Dataspace API that replaced the old SciHub service.\n")
    
    success = test_credentials()
    
    if success:
        print("\n🎉 Authentication test passed!")
        print("Your SAR4CET package should now work correctly.")
    else:
        print("\n❌ Authentication test failed.")
        print("Please follow the troubleshooting steps above.")
    
    print("\n📚 For more help, visit: https://dataspace.copernicus.eu/")

if __name__ == "__main__":
    main()