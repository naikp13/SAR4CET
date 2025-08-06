import os
import datetime
import requests
import pandas as pd
from urllib.parse import quote
from shapely.geometry import box
try:
    import openeo
    OPENEO_AVAILABLE = True
except ImportError:
    OPENEO_AVAILABLE = False
    print("Warning: openEO not available. Please install with: pip install openeo")

try:
    from sentinelsat import SentinelAPI
    SENTINELSAT_AVAILABLE = True
except ImportError:
    SENTINELSAT_AVAILABLE = False
    print("Warning: SentinelSat not available. Using openEO implementation.")

def get_openeo_connection(client_id=None, client_secret=None):
    """
    Get authenticated openEO connection for Copernicus Dataspace.
    
    Parameters
    ----------
    client_id : str, optional
        OAuth2 client ID for service account authentication
    client_secret : str, optional
        OAuth2 client secret for service account authentication
        
    Returns
    -------
    openeo.Connection
        Authenticated openEO connection
        
    Raises
    ------
    Exception
        If connection or authentication fails
    """
    if not OPENEO_AVAILABLE:
        raise ImportError("openEO is required. Install with: pip install openeo")
    
    try:
        # Connect to Copernicus Dataspace openEO backend
        connection = openeo.connect("openeo.dataspace.copernicus.eu")
        
        if client_id and client_secret:
            # Use OAuth2 client credentials (recommended)
            connection.authenticate_oidc_client_credentials(
                client_id=client_id,
                client_secret=client_secret
            )
            print("✅ Authenticated with OAuth2 client credentials")
        else:
            # Interactive authentication fallback
            connection.authenticate_oidc()
            print("✅ Authenticated with interactive OIDC")
        
        return connection
        
    except Exception as e:
        raise Exception(
            f"Failed to connect to openEO backend. Error: {e}\n"
            f"Please check your credentials and ensure you have registered at https://dataspace.copernicus.eu/\n"
            f"For service accounts, create OAuth client credentials in your account settings."
        )

def search_sentinel1_openeo(aoi, start_date, end_date, polarization='VV,VH', product_type='GRD'):
    """
    Search for Sentinel-1 data using openEO API.
    
    Parameters
    ----------
    aoi : list
        Area of interest as [lon_min, lat_min, lon_max, lat_max]
    start_date : str
        Start date in format 'YYYY-MM-DD'
    end_date : str
        End date in format 'YYYY-MM-DD'
    polarization : str, optional
        Polarization mode, by default 'VV,VH'
    product_type : str, optional
        Product type, by default 'GRD'
    
    Returns
    -------
    dict
        Dictionary of search results with product information
        
    Notes
    -----
    Requires registration at https://dataspace.copernicus.eu/ and setting:
    - COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET (OAuth2 - recommended)
    Or using interactive authentication
    """
    # Get credentials
    client_id = os.environ.get('COPERNICUS_CLIENT_ID')
    client_secret = os.environ.get('COPERNICUS_CLIENT_SECRET')
    
    try:
        # Get openEO connection
        connection = get_openeo_connection(client_id=client_id, client_secret=client_secret)
        
        # Load Sentinel-1 collection
        if product_type.upper() == 'GRD':
            collection_id = "SENTINEL1_GRD"
        elif product_type.upper() == 'SLC':
            collection_id = "SENTINEL1_SLC"
        else:
            collection_id = "SENTINEL1_GRD"  # Default to GRD
        
        # Create spatial extent
        spatial_extent = {
            "west": aoi[0],
            "south": aoi[1], 
            "east": aoi[2],
            "north": aoi[3]
        }
        
        # Create temporal extent
        temporal_extent = [start_date, end_date]
        
        # Load the collection
        datacube = connection.load_collection(
            collection_id,
            spatial_extent=spatial_extent,
            temporal_extent=temporal_extent,
            bands=polarization.split(',') if polarization else None
        )
        
        # Get collection metadata for search results
        collection_info = connection.describe_collection(collection_id)
        
        print(f"✅ Successfully created datacube for {collection_id}")
        print(f"   Spatial extent: {spatial_extent}")
        print(f"   Temporal extent: {temporal_extent}")
        print(f"   Polarization: {polarization}")
        
        # Return datacube and metadata
        return {
            'datacube': datacube,
            'collection_info': collection_info,
            'spatial_extent': spatial_extent,
            'temporal_extent': temporal_extent,
            'polarization': polarization,
            'product_type': product_type
        }
        
    except Exception as e:
        print(f"Error during search: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify your credentials by logging into https://dataspace.copernicus.eu/")
        print("2. For OAuth2: Create an OAuth client in User Settings > OAuth clients")
        print("3. Ensure your account is activated (check your email for activation link)")
        print("4. Install openEO: pip install openeo")
        print("5. Try setting your environment variables:")
        print("   export COPERNICUS_CLIENT_ID='your_client_id'")
        print("   export COPERNICUS_CLIENT_SECRET='your_client_secret'")
        raise

