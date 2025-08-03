# SAR4CET - Synthetic Aperture Radar to support Clean Energy Transition 

SAR4CET is repository developed under the Plan4CET project at the Insitute for Renewable Energy, EURAC Research. It provides is a toolkit for automated change detection using primarily Sentinel-1 SAR data and a scope of integration with other remote sensing modalities to improve the end product. This toolkit provides tools and utilities to process Sentinel-1 data and detect changes in land cover, urban areas, natural disasters, and oil reservoirs.

<img src="https://raw.githubusercontent.com/naikp13/SAR4CET/main/plan4cet.png" alt="XAI" width="800"/>

## Features

- Download and preprocess Sentinel-1 SAR imagery
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

## Usage

Basic example of change detection workflow:

```python
from sar4cet import preprocessing, change_detection, visualization

# Define area of interest and time period
aoi = [lon_min, lat_min, lon_max, lat_max]  # Bounding box coordinates
start_date = "2020-01-01"
end_date = "2020-12-31"

# Download and preprocess Sentinel-1 data
scenes = preprocessing.download_sentinel1(aoi, start_date, end_date)
processed_scenes = preprocessing.apply_rtc(scenes)

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


