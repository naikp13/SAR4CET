#!/usr/bin/env python3
"""
Direct API implementation for Copernicus Dataspace
This bypasses SentinelSat and uses the API directly, based on successful endpoint tests.
"""

import os
import requests
import json
from datetime import datetime, date
import pandas as pd
from urllib.parse import quote

def get_access_token():
    """Get OAuth2 access token."""
    username = os.getenv('COPERNICUS_USER')
    password = os.getenv('COPERNICUS_PASSWORD')
    
    if not username or not password:
        return None, "Environment variables not set"
    
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    
    token_data = {
        'client_id': 'cdse-public',
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(token_url, data=token_data, timeout=30)
        if response.status_code == 200:
            return response.json().get('access_token'), None
        else:
            return None, f"Token request failed: {response.status_code} - {response.text}"
    except Exception as e:
        return None, f"Token request error: {e}"

def search_products(access_token, platform='Sentinel-2', start_date='2015-12-19', end_date='2015-12-29', limit=10):
    """Search for products using direct API calls."""
    
    base_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Build filter for platform and date range
    filters = []
    
    # Platform filter
    if platform == 'Sentinel-2':
        filters.append("Collection/Name eq 'SENTINEL-2'")
    elif platform == 'Sentinel-1':
        filters.append("Collection/Name eq 'SENTINEL-1'")
    elif platform == 'Sentinel-3':
        filters.append("Collection/Name eq 'SENTINEL-3'")
    
    # Date filter
    if start_date and end_date:
        filters.append(f"ContentDate/Start ge {start_date}T00:00:00.000Z")
        filters.append(f"ContentDate/Start le {end_date}T23:59:59.999Z")
    
    # Combine filters
    filter_str = " and ".join(filters)
    
    # Build query parameters
    params = {
        '$top': limit,
        '$orderby': 'ContentDate/Start desc'
    }
    
    if filter_str:
        params['$filter'] = filter_str
    
    print(f"🔍 API Query: {base_url}")
    print(f"📋 Filters: {filter_str}")
    print(f"📊 Limit: {limit}\n")
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=60)
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('value', [])
            total_count = data.get('@odata.count', len(products))
            
            print(f"✅ Success: Found {len(products)} products (total available: {total_count})")
            return products, None
        else:
            error_msg = f"API request failed: {response.status_code} - {response.text[:500]}"
            print(f"❌ {error_msg}")
            return [], error_msg
            
    except Exception as e:
        error_msg = f"API request error: {e}"
        print(f"❌ {error_msg}")
        return [], error_msg