def download_sentinel1_openeo(aoi, start_date, end_date, download_dir='data', output_format='GTiff', **kwargs):
    """
    Download Sentinel-1 data using openEO API.
    
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
    output_format : str, optional
        Output format, by default 'GTiff'
    **kwargs : dict
        Additional arguments to pass to search_sentinel1_openeo
    
    Returns
    -------
    list
        List of downloaded file paths
        
    Notes
    -----
    Requires registration at https://dataspace.copernicus.eu/ and setting
    COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET environment variables.
    """
    # Search for Sentinel-1 data
    search_result = search_sentinel1_openeo(aoi, start_date, end_date, **kwargs)
    
    if not search_result:
        print("No data found")
        return []
    
    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        datacube = search_result['datacube']
        
        # Generate output filename
        start_clean = start_date.replace('-', '')
        end_clean = end_date.replace('-', '')
        aoi_str = f"{aoi[0]:.2f}_{aoi[1]:.2f}_{aoi[2]:.2f}_{aoi[3]:.2f}"
        filename = f"sentinel1_{search_result['product_type']}_{start_clean}_{end_clean}_{aoi_str}"
        
        if output_format.upper() == 'GTIFF':
            filename += '.tif'
        elif output_format.upper() == 'NETCDF':
            filename += '.nc'
        else:
            filename += '.tif'  # Default to GeoTIFF
        
        filepath = os.path.join(download_dir, filename)
        
        print(f"Downloading Sentinel-1 data to {filepath}...")
        
        # Download the data
        datacube.download(filepath, format=output_format)
        
        print(f"✅ Successfully downloaded: {filename}")
        return [filepath]
        
    except Exception as e:
        print(f"Error during download: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify your credentials by logging into https://dataspace.copernicus.eu/")
        print("2. Ensure your account is activated and has sufficient quota")
        print("3. Try reducing the spatial or temporal extent")
        print("4. Check if the requested data is available for your area and time period")
        raise

def process_sentinel1_openeo(aoi, start_date, end_date, processing_options=None, download_dir='data', **kwargs):
    """
    Process Sentinel-1 data using openEO with custom processing options.
    
    Parameters
    ----------
    aoi : list
        Area of interest as [lon_min, lat_min, lon_max, lat_max]
    start_date : str
        Start date in format 'YYYY-MM-DD'
    end_date : str
        End date in format 'YYYY-MM-DD'
    processing_options : dict, optional
        Processing options like temporal reduction, filtering, etc.
    download_dir : str, optional
        Directory to download processed data to, by default 'data'
    **kwargs : dict
        Additional arguments
    
    Returns
    -------
    list
        List of processed and downloaded file paths
    """
    # Search for Sentinel-1 data
    search_result = search_sentinel1_openeo(aoi, start_date, end_date, **kwargs)
    
    if not search_result:
        print("No data found")
        return []
    
    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        datacube = search_result['datacube']
        
        # Apply processing options if provided
        if processing_options:
            if processing_options.get('temporal_reduction'):
                # Apply temporal reduction (e.g., mean, median)
                reduction_method = processing_options['temporal_reduction']
                if reduction_method == 'mean':
                    datacube = datacube.mean_time()
                elif reduction_method == 'median':
                    datacube = datacube.median_time()
                elif reduction_method == 'max':
                    datacube = datacube.max_time()
                elif reduction_method == 'min':
                    datacube = datacube.min_time()
            
            if processing_options.get('apply_mask'):
                # Apply cloud mask or other masks
                pass  # Implementation depends on specific requirements
            
            if processing_options.get('resample_resolution'):
                # Resample to different resolution
                resolution = processing_options['resample_resolution']
                datacube = datacube.resample_spatial(resolution=resolution)
        
        # Generate output filename
        start_clean = start_date.replace('-', '')
        end_clean = end_date.replace('-', '')
        aoi_str = f"{aoi[0]:.2f}_{aoi[1]:.2f}_{aoi[2]:.2f}_{aoi[3]:.2f}"
        
        processing_suffix = ""
        if processing_options and processing_options.get('temporal_reduction'):
            processing_suffix = f"_{processing_options['temporal_reduction']}"
        
        filename = f"sentinel1_processed_{search_result['product_type']}_{start_clean}_{end_clean}_{aoi_str}{processing_suffix}.tif"
        filepath = os.path.join(download_dir, filename)
        
        print(f"Processing and downloading Sentinel-1 data to {filepath}...")
        
        # Download the processed data
        datacube.download(filepath, format="GTiff")
        
        print(f"✅ Successfully processed and downloaded: {filename}")
        return [filepath]
        
    except Exception as e:
        print(f"Error during processing: {e}")
        raise

