#!/usr/bin/env python3
"""
Fixed SentinelSat example for Copernicus Dataspace API
This script demonstrates how to use sentinelsat with the new API once authentication is working.

Based on the user's original request but updated for the new Copernicus Dataspace Ecosystem.
"""

import os
from datetime import date
try:
    from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
except ImportError:
    print("❌ SentinelSat not installed. Install with: pip install sentinelsat")
    exit(1)

def main():
    print("=== SentinelSat with Copernicus Dataspace API ===")
    print("This example shows how to use sentinelsat once authentication is working.\n")
    
    # Get credentials
    username = os.getenv('COPERNICUS_USER')
    password = os.getenv('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ ERROR: Environment variables not set")
        print("Please set COPERNICUS_USER and COPERNICUS_PASSWORD")
        print("Example:")
        print("export COPERNICUS_USER='your_email@example.com'")
        print("export COPERNICUS_PASSWORD='your_password'")
        return
    
    print(f"✓ Username: {username}")
    print(f"✓ Password: {'*' * len(password)}\n")
    
    # IMPORTANT: Use the new Copernicus Dataspace API endpoint
    # The old endpoint (https://apihub.copernicus.eu/apihub) is deprecated
    new_api_url = "https://catalogue.dataspace.copernicus.eu/odata/v1"
    
    print("🔗 Connecting to Copernicus Dataspace API...")
    print(f"Endpoint: {new_api_url}")
    
    try:
        # Connect to the NEW API endpoint
        api = SentinelAPI(username, password, new_api_url)
        print("✅ Connection established successfully!\n")
        
        # Example search parameters (modified from user's original request)
        print("🔍 Searching for Sentinel-2 products...")
        
        # Since we don't have the user's geojson file, let's use a simple area
        # You can replace this with: footprint = geojson_to_wkt(read_geojson('map.geojson'))
        
        # Example: Search over a small area (you can modify coordinates)
        footprint = "POLYGON((10 40, 11 40, 11 41, 10 41, 10 40))"  # Small area in Italy
        
        # Search parameters from user's original request
        products = api.query(
            footprint,
            date=('20151219', date(2015, 12, 29)),
            platformname='Sentinel-2',
            limit=5  # Limit results for testing
        )
        
        print(f"✅ Found {len(products)} products\n")
        
        if products:
            # Convert to Pandas DataFrame (from user's original request)
            print("📊 Converting to DataFrame...")
            products_df = api.to_dataframe(products)
            
            # Sort and limit to first 5 sorted products (from user's original request)
            print("📈 Sorting by cloud cover and ingestion date...")
            products_df_sorted = products_df.sort_values(
                ['cloudcoverpercentage', 'ingestiondate'], 
                ascending=[True, True]
            )
            products_df_sorted = products_df_sorted.head(5)
            
            print("\n📋 Top 5 products (sorted by cloud cover):")
            print(products_df_sorted[['title', 'cloudcoverpercentage', 'size']].to_string())
            
            # Download option (commented out for safety)
            print("\n💾 Download option:")
            print("To download these products, uncomment the following line:")
            print("# api.download_all(products_df_sorted.index)")
            print("\n⚠️  WARNING: Downloads can be very large (several GB per product)")
            
        else:
            print("ℹ️  No products found for the specified criteria.")
            print("Try adjusting the search parameters (date range, area, etc.)")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        
        if "401" in str(e) or "Unauthorized" in str(e):
            print("\n🚨 AUTHENTICATION ERROR DETECTED")
            print("This indicates your account credentials are not working.")
            print("\nPlease follow these steps:")
            print("1. Run: ./troubleshoot_account.sh")
            print("2. Follow the troubleshooting steps provided")
            print("3. Ensure your account is fully verified and activated")
            
        elif "403" in str(e) or "Forbidden" in str(e):
            print("\n🚨 PERMISSION ERROR DETECTED")
            print("This indicates your account lacks necessary permissions.")
            print("\nPossible solutions:")
            print("1. Ensure your account is fully activated (may take 24 hours)")
            print("2. Check if you need to accept additional terms")
            print("3. Contact help-login@dataspace.copernicus.eu for account upgrade")
            
        else:
            print("\n🔧 TROUBLESHOOTING:")
            print("1. Check your internet connection")
            print("2. Verify the API endpoint is accessible")
            print("3. Try again later (API may be temporarily unavailable)")

if __name__ == "__main__":
    main()
    
    print("\n" + "="*60)
    print("📚 COMPARISON: Old vs New API")
    print("="*60)
    print("❌ OLD (deprecated): https://apihub.copernicus.eu/apihub")
    print("✅ NEW (current):    https://catalogue.dataspace.copernicus.eu/odata/v1")
    print("\n📖 For more information:")
    print("- Documentation: https://documentation.dataspace.copernicus.eu/")
    print("- Support: help-login@dataspace.copernicus.eu")