def process_products(products):
    """Process and display product information."""
    
    if not products:
        print("ℹ️  No products to process")
        return None
    
    print(f"\n📊 Processing {len(products)} products...")
    
    # Extract key information
    processed_data = []
    
    for product in products:
        product_info = {
            'id': product.get('Id', 'N/A'),
            'name': product.get('Name', 'N/A'),
            'collection': product.get('Collection', {}).get('Name', 'N/A'),
            'size_mb': product.get('ContentLength', 0) / (1024*1024) if product.get('ContentLength') else 0,
            'start_date': product.get('ContentDate', {}).get('Start', 'N/A'),
            'end_date': product.get('ContentDate', {}).get('End', 'N/A'),
            'footprint': product.get('Footprint', 'N/A'),
            'download_url': f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product.get('Id')})/$value"
        }
        
        # Extract additional attributes if available
        attributes = product.get('Attributes', [])
        for attr in attributes:
            attr_name = attr.get('Name', '').lower()
            attr_value = attr.get('Value')
            
            if 'cloud' in attr_name and 'cover' in attr_name:
                try:
                    product_info['cloud_cover'] = float(attr_value)
                except:
                    product_info['cloud_cover'] = attr_value
            elif 'instrument' in attr_name:
                product_info['instrument'] = attr_value
            elif 'product' in attr_name and 'type' in attr_name:
                product_info['product_type'] = attr_value
        
        processed_data.append(product_info)
    
    # Create DataFrame
    df = pd.DataFrame(processed_data)
    
    print("\n📋 Product Summary:")
    print("=" * 80)
    
    # Display key columns
    display_columns = ['name', 'collection', 'start_date', 'size_mb']
    if 'cloud_cover' in df.columns:
        display_columns.append('cloud_cover')
    
    # Sort by cloud cover if available, otherwise by date
    if 'cloud_cover' in df.columns:
        df_sorted = df.sort_values(['cloud_cover', 'start_date'], ascending=[True, True])
        print("Sorted by: Cloud cover (ascending), then date")
    else:
        df_sorted = df.sort_values('start_date', ascending=False)
        print("Sorted by: Date (newest first)")
    
    # Show top 5 products
    top_products = df_sorted.head(5)
    
    for i, (_, product) in enumerate(top_products.iterrows(), 1):
        print(f"\n{i}. {product['name']}")
        print(f"   Collection: {product['collection']}")
        print(f"   Date: {product['start_date'][:10] if product['start_date'] != 'N/A' else 'N/A'}")
        print(f"   Size: {product['size_mb']:.1f} MB")
        if 'cloud_cover' in product and pd.notna(product['cloud_cover']):
            print(f"   Cloud Cover: {product['cloud_cover']}%")
        if 'product_type' in product:
            print(f"   Type: {product['product_type']}")
    
    print("\n💾 Download Information:")
    print("=" * 40)
    print("To download products, use the download URLs:")
    for i, (_, product) in enumerate(top_products.head(3).iterrows(), 1):
        print(f"\n{i}. {product['name'][:50]}...")
        print(f"   URL: {product['download_url']}")
    
    print("\n📝 Download Example:")
    print("# Using curl:")
    print(f"# curl -H 'Authorization: Bearer YOUR_TOKEN' '{top_products.iloc[0]['download_url']}' -o product.zip")
    print("\n# Using Python requests:")
    print("# response = requests.get(download_url, headers={'Authorization': f'Bearer {access_token}'})")
    print("# with open('product.zip', 'wb') as f: f.write(response.content)")
    
    return df_sorted

def main():
    print("=== Direct Copernicus Dataspace API Example ===")
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
    
    # Get access token
    print("🔑 Getting access token...")
    access_token, error = get_access_token()
    
    if not access_token:
        print(f"❌ Failed to get access token: {error}")
        return
    
    print(f"✅ Token obtained successfully\n")
    
    # Search for products
    print("🔍 Searching for Sentinel-2 products...")
    products, error = search_products(
        access_token, 
        platform='Sentinel-2',
        start_date='2015-12-19',
        end_date='2015-12-29',
        limit=10
    )
    
    if error:
        print(f"❌ Search failed: {error}")
        
        # Try alternative search with recent data
        print("\n🔄 Trying alternative search (recent Sentinel-2 data)...")
        recent_start = (datetime.now().replace(day=1) - pd.DateOffset(months=1)).strftime('%Y-%m-%d')
        recent_end = datetime.now().strftime('%Y-%m-%d')
        
        products, error = search_products(
            access_token,
            platform='Sentinel-2',
            start_date=recent_start,
            end_date=recent_end,
            limit=5
        )
        
        if error:
            print(f"❌ Alternative search also failed: {error}")
            print("\n🆘 This suggests account permission issues.")
            print("Please contact help-login@dataspace.copernicus.eu")
            return
    
    # Process and display results
    if products:
        df = process_products(products)
        
        print("\n🎉 SUCCESS: Direct API access is working!")
        print("\n📈 Statistics:")
        print(f"- Total products found: {len(products)}")
        if df is not None and 'size_mb' in df.columns:
            total_size_gb = df['size_mb'].sum() / 1024
            print(f"- Total size: {total_size_gb:.2f} GB")
        
    else:
        print("ℹ️  No products found for the specified criteria")
        print("\nTry:")
        print("1. Expanding the date range")
        print("2. Using different platforms (Sentinel-1, Sentinel-3)")
        print("3. Checking recent data availability")

if __name__ == "__main__":
    main()
    
    print("\n" + "="*60)
    print("📚 COMPARISON: SentinelSat vs Direct API")
    print("="*60)
    print("❌ SentinelSat: Getting 403 errors (compatibility issues)")
    print("✅ Direct API: Working with proper authentication")
    print("\n💡 RECOMMENDATION:")
    print("Use direct API calls until SentinelSat is updated for the new Copernicus Dataspace")
    print("\n📞 Support: help-login@dataspace.copernicus.eu")