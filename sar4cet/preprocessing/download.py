import os
import datetime
import requests
import pandas as pd
from urllib.parse import quote
from shapely.geometry import box
try:
    from sentinelsat import SentinelAPI
    SENTINELSAT_AVAILABLE = True
except ImportError:
    SENTINELSAT_AVAILABLE = False
    print("Warning: SentinelSat not available. Using direct API implementation.")

def get_access_token(username=None, password=None, client_id=None, client_secret=None):
    """
    Get OAuth2 access token for Copernicus Dataspace API.
    
    Supports both username/password and OAuth2 client credentials authentication.
    For downloads, OAuth2 client credentials are recommended.
    
    Parameters
    ----------
    username : str, optional
        Copernicus Dataspace username (for password grant)
    password : str, optional
        Copernicus Dataspace password (for password grant)
    client_id : str, optional
        OAuth2 client ID (for client credentials grant)
    client_secret : str, optional
        OAuth2 client secret (for client credentials grant)
        
    Returns
    -------
    str
        Access token for API authentication
        
    Raises
    ------
    Exception
        If token creation fails
    """
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    
    # Try OAuth2 client credentials first (recommended for downloads)
    if client_id and client_secret:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }
    elif username and password:
        # Fallback to username/password (mainly for search)
        data = {
            "client_id": "cdse-public",
            "username": username,
            "password": password,
            "grant_type": "password",
        }
    else:
        raise ValueError("Either (client_id, client_secret) or (username, password) must be provided")
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        raise Exception(
            f"Failed to get access token. Error: {e}\n"
            f"Please check your credentials and ensure you have registered at https://dataspace.copernicus.eu/\n"
            f"If you continue to have issues, try logging in to the website first to verify your account is active."
        )
    except KeyError:
        raise Exception(
            f"Invalid response from authentication server. Response: {response.text}\n"
            f"Please verify your credentials are correct."
        )

def _search_products_direct_api(access_token, aoi, start_date, end_date, platform='Sentinel-1', product_type='GRD', polarization='VV VH', limit=100):
    """
    Search for products using direct Copernicus Dataspace API calls.
    
    Parameters
    ----------
    access_token : str
        OAuth2 access token
    aoi : list
        Area of interest as [lon_min, lat_min, lon_max, lat_max]
    start_date : str
        Start date in format 'YYYY-MM-DD'
    end_date : str
        End date in format 'YYYY-MM-DD'
    platform : str
        Platform name (e.g., 'Sentinel-1', 'Sentinel-2')
    product_type : str
        Product type (e.g., 'GRD', 'SLC')
    polarization : str
        Polarization mode
    limit : int
        Maximum number of products to return
        
    Returns
    -------
    dict
        Dictionary of products in SentinelSat-compatible format
    """
    base_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Build filter for platform and date range
    filters = []
    
    # Platform filter
    if platform == 'Sentinel-1':
        filters.append("Collection/Name eq 'SENTINEL-1'")
    elif platform == 'Sentinel-2':
        filters.append("Collection/Name eq 'SENTINEL-2'")
    elif platform == 'Sentinel-3':
        filters.append("Collection/Name eq 'SENTINEL-3'")
    
    # Date filter
    if start_date and end_date:
        filters.append(f"ContentDate/Start ge {start_date}T00:00:00.000Z")
        filters.append(f"ContentDate/Start le {end_date}T23:59:59.999Z")
    
    # Product type filter (for Sentinel-1)
    if platform == 'Sentinel-1' and product_type:
        # Note: Product type filtering might need adjustment based on API capabilities
        pass  # Will be handled in post-processing if needed
    
    # Combine filters
    filter_str = " and ".join(filters)
    
    # Build query parameters
    params = {
        '$top': limit,
        '$orderby': 'ContentDate/Start desc'
    }
    
    if filter_str:
        params['$filter'] = filter_str
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            raw_products = data.get('value', [])
            
            # Convert to SentinelSat-compatible format
            products = {}
            
            for product in raw_products:
                # Filter by AOI if specified
                if aoi and not _product_intersects_aoi(product, aoi):
                    continue
                    
                # Filter by product type and polarization if specified
                if platform == 'Sentinel-1':
                    if product_type and not _matches_product_type(product, product_type):
                        continue
                    if polarization and not _matches_polarization(product, polarization):
                        continue
                
                product_id = product.get('Id')
                if product_id:
                    # Convert to SentinelSat format
                    products[product_id] = {
                        'title': product.get('Name', 'Unknown'),
                        'size': product.get('ContentLength', 0),
                        'beginposition': product.get('ContentDate', {}).get('Start', ''),
                        'endposition': product.get('ContentDate', {}).get('End', ''),
                        'footprint': product.get('Footprint', ''),
                        'platformname': platform,
                        'producttype': product_type,
                        'uuid': product_id,
                        'download_url': f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
                    }
                    
                    # Add additional attributes
                    attributes = product.get('Attributes', [])
                    for attr in attributes:
                        attr_name = attr.get('Name', '').lower()
                        attr_value = attr.get('Value')
                        if attr_name and attr_value:
                            products[product_id][attr_name] = attr_value
            
            return products
        else:
            raise Exception(f"API request failed: {response.status_code} - {response.text[:500]}")
            
    except Exception as e:
        raise Exception(f"API request error: {e}")