# Legacy function aliases for backward compatibility
def search_sentinel1(aoi, start_date, end_date, polarization='VV,VH', product_type='GRD'):
    """
    Legacy function for backward compatibility.
    Now uses openEO API instead of direct Copernicus API.
    """
    print("ℹ️  Using openEO API for Sentinel-1 data access")
    return search_sentinel1_openeo(aoi, start_date, end_date, polarization, product_type)

def download_sentinel1(aoi, start_date, end_date, download_dir='data', max_products=None, **kwargs):
    """
    Legacy function for backward compatibility.
    Now uses openEO API instead of direct Copernicus API.
    """
    print("ℹ️  Using openEO API for Sentinel-1 data download")
    if max_products:
        print(f"⚠️  max_products parameter is not applicable with openEO API")
    
    return download_sentinel1_openeo(aoi, start_date, end_date, download_dir, **kwargs)

# Utility functions for openEO
def list_available_collections():
    """
    List available collections in the openEO backend.
    
    Returns
    -------
    list
        List of available collection IDs
    """
    if not OPENEO_AVAILABLE:
        raise ImportError("openEO is required. Install with: pip install openeo")
    
    client_id = os.environ.get('COPERNICUS_CLIENT_ID')
    client_secret = os.environ.get('COPERNICUS_CLIENT_SECRET')
    
    try:
        connection = get_openeo_connection(client_id=client_id, client_secret=client_secret)
        collections = connection.list_collections()
        
        print("Available collections:")
        for collection in collections:
            print(f"  - {collection['id']}: {collection.get('title', 'No title')}")
        
        return [col['id'] for col in collections]
        
    except Exception as e:
        print(f"Error listing collections: {e}")
        raise

def get_collection_info(collection_id):
    """
    Get detailed information about a specific collection.
    
    Parameters
    ----------
    collection_id : str
        Collection ID (e.g., 'SENTINEL1_GRD')
    
    Returns
    -------
    dict
        Collection metadata
    """
    if not OPENEO_AVAILABLE:
        raise ImportError("openEO is required. Install with: pip install openeo")
    
    client_id = os.environ.get('COPERNICUS_CLIENT_ID')
    client_secret = os.environ.get('COPERNICUS_CLIENT_SECRET')
    
    try:
        connection = get_openeo_connection(client_id=client_id, client_secret=client_secret)
        collection_info = connection.describe_collection(collection_id)
        
        print(f"Collection: {collection_id}")
        print(f"Title: {collection_info.get('title', 'No title')}")
        print(f"Description: {collection_info.get('description', 'No description')}")
        
        if 'extent' in collection_info:
            extent = collection_info['extent']
            if 'spatial' in extent:
                print(f"Spatial extent: {extent['spatial']}")
            if 'temporal' in extent:
                print(f"Temporal extent: {extent['temporal']}")
        
        return collection_info
        
    except Exception as e:
        print(f"Error getting collection info: {e}")
        raise