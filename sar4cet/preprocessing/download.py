import os
import datetime
import requests
from sentinelsat import SentinelAPI
import geopandas as gpd
from shapely.geometry import box

def get_access_token(username, password):
    """
    Get OAuth2 access token for Copernicus Dataspace API.
    
    Parameters
    ----------
    username : str
        Copernicus Dataspace username
    password : str
        Copernicus Dataspace password
        
    Returns
    -------
    str
        Access token for API authentication
        
    Raises
    ------
    Exception
        If token creation fails
    """
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    
    try:
        response = requests.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data=data,
            timeout=30
        )
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

def search_sentinel1(aoi, start_date, end_date, polarization='VV VH', product_type='GRD'):
    """
    Search for Sentinel-1 data based on area of interest and time period.
    
    Uses the new Copernicus Dataspace API (https://dataspace.copernicus.eu/)
    which replaced the old SciHub service. This function now uses OAuth2 
    access tokens for authentication.
    
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
        Dictionary of search results
        
    Notes
    -----
    Requires registration at https://dataspace.copernicus.eu/ and setting
    COPERNICUS_USER and COPERNICUS_PASSWORD environment variables.
    The function will automatically obtain an OAuth2 access token.
    """
    # Convert AOI to WKT format
    footprint = box(aoi[0], aoi[1], aoi[2], aoi[3])
    footprint_wkt = footprint.wkt
    
    # Get credentials from environment variables
    user = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    if not user or not password:
        raise ValueError(
            "Please set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables.\n"
            "Register at https://dataspace.copernicus.eu/ to get credentials for the new Copernicus Dataspace.\n"
            "\n"
            "To set environment variables:\n"
            "export COPERNICUS_USER='your_username'\n"
            "export COPERNICUS_PASSWORD='your_password'"
        )
    
    try:
        # Get OAuth2 access token
        access_token = get_access_token(user, password)
        
        # Create SentinelAPI instance with access token
        # Note: For the new Dataspace API, we pass the token as password and use a dummy user
        api = SentinelAPI('token', access_token, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
        
        # Convert dates to datetime objects
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        # Search for Sentinel-1 data
        products = api.query(
            footprint_wkt,
            date=(start_date, end_date),
            platformname='Sentinel-1',
            producttype=product_type,
            polarisationmode=polarization
        )
        
        print(f"Found {len(products)} Sentinel-1 scenes")
        return products
        
    except Exception as e:
        print(f"Error during search: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify your credentials by logging into https://dataspace.copernicus.eu/")
        print("2. Ensure your account is activated (check your email for activation link)")
        print("3. Try setting your environment variables again")
        print("4. If the issue persists, try resetting your password on the website")
        raise

def download_sentinel1(aoi, start_date, end_date, download_dir='data', **kwargs):
    """
    Download Sentinel-1 data based on area of interest and time period.
    
    Uses the new Copernicus Dataspace API with OAuth2 authentication for downloading.
    
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
    The function will automatically obtain an OAuth2 access token for downloads.
    """
    # Search for Sentinel-1 data
    products = search_sentinel1(aoi, start_date, end_date, **kwargs)
    
    if not products:
        print("No products found")
        return []
    
    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    
    # Get credentials and access token
    user = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    try:
        # Get OAuth2 access token
        access_token = get_access_token(user, password)
        
        # Create SentinelAPI instance with access token
        api = SentinelAPI('token', access_token, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
        
        # Download products
        print(f"Downloading {len(products)} products to {download_dir}...")
        downloaded_files = []
        
        for product_id, product_info in products.items():
            try:
                # Download the product
                download_path = api.download(product_id, directory_path=download_dir)
                downloaded_files.append(download_path)
                print(f"Downloaded {product_info['title']}")
            except Exception as e:
                print(f"Error downloading {product_info['title']}: {e}")
                # If download fails due to authentication, try to get a new token
                if "401" in str(e) or "403" in str(e):
                    print("Authentication error detected. Trying to refresh access token...")
                    try:
                        access_token = get_access_token(user, password)
                        api = SentinelAPI('token', access_token, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
                        download_path = api.download(product_id, directory_path=download_dir)
                        downloaded_files.append(download_path)
                        print(f"Downloaded {product_info['title']} after token refresh")
                    except Exception as retry_error:
                        print(f"Failed to download {product_info['title']} even after token refresh: {retry_error}")
        
        return downloaded_files
        
    except Exception as e:
        print(f"Error during download: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify your credentials by logging into https://dataspace.copernicus.eu/")
        print("2. Ensure your account is activated (check your email for activation link)")
        print("3. Try setting your environment variables again")
        print("4. If the issue persists, try resetting your password on the website")
        raise