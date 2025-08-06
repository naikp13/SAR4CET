# OpenEO Migration Guide

SAR4CET has been updated to use the **openEO API** for accessing Sentinel-1 data from the Copernicus Dataspace. This provides improved reliability, performance, and standardized access to Earth observation data.

## What Changed

### 🔄 API Migration
- **Before**: Direct Copernicus Dataspace API
- **After**: OpenEO API for Copernicus Dataspace

### 🔧 New Functions
- `search_sentinel1_openeo()` - Search for Sentinel-1 data using openEO
- `download_sentinel1_openeo()` - Download Sentinel-1 data using openEO
- `process_sentinel1_openeo()` - Process data with custom openEO workflows
- `connect_openeo()` - Connect to openEO backend
- `list_openeo_collections()` - List available data collections
- `describe_openeo_collection()` - Get collection metadata

### 🔄 Backward Compatibility
The old functions still work as aliases:
- `search_sentinel1()` → calls `search_sentinel1_openeo()`
- `download_sentinel1()` → calls `download_sentinel1_openeo()`

## Installation

### Requirements
Add openEO to your dependencies:

```bash
pip install openeo>=0.22.0
```

Or update your `requirements.txt`:
```
openeo>=0.22.0
sentinelsat>=1.2.1  # Optional, for legacy compatibility
```

## Authentication Setup

### Option 1: OAuth2 Client Credentials (Recommended)

1. **Register** at https://dataspace.copernicus.eu/ (free)
2. **Login** to your account
3. **Navigate** to User Settings → OAuth clients
4. **Create** a new OAuth client
5. **Set environment variables**:
   ```bash
   export COPERNICUS_CLIENT_ID="your_client_id"
   export COPERNICUS_CLIENT_SECRET="your_client_secret"
   ```

### Option 2: Interactive Authentication

If no credentials are set, the system will open a browser for interactive login.

## Usage Examples

### Basic Search and Download

```python
from sar4cet.preprocessing import search_sentinel1_openeo, download_sentinel1_openeo

# Define area of interest (bounding box)
aoi = [-122.5, 37.5, -122.0, 38.0]  # [lon_min, lat_min, lon_max, lat_max]

# Search for data
results = search_sentinel1_openeo(
    aoi=aoi,
    start_date="2023-01-01",
    end_date="2023-01-31",
    polarization="VV,VH",
    product_type="GRD"
)

print(f"Found {len(results)} products")

# Download data
files = download_sentinel1_openeo(
    aoi=aoi,
    start_date="2023-01-01",
    end_date="2023-01-31",
    download_dir="data"
)
```

### Advanced Processing

```python
from sar4cet.preprocessing import process_sentinel1_openeo

# Process data with custom options
processed_data = process_sentinel1_openeo(
    aoi=aoi,
    start_date="2023-01-01",
    end_date="2023-01-31",
    processing_options={
        "radiometric_terrain_correction": True,
        "speckle_filter": "lee",
        "output_format": "GTiff"
    }
)
```

### Connection Management

```python
from sar4cet.preprocessing import connect_openeo, list_openeo_collections

# Connect to openEO
connection = connect_openeo()
print(f"Connected to: {connection.url}")

# List available collections
collections = list_openeo_collections()
print(f"Available collections: {len(collections)}")
```

## Migration Checklist

### For Existing Code
- [ ] Update `requirements.txt` to include `openeo>=0.22.0`
- [ ] Set up OAuth2 credentials (recommended)
- [ ] Test existing code (should work with backward compatibility)
- [ ] Consider migrating to new `*_openeo` functions for better performance

### For New Projects
- [ ] Use `search_sentinel1_openeo()` and `download_sentinel1_openeo()` directly
- [ ] Set up OAuth2 client credentials
- [ ] Explore advanced processing options with `process_sentinel1_openeo()`

## Testing

Run the integration test to verify everything works:

```bash
python examples/test_openeo_integration.py
```

## Benefits of OpenEO

### 🚀 Performance
- Server-side processing reduces data transfer
- Optimized for large-scale analysis
- Parallel processing capabilities

### 🔒 Reliability
- Standardized API across multiple data providers
- Better error handling and retry mechanisms
- Consistent authentication

### 🛠️ Flexibility
- Custom processing workflows
- Multiple output formats
- Advanced filtering and preprocessing

### 🌍 Standardization
- OpenEO is an open standard for Earth observation data
- Works with multiple backends (Copernicus, Google Earth Engine, etc.)
- Future-proof architecture

## Troubleshooting

### Common Issues

1. **Import Error**: `ModuleNotFoundError: No module named 'openeo'`
   - **Solution**: Install openEO with `pip install openeo>=0.22.0`

2. **Authentication Error**: `401 Unauthorized`
   - **Solution**: Check your OAuth2 credentials or use interactive authentication

3. **Connection Error**: `Failed to connect to openEO backend`
   - **Solution**: Check internet connection and firewall settings

4. **No Data Found**: Empty search results
   - **Solution**: Verify AOI coordinates and date range

### Getting Help

- **SAR4CET Issues**: https://github.com/your-repo/SAR4CET/issues
- **OpenEO Documentation**: https://openeo.org/documentation/
- **Copernicus Dataspace**: https://documentation.dataspace.copernicus.eu/

## Resources

- [OpenEO API Documentation](https://openeo.org/documentation/)
- [Copernicus Dataspace OpenEO](https://documentation.dataspace.copernicus.eu/APIs/openEO/)
- [OpenEO Client Credentials Guide](https://documentation.dataspace.copernicus.eu/APIs/openEO/authentication/client_credentials.html)
- [OpenEO Tutorial Video](https://www.youtube.com/watch?v=UL6om8Jxh9w&t=146s&ab_channel=CopernicusDataSpaceEcosystem)