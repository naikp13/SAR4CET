#!/usr/bin/env python3
"""
Test script to check API permissions and access levels
for Copernicus Dataspace account.
"""

import os
import requests
import json
from datetime import datetime

def get_access_token():
    """Get OAuth2 access token."""
    username = os.getenv('COPERNICUS_USER')
    password = os.getenv('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ Environment variables not set")
        return None
    
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
            return response.json().get('access_token')
        else:
            print(f"❌ Token request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Token request error: {e}")
        return None

def test_api_endpoints(access_token):
    """Test various API endpoints to check permissions."""
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Test endpoints with different permission levels
    test_endpoints = [
        {
            'name': 'Basic Catalogue Info',
            'url': 'https://catalogue.dataspace.copernicus.eu/odata/v1/$metadata',
            'description': 'Basic metadata (should work for all users)'
        },
        {
            'name': 'Product Count',
            'url': 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products/$count',
            'description': 'Total product count (basic access)'
        },
        {
            'name': 'Collections List',
            'url': 'https://catalogue.dataspace.copernicus.eu/odata/v1/Collections',
            'description': 'Available collections (basic access)'
        },
        {
            'name': 'Single Product',
            'url': 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$top=1',
            'description': 'Single product (requires search permissions)'
        },
        {
            'name': 'Sentinel-2 Search',
            'url': 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq \'SENTINEL-2\'&$top=1',
            'description': 'Filtered search (requires full access)'
        }
    ]
    
    print("\n🔍 Testing API Endpoints...")
    print("=" * 50)
    
    results = []
    
    for endpoint in test_endpoints:
        print(f"\n📡 Testing: {endpoint['name']}")
        print(f"Description: {endpoint['description']}")
        
        try:
            response = requests.get(endpoint['url'], headers=headers, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ SUCCESS: {response.status_code}")
                
                # Try to parse response
                try:
                    if 'json' in response.headers.get('content-type', '').lower():
                        data = response.json()
                        if '@odata.count' in data:
                            print(f"   Count: {data['@odata.count']}")
                        elif 'value' in data:
                            print(f"   Items: {len(data['value'])}")
                    else:
                        print(f"   Response length: {len(response.text)} chars")
                except:
                    print(f"   Response length: {len(response.text)} chars")
                    
                results.append((endpoint['name'], 'SUCCESS', response.status_code))
                
            else:
                print(f"❌ FAILED: {response.status_code}")
                print(f"   Error: {response.text[:200]}...")
                results.append((endpoint['name'], 'FAILED', response.status_code))
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((endpoint['name'], 'ERROR', str(e)))
    
    return results

def analyze_permissions(results):
    """Analyze test results to determine account permissions."""
    
    print("\n📊 PERMISSION ANALYSIS")
    print("=" * 50)
    
    success_count = sum(1 for _, status, _ in results if status == 'SUCCESS')
    total_tests = len(results)
    
    print(f"Successful tests: {success_count}/{total_tests}")
    
    if success_count == 0:
        print("\n🚨 NO ACCESS: Account has no API permissions")
        print("Possible causes:")
        print("- Account not fully activated")
        print("- Missing terms acceptance")
        print("- Account suspended")
        
    elif success_count <= 2:
        print("\n⚠️  LIMITED ACCESS: Basic metadata only")
        print("Your account can access basic information but not search/download")
        print("This suggests a partially activated account")
        
    elif success_count <= 4:
        print("\n✅ GOOD ACCESS: Most features available")
        print("Your account has good access but may have some limitations")
        
    else:
        print("\n🎉 FULL ACCESS: All features available")
        print("Your account is fully functional!")
    
    print("\n📋 DETAILED RESULTS:")
    for name, status, code in results:
        status_icon = "✅" if status == 'SUCCESS' else "❌"
        print(f"{status_icon} {name}: {status} ({code})")

def main():
    print("=== Copernicus Dataspace API Permission Test ===")
    print(f"Timestamp: {datetime.now()}\n")
    
    # Get credentials
    username = os.getenv('COPERNICUS_USER')
    password = os.getenv('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ ERROR: Environment variables not set")
        print("Please set COPERNICUS_USER and COPERNICUS_PASSWORD")
        return
    
    print(f"✓ Username: {username}")
    print(f"✓ Password: {'*' * len(password)}")
    
    # Get access token
    print("\n🔑 Getting access token...")
    access_token = get_access_token()
    
    if not access_token:
        print("❌ Failed to get access token")
        return
    
    print(f"✅ Token obtained: {access_token[:20]}...")
    
    # Test API endpoints
    results = test_api_endpoints(access_token)
    
    # Analyze results
    analyze_permissions(results)
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. If you have limited access, wait 24 hours for full activation")
    print("2. Log into https://dataspace.copernicus.eu/ and check for pending actions")
    print("3. Accept any outstanding Terms & Conditions")
    print("4. Contact help-login@dataspace.copernicus.eu if issues persist")

if __name__ == "__main__":
    main()