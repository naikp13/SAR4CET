#!/usr/bin/env python3
"""
Simple Copernicus Dataspace API Authentication Test
Based on the official documentation and community examples
"""

import os
import requests

def test_copernicus_auth():
    """Test authentication with Copernicus Dataspace API"""
    
    # Get credentials from environment
    username = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ Please set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables")
        return False
    
    print(f"🔍 Testing authentication for user: {username}")
    
    # Token endpoint
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    
    # Authentication data
    data = {
        'client_id': 'cdse-public',
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    try:
        # Request token
        print("📡 Requesting access token...")
        response = requests.post(token_url, data=data, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                print("✅ Successfully obtained access token!")
                print(f"Token type: {token_data.get('token_type', 'Bearer')}")
                print(f"Expires in: {token_data.get('expires_in', 'Unknown')} seconds")
                
                # Test a simple API call
                print("\n🧪 Testing API call...")
                headers = {'Authorization': f'Bearer {access_token}'}
                
                # Try a simple search query
                search_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$top=1"
                api_response = requests.get(search_url, headers=headers, timeout=30)
                
                if api_response.status_code == 200:
                    print("✅ API call successful!")
                    print("🎉 Authentication is working correctly!")
                    return True
                else:
                    print(f"❌ API call failed: {api_response.status_code}")
                    print(f"Response: {api_response.text[:200]}...")
                    return False
            else:
                print("❌ No access token in response")
                print(f"Response: {response.text}")
                return False
        else:
            print(f"❌ Token request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 401:
                print("\n🔍 Troubleshooting 401 Unauthorized:")
                print("1. Verify your username and password are correct")
                print("2. Try logging into https://dataspace.copernicus.eu/ to verify your account")
                print("3. Check if your account is activated (check your email)")
                print("4. Ensure you accepted the terms and conditions")
            
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🛰️  Copernicus Dataspace API - Simple Authentication Test\n")
    
    success = test_copernicus_auth()
    
    if success:
        print("\n🎯 Result: Authentication successful!")
        print("Your SAR4CET package should now work with the Copernicus Dataspace API.")
    else:
        print("\n❌ Result: Authentication failed.")
        print("Please check the troubleshooting steps above.")