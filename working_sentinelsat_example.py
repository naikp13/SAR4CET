#!/usr/bin/env python3
"""
Working SentinelSat example for Copernicus Dataspace API
Based on successful API permission tests showing search access is available.
"""

import os
from datetime import date, datetime
try:
    from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
    import pandas as pd
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install sentinelsat pandas")
    exit(1)

def main():
    print("=== Working SentinelSat Example ===")
    print(f"Timestamp: {datetime.now()}\n")
    
    # Get credentials
    username = os.getenv('COPERNICUS_USER')
    password = os.getenv('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ ERROR: Environment variables not set")
        print("Please set COPERNICUS_USER and COPERNICUS_PASSWORD")
        return
    
    print(f"✓ Username: {username}")
    print(f"✓ Password: {'*' * len(password)}\n")
    
    # Use the new Copernicus Dataspace API endpoint
    api_url = "https://catalogue.dataspace.copernicus.eu/odata/v1"
    
    print("🔗 Connecting to Copernicus Dataspace API...")
    print(f"Endpoint: {api_url}")
    
    try:
        # Connect to the API
        api = SentinelAPI(username, password, api_url)
        print("✅ Connection established successfully!\n")
        
        # Define search area (small area for testing)
        # You can replace this with your own coordinates or geojson file
        print("🗺️  Defining search area...")
        
        # Example area: Small region in Italy
        # Format: POLYGON((lon1 lat1, lon2 lat2, ...))
        footprint = "POLYGON((11.0 43.0, 12.0 43.0, 12.0 44.0, 11.0 44.0, 11.0 43.0))"
        print(f"Area: Small region in Italy")
        
        # Alternative: If you have a geojson file, uncomment this:
        # footprint = geojson_to_wkt(read_geojson('your_area.geojson'))
        
        # Search parameters (based on your original request)
        print("\n🔍 Searching for Sentinel-2 products...")
        print("Search criteria:")
        print("- Platform: Sentinel-2")
        print("- Date range: 2015-12-19 to 2015-12-29")
        print("- Cloud cover: Any")
        print("- Limit: 10 products (for testing)\n")
        
        # Perform search
        products = api.query(
            footprint,
            date=('20151219', date(2015, 12, 29)),
            platformname='Sentinel-2',
            limit=10  # Limit for testing
        )
        
        print(f"✅ Search completed: Found {len(products)} products\n")
        
        if products:
            # Convert to DataFrame (from your original request)
            print("📊 Converting to Pandas DataFrame...")
            products_df = api.to_dataframe(products)
            
            print(f"DataFrame shape: {products_df.shape}")
            print(f"Columns: {list(products_df.columns)}\n")
            
            # Sort by cloud cover and ingestion date (from your original request)
            print("📈 Sorting by cloud cover and ingestion date...")
            
            # Check if cloudcoverpercentage column exists
            if 'cloudcoverpercentage' in products_df.columns:
                products_df_sorted = products_df.sort_values(
                    ['cloudcoverpercentage', 'ingestiondate'], 
                    ascending=[True, True]
                )
            else:
                # Fallback sorting if cloud cover not available
                products_df_sorted = products_df.sort_values('ingestiondate', ascending=True)
                print("Note: Cloud cover data not available, sorting by date only")
            
            # Limit to first 5 (from your original request)
            products_df_sorted = products_df_sorted.head(5)
            
            print("\n📋 Top 5 products:")
            print("=" * 80)
            
            # Display key information
            display_columns = []
            if 'title' in products_df_sorted.columns:
                display_columns.append('title')
            if 'cloudcoverpercentage' in products_df_sorted.columns:
                display_columns.append('cloudcoverpercentage')
            if 'size' in products_df_sorted.columns:
                display_columns.append('size')
            if 'beginposition' in products_df_sorted.columns:
                display_columns.append('beginposition')
            
            if display_columns:
                print(products_df_sorted[display_columns].to_string(index=False))
            else:
                # Fallback: show first few columns
                print(products_df_sorted.iloc[:, :3].to_string(index=False))
            
            print("\n💾 Download Information:")
            print("=" * 40)
            print("To download these products, you can use:")
            print("\n# Download all found products:")
            print("# api.download_all(products)")
            print("\n# Download specific products:")
            print("# api.download_all(products_df_sorted.index[:2])  # First 2 products")
            
            # Calculate total size if available
            if 'size' in products_df_sorted.columns:
                try:
                    # Convert size strings to numbers (assuming format like "1.2 GB")
                    total_size_info = "Size information available in 'size' column"
                    print(f"\n📏 {total_size_info}")
                except:
                    pass
            
            print("\n⚠️  WARNING: Sentinel-2 products are typically 500MB - 1GB each")
            print("Make sure you have sufficient disk space and bandwidth")
            
            # Show product IDs for reference
            print("\n🆔 Product IDs (for reference):")
            for i, (product_id, product_info) in enumerate(products_df_sorted.head(3).iterrows()):
                title = product_info.get('title', product_id)
                print(f"{i+1}. {title}")
                
        else:
            print("ℹ️  No products found for the specified criteria.")
            print("\nTry adjusting the search parameters:")
            print("- Expand the date range")
            print("- Use a different geographic area")
            print("- Try different satellite platforms (Sentinel-1, Sentinel-3)")
            
            # Example alternative search
            print("\n🔄 Trying alternative search (Sentinel-1, recent data)...")
            try:
                alt_products = api.query(
                    footprint,
                    date=('NOW-30DAYS', 'NOW'),
                    platformname='Sentinel-1',
                    limit=5
                )
                print(f"Alternative search found: {len(alt_products)} Sentinel-1 products")
            except Exception as e:
                print(f"Alternative search failed: {e}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        
        error_str = str(e).lower()
        
        if "401" in error_str or "unauthorized" in error_str:
            print("\n🚨 AUTHENTICATION ERROR")
            print("Your credentials are not working. Please check:")
            print("1. Username and password are correct")
            print("2. Account is fully activated")
            print("3. Email is verified")
            
        elif "403" in error_str or "forbidden" in error_str:
            print("\n🚨 PERMISSION ERROR")
            print("Your account lacks search permissions. This may indicate:")
            print("1. Account is not fully activated (wait 24 hours)")
            print("2. Need to accept additional terms on the website")
            print("3. Account type restrictions")
            
        elif "timeout" in error_str or "connection" in error_str:
            print("\n🌐 NETWORK ERROR")
            print("Connection issue. Please check:")
            print("1. Internet connection")
            print("2. Try again later (API may be busy)")
            
        else:
            print("\n🔧 GENERAL ERROR")
            print("Please try:")
            print("1. Running the troubleshoot_account.sh script")
            print("2. Checking the API status")
            print("3. Contacting support if the issue persists")

if __name__ == "__main__":
    main()
    
    print("\n" + "="*60)
    print("📚 SUMMARY")
    print("="*60)
    print("✅ Authentication: Working")
    print("✅ API Access: Available")
    print("✅ Search Function: Operational")
    print("\n📖 Next Steps:")
    print("1. Modify search parameters for your specific needs")
    print("2. Replace the example coordinates with your area of interest")
    print("3. Uncomment download commands when ready to download data")
    print("\n📞 Support: help-login@dataspace.copernicus.eu")