import os
import datetime
from sentinelsat import SentinelAPI
import geopandas as gpd
from shapely.geometry import box

def search_sentinel1(aoi, start_date, end_date, polarization='VV VH', product_type='GRD'):
    """
    Search for Sentinel-1 data based on area of interest and time period.
    
    Uses the new Copernicus Dataspace API (https://dataspace.copernicus.eu/)
    which replaced the old SciHub service.
    
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
    """
    # Convert AOI to WKT format
    footprint = box(aoi[0], aoi[1], aoi[2], aoi[3])
    footprint_wkt = footprint.wkt
    
    # Connect to Copernicus Dataspace
    # Note: Requires user to set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables
    user = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    
    if not user or not password:
        raise ValueError(
            "Please set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables.\n"
            "Register at https://dataspace.copernicus.eu/ to get credentials for the new Copernicus Dataspace."
        )
    
    # Use the new Copernicus Dataspace API endpoint
    api = SentinelAPI(user, password, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
    
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

def download_sentinel1(aoi, start_date, end_date, download_dir='data', **kwargs):
    """
    Download Sentinel-1 data based on area of interest and time period.
    
    Uses the new Copernicus Dataspace API for downloading.
    
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
    """
    # Search for Sentinel-1 data
    products = search_sentinel1(aoi, start_date, end_date, **kwargs)
    
    if not products:
        print("No products found")
        return []
    
    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    
    # Connect to Copernicus Dataspace
    user = os.environ.get('COPERNICUS_USER')
    password = os.environ.get('COPERNICUS_PASSWORD')
    api = SentinelAPI(user, password, 'https://catalogue.dataspace.copernicus.eu/odata/v1')
    
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
    
    return downloaded_files