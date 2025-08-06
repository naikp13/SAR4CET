# SAR4CET - Synthetic Aperture Radar to support Clean Energy Transition 

SAR4CET is repository developed under the Plan4CET project (https://plan4cet.eu/) at the Insitute for Renewable Energy, EURAC Research. It provides is a toolkit for automated change detection using primarily Sentinel-1 SAR data and a scope of integration with other remote sensing modalities to improve the end product. This package provides tools and utilities to process Sentinel-1 data and detect changes in land cover, urban areas, natural disasters, and oil reservoirs.

<img src="https://raw.githubusercontent.com/naikp13/SAR4CET/master/plan4cet.png" alt="plan4cet" width="800"/>

## Features

- **openEO Integration**: Access Sentinel-1 SAR data through the standardized openEO API
- Radiometric Terrain Correction (RTC) for SAR data
- Change detection algorithms for multi-temporal SAR imagery
- Visualization tools for change detection results
- Support for various change detection applications:
  - Urban development monitoring
  - Deforestation detection
  - Flood mapping
  - Disaster assessment
- Oil reservoir monitoring capabilities:
  - Storage tank volume estimation and change detection
  - Traffic and logistics activity analysis
  - Operational anomaly detection
- **New**: Urban change detection notebook for New Delhi using openEO API

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/SAR4CET.git
cd SAR4CET

# Create a conda environment
conda create -n sar4cet python=3.9
conda activate sar4cet

# Install dependencies
pip install -r requirements.txt
```

## Authentication Setup

**Important:** SAR4CET now uses the openEO API for accessing Sentinel-1 data through Copernicus Dataspace.

### Setting up openEO Copernicus Dataspace Access

1. **Register for free** at: https://dataspace.copernicus.eu/
2. **Authentication Options**:
   
   **Option A: Interactive Authentication (Recommended for notebooks)**
   ```python
   import openeo
   conn = openeo.connect("openeo.dataspace.copernicus.eu").authenticate_oidc()
   ```
   
   **Option B: OAuth2 Client Credentials (For automated scripts)**
   - Set up OAuth2 client credentials in your Copernicus Dataspace account
   - Set environment variables:
   ```bash
   export OPENEO_CLIENT_ID='your_client_id'
   export OPENEO_CLIENT_SECRET='your_client_secret'
   ```

3. **Restart your Python environment** after setting the variables

### Verification

You can verify your openEO setup by running:
```python
import openeo
conn = openeo.connect("openeo.dataspace.copernicus.eu")
print("Available collections:", conn.list_collection_ids()[:5])  # Show first 5 collections
```

## Usage

### Urban Change Detection with openEO (New!)

For a complete urban change detection workflow using openEO API, see the Jupyter notebook:

```bash
# Run the New Delhi urban change detection example
jupyter notebook examples/new_delhi_urban_change_detection.ipynb
```

This notebook demonstrates:
- Accessing Sentinel-1 data through openEO API
- SAR backscatter processing and calibration
- Multi-temporal change detection for urban development
- Visualization of urban growth patterns in New Delhi

### Basic Change Detection Workflow

```python
from sar4cet import preprocessing, change_detection, visualization

# Define area of interest and time period
aoi = [lon_min, lat_min, lon_max, lat_max]  # Bounding box coordinates
start_date = "2020-01-01"
end_date = "2020-12-31"

# Process SAR data using simulated data (real download functionality removed)
processed_scenes = preprocessing.simulate_sample_data()

# Detect changes
changes = change_detection.detect_changes(processed_scenes, method='omnibus')

# Visualize results
visualization.plot_changes(changes)
```

Example of oil reservoir monitoring:

```python
from sar4cet import preprocessing, visualization
from sar4cet.oil_monitoring import estimate_tank_volume, detect_tank_changes, analyze_traffic, detect_anomalies

# Load preprocessed SAR images
images = [...] # List of preprocessed SAR images

# Estimate oil storage tank volumes
tank_results = estimate_tank_volume(images[0])
print(f"Detected {tank_results['count']} tanks")

# Detect changes in tank volumes between two time periods
tank_changes = detect_tank_changes(images[0], images[-1])
print(f"Total volume change: {tank_changes['total_volume_change']} cubic meters")

# Analyze traffic patterns around oil facilities
traffic_results = analyze_traffic(images)
print(f"Traffic hotspots: {len(traffic_results['traffic_hotspots'])}")

# Detect operational anomalies
anomalies = detect_anomalies(images, method='isolation_forest')
print(f"Detected {len(anomalies['anomalies'])} anomalies")
```

See the `examples` directory for more detailed examples.

## License

This project is licensed under the MIT License - see the LICENSE file for details.


