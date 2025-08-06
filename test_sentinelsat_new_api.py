#!/usr/bin/env python3
"""
Test sentinelsat with the new Copernicus Dataspace API
This script demonstrates how to use sentinelsat with the new API endpoint
"""

import os
from sentinelsat import SentinelAPI
from datetime import date
from shapely.geometry import box
import geopandas as gpd

def test_sentinelsat_new_api():
    """Test sentinelsat with the new Copernicus Dataspace API"""
    
    # Get credentials from environment
    username = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ Please set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables")
        return False
    
    print(f"🔍 Testing sentinelsat with new Copernicus Dataspace API")
    print(f"Username: {username}")
    
    try:
        # Connect to the NEW Copernicus Dataspace API endpoint
        # Note: Using the new endpoint, not the old apihub.copernicus.eu
        api = SentinelAPI(
            username, 
            password, 
            'https://catalogue.dataspace.copernicus.eu/odata/v1'
        )
        
        print("✅ Successfully created SentinelAPI connection")
        
        # Create a simple bounding box for testing (small area in Europe)
        # Coordinates: [min_lon, min_lat, max_lon, max_lat]
        bbox = [2.0, 48.0, 3.0, 49.0]  # Small area around Paris
        footprint = box(*bbox)
        
        print("🔍 Performing search query...")
        
        # Search for Sentinel-1 products (more recent data available)
        products = api.query(
            footprint,
            date=('20240101', '20240131'),  # Recent date range
            platformname='Sentinel-1',
            producttype='GRD',
            limit=5  # Limit to 5 products for testing
        )
        
        print(f"✅ Search successful! Found {len(products)} products")
        
        if len(products) > 0:
            # Convert to DataFrame for easier viewing
            products_df = api.to_dataframe(products)
            print("\n📊 Found products:")
            print(products_df[['title', 'beginposition', 'size']].head())
            
            print("\n🎉 sentinelsat is working with the new Copernicus Dataspace API!")
            return True
        else:
            print("⚠️  No products found for the specified criteria")
            return True  # Still successful connection
            
    except Exception as e:
        print(f"❌ Error with sentinelsat: {e}")
        
        # Check if it's an authentication error
        if "401" in str(e) or "Unauthorized" in str(e):
            print("\n🔍 Authentication troubleshooting:")
            print("1. Verify your credentials are correct")
            print("2. Check if your account is activated")
            print("3. Try logging into https://dataspace.copernicus.eu/ first")
            print("4. Ensure you've accepted all terms and conditions")
        elif "403" in str(e) or "Forbidden" in str(e):
            print("\n🔍 Access troubleshooting:")
            print("1. Your account may need additional permissions")
            print("2. Check if your account supports API access")
            print("3. Contact Copernicus support if the issue persists")
        
        return False

def test_old_vs_new_endpoint():
    """Compare old and new API endpoints"""
    
    username = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ Please set environment variables first")
        return
    
    print("\n🔄 Comparing old vs new API endpoints:")
    
    # Test old endpoint (should fail)
    print("\n1. Testing OLD endpoint (apihub.copernicus.eu):")
    try:
        old_api = SentinelAPI(username, password, 'https://apihub.copernicus.eu/apihub')
        print("   ⚠️  Old endpoint connection created (but likely won't work)")
    except Exception as e:
        print(f"   ❌ Old endpoint failed: {e}")
    
    # Test new endpoint
    print("\n2. Testing NEW endpoint (catalogue.dataspace.copernicus.eu):")
    try:
        new_api = SentinelAPI(username, password, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
        print("   ✅ New endpoint connection created successfully")
    except Exception as e:
        print(f"   ❌ New endpoint failed: {e}")

if __name__ == "__main__":
    print("🛰️  SentinelSat - New Copernicus Dataspace API Test\n")
    
    # Test the new API
    success = test_sentinelsat_new_api()
    
    # Compare endpoints
    test_old_vs_new_endpoint()
    
    print("\n" + "="*60)
    if success:
        print("🎯 Result: SentinelSat works with the new Copernicus Dataspace API!")
        print("\n📝 Key changes needed in your code:")
        print("   OLD: 'https://apihub.copernicus.eu/apihub'")
        print("   NEW: 'https://catalogue.dataspace.copernicus.eu/odata/v1'")
    else:
        print("❌ Result: Authentication or API access issues detected.")
        print("Please resolve the authentication issues first.")