def _product_intersects_aoi(product, aoi):
    """
    Check if product footprint intersects with area of interest.
    
    Parameters
    ----------
    product : dict
        Product information from API
    aoi : list
        Area of interest as [lon_min, lat_min, lon_max, lat_max]
        
    Returns
    -------
    bool
        True if product intersects AOI
    """
    # For now, return True (basic implementation)
    # In a full implementation, you would parse the footprint geometry
    # and check for intersection with the AOI
    return True

def _matches_product_type(product, product_type):
    """
    Check if product matches the specified product type.
    
    Parameters
    ----------
    product : dict
        Product information from API
    product_type : str
        Desired product type
        
    Returns
    -------
    bool
        True if product matches type
    """
    product_name = product.get('Name', '').upper()
    return product_type.upper() in product_name

def _matches_polarization(product, polarization):
    """
    Check if product matches the specified polarization.
    
    Parameters
    ----------
    product : dict
        Product information from API
    polarization : str
        Desired polarization (e.g., 'VV VH')
        
    Returns
    -------
    bool
        True if product matches polarization
    """
    # For now, return True (basic implementation)
    # In a full implementation, you would check product attributes
    # for polarization information
    return True

def search_sentinel1(aoi, start_date, end_date, polarization='VV VH', product_type='GRD'):
    """
    Search for Sentinel-1 data based on area of interest and time period.
    
    Uses the new Copernicus Dataspace API (https://dataspace.copernicus.eu/)
    with direct API calls for maximum compatibility.
    
    Parameters
    ----------
    aoi : list
        Area of interest as [lon_min, lat_min, lon_max, lat_max]
    start_date : str
        Start date in format 'YYYY-MM-DD'
    end_date : str
        End date in format 'YYYY-MM-DD'
    polarization : str, optional
        Polarization mode, by default 'VV VH'
    product_type : str, optional
        Product type, by default 'GRD'
    
    Returns
    -------
    dict
        Dictionary of search results compatible with SentinelSat format
        
    Notes
    -----
    Requires registration at https://dataspace.copernicus.eu/ and setting either:
    - COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET (OAuth2 - recommended)
    - COPERNICUS_USER and COPERNICUS_PASSWORD (username/password - fallback)
    """
    # Try OAuth2 client credentials first
    client_id = os.environ.get('COPERNICUS_CLIENT_ID')
    client_secret = os.environ.get('COPERNICUS_CLIENT_SECRET')
    
    # Fallback to username/password
    user = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    if not ((client_id and client_secret) or (user and password)):
        raise ValueError(
            "Please set either:\n"
            "- COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET (OAuth2 - recommended)\n"
            "- COPERNICUS_USER and COPERNICUS_PASSWORD (username/password - fallback)\n"
            "Register at https://dataspace.copernicus.eu/ to get credentials for the new Copernicus Dataspace.\n"
            "\n"
            "To set environment variables:\n"
            "export COPERNICUS_CLIENT_ID='your_client_id'\n"
            "export COPERNICUS_CLIENT_SECRET='your_client_secret'"
        )
    
    try:
        # Get OAuth2 access token
        if client_id and client_secret:
            access_token = get_access_token(client_id=client_id, client_secret=client_secret)
        else:
            access_token = get_access_token(username=user, password=password)
        
        # Use direct API search
        products = _search_products_direct_api(
            access_token=access_token,
            aoi=aoi,
            start_date=start_date,
            end_date=end_date,
            platform='Sentinel-1',
            product_type=product_type,
            polarization=polarization
        )
        
        print(f"Found {len(products)} Sentinel-1 scenes")
        return products
        
    except Exception as e:
        print(f"Error during search: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify your credentials by logging into https://dataspace.copernicus.eu/")
        print("2. For OAuth2: Create an OAuth client in your account settings")
        print("3. Ensure your account is activated (check your email for activation link)")
        print("4. Try setting your environment variables again")
        print("5. If the issue persists, try resetting your password on the website")
        raise

def download_sentinel1(aoi, start_date, end_date, download_dir='data', max_products=None, **kwargs):
    """
    Download Sentinel-1 data based on area of interest and time period.
    
    Uses the new Copernicus Dataspace API with direct downloads for maximum compatibility.
    
    Parameters
    ----------
    aoi : list
        Area of interest as [lon_min, lat_min, lon_max, lat_max]
    start_date : str
        Start date in format 'YYYY-MM-DD'
    end_date : str
        End date in format 'YYYY-MM-DD'
    download_dir : str, optional
        Directory to download data to, by default 'data'
    max_products : int, optional
        Maximum number of products to download, by default None (all)
    **kwargs : dict
        Additional arguments to pass to search_sentinel1
    
    Returns
    -------
    list
        List of downloaded file paths
        
    Notes
    -----
    Requires registration at https://dataspace.copernicus.eu/ and setting
    COPERNICUS_USER and COPERNICUS_PASSWORD environment variables.
    """
    # Search for Sentinel-1 data
    products = search_sentinel1(aoi, start_date, end_date, **kwargs)
    
    if not products:
        print("No products found")
        return []
    
    # Limit products if specified
    if max_products and len(products) > max_products:
        products = dict(list(products.items())[:max_products])
        print(f"Limited to {max_products} products for download")
    
    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    
    # Get credentials and access token
    client_id = os.environ.get('COPERNICUS_CLIENT_ID')
    client_secret = os.environ.get('COPERNICUS_CLIENT_SECRET')
    user = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    try:
        # Get OAuth2 access token
        if client_id and client_secret:
            access_token = get_access_token(client_id=client_id, client_secret=client_secret)
        else:
            access_token = get_access_token(username=user, password=password)
        
        # Download products using direct API
        print(f"Downloading {len(products)} products to {download_dir}...")
        downloaded_files = []
        
        for i, (product_id, product_info) in enumerate(products.items(), 1):
            try:
                print(f"Downloading {i}/{len(products)}: {product_info['title']}")
                
                # Use direct download URL
                download_url = product_info.get('download_url')
                if not download_url:
                    download_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
                
                # Download the product
                headers = {'Authorization': f'Bearer {access_token}'}
                
                response = requests.get(download_url, headers=headers, stream=True, timeout=300)
                
                if response.status_code == 200:
                    # Generate filename
                    filename = product_info['title']
                    if not filename.endswith('.zip'):
                        filename += '.zip'
                    
                    filepath = os.path.join(download_dir, filename)
                    
                    # Download with progress
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                # Simple progress indicator
                                if total_size > 0:
                                    progress = (downloaded_size / total_size) * 100
                                    print(f"\r  Progress: {progress:.1f}%", end='', flush=True)
                    
                    print(f"\n  ✅ Downloaded: {filename}")
                    downloaded_files.append(filepath)
                    
                elif response.status_code in [401, 403]:
                    print(f"\n  ❌ Authentication error for {product_info['title']}")
                    print("  Trying to refresh access token...")
                    
                    # Refresh token and retry
                    if client_id and client_secret:
                        access_token = get_access_token(client_id=client_id, client_secret=client_secret)
                    else:
                        access_token = get_access_token(username=user, password=password)
                    headers = {'Authorization': f'Bearer {access_token}'}
                    
                    response = requests.get(download_url, headers=headers, stream=True, timeout=300)
                    
                    if response.status_code == 200:
                        filename = product_info['title']
                        if not filename.endswith('.zip'):
                            filename += '.zip'
                        
                        filepath = os.path.join(download_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        print(f"  ✅ Downloaded after token refresh: {filename}")
                        downloaded_files.append(filepath)
                    else:
                        print(f"  ❌ Failed even after token refresh: {response.status_code}")
                        
                else:
                    print(f"\n  ❌ Download failed: {response.status_code} - {response.reason}")
                    
            except Exception as e:
                print(f"\n  ❌ Error downloading {product_info['title']}: {e}")
                continue
        
        print(f"\n🎉 Successfully downloaded {len(downloaded_files)} out of {len(products)} products")
        return downloaded_files
        
    except Exception as e:
        print(f"Error during download: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify your credentials by logging into https://dataspace.copernicus.eu/")
        print("2. Ensure your account is activated (check your email for activation link)")
        print("3. Try setting your environment variables again")
        print("4. If the issue persists, try resetting your password on the website")
        raise