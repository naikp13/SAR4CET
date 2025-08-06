#!/usr/bin/env python3
"""
Test script for openEO integration in SAR4CET.

This script tests the new openEO-based Sentinel-1 data access functionality.
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sar4cet.preprocessing import (
    get_openeo_connection, list_available_collections, get_collection_info,
    search_sentinel1_openeo, download_sentinel1_openeo
)

def test_openeo_connection():
    """Test openEO connection."""
    print("Testing openEO connection...")
    try:
        connection = get_openeo_connection()
        print(f"✅ Connected to openEO backend: {connection.url}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to openEO: {e}")
        return False

def test_list_collections():
    """Test listing available collections."""
    print("\nTesting collection listing...")
    try:
        collections = list_available_collections()
        print(f"✅ Found {len(collections)} collections")
        
        # Look for Sentinel-1 collections
        s1_collections = [c for c in collections if 'sentinel-1' in c.lower() or 's1' in c.lower()]
        if s1_collections:
            print(f"📡 Sentinel-1 collections found: {s1_collections[:3]}")
        else:
            print("⚠️  No Sentinel-1 collections found in listing")
        return True
    except Exception as e:
        print(f"❌ Failed to list collections: {e}")
        return False

def test_describe_collection():
    """Test describing a collection."""
    print("\nTesting collection description...")
    try:
        # Try common Sentinel-1 collection names
        collection_names = ['SENTINEL1_GRD', 'S1_GRD', 'sentinel-1-grd']
        
        for collection_name in collection_names:
            try:
                description = get_collection_info(collection_name)
                print(f"✅ Successfully described collection: {collection_name}")
                print(f"   Description: {description.get('description', 'No description')[:100]}...")
                return True
            except Exception:
                continue
        
        print("⚠️  Could not describe any Sentinel-1 collection")
        return False
    except Exception as e:
        print(f"❌ Failed to describe collection: {e}")
        return False

def test_search_functionality():
    """Test search functionality with a small AOI."""
    print("\nTesting search functionality...")
    try:
        # Small test area (San Francisco Bay Area)
        aoi = [-122.5, 37.5, -122.0, 38.0]  # [lon_min, lat_min, lon_max, lat_max]
        start_date = "2023-01-01"
        end_date = "2023-01-31"
        
        print(f"Searching for Sentinel-1 data in AOI: {aoi}")
        print(f"Date range: {start_date} to {end_date}")
        
        results = search_sentinel1_openeo(
            aoi=aoi,
            start_date=start_date,
            end_date=end_date,
            polarization='VV,VH',
            product_type='GRD'
        )
        
        print(f"✅ Search completed. Found {len(results)} products")
        
        if results:
            # Show first few results
            for i, (product_id, product_info) in enumerate(list(results.items())[:3]):
                title = product_info.get('title', 'Unknown')
                date = product_info.get('beginposition', 'Unknown')[:10]
                print(f"   {i+1}. {title} - {date}")
        
        return True
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False

def main():
    """Run all tests."""
    print("SAR4CET openEO Integration Test")
    print("=" * 40)
    
    # Check environment variables
    client_id = os.environ.get('COPERNICUS_CLIENT_ID')
    client_secret = os.environ.get('COPERNICUS_CLIENT_SECRET')
    
    if client_id and client_secret:
        print("✅ OAuth2 credentials found")
    else:
        print("⚠️  No OAuth2 credentials found. Will use interactive authentication.")
        print("   Set COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET for automated access.")
    
    print()
    
    # Run tests
    tests = [
        test_openeo_connection,
        test_list_collections,
        test_describe_collection,
        test_search_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! openEO integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("   Common issues:")
        print("   - Missing openEO library: pip install openeo")
        print("   - Network connectivity issues")
        print("   - Authentication problems")

if __name__ == "__main__":
    main()