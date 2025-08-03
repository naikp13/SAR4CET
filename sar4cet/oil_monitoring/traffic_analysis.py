import numpy as np
import rasterio
import cv2
from scipy import ndimage
from skimage import feature, measure, segmentation
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from datetime import datetime, timedelta

def analyze_traffic(image_series, timestamps=None, roi=None, min_vehicle_size=3, max_vehicle_size=20):
    """
    Analyze traffic patterns around oil facilities using time series of SAR images.
    
    Parameters
    ----------
    image_series : list
        List of SAR image file paths or numpy arrays
    timestamps : list, optional
        List of datetime objects corresponding to image acquisition times
    roi : tuple, optional
        Region of interest as (row_start, row_end, col_start, col_end)
    min_vehicle_size : int, optional
        Minimum vehicle size in pixels, by default 3
    max_vehicle_size : int, optional
        Maximum vehicle size in pixels, by default 20
    
    Returns
    -------
    dict
        Dictionary containing traffic analysis results
    """
    # Load images if file paths are provided
    loaded_images = []
    transform = None
    crs = None
    
    for i, image in enumerate(image_series):
        if isinstance(image, str):
            with rasterio.open(image) as src:
                img_data = src.read(1)  # Read first band
                if i == 0:  # Get metadata from first image
                    transform = src.transform
                    crs = src.crs
        else:
            img_data = image
        
        # Apply ROI if provided
        if roi is not None:
            row_start, row_end, col_start, col_end = roi
            img_data = img_data[row_start:row_end, col_start:col_end]
        
        loaded_images.append(img_data)
    
    # Create timestamps if not provided
    if timestamps is None:
        base_time = datetime.now()
        timestamps = [base_time - timedelta(days=i) for i in range(len(loaded_images)-1, -1, -1)]
    
    # Detect vehicles in each image
    vehicle_detections = []
    for i, img in enumerate(loaded_images):
        # Normalize image
        img_norm = (img - np.min(img)) / (np.max(img) - np.min(img))
        
        # Apply adaptive thresholding to identify potential vehicles
        # Vehicles typically appear as bright spots in SAR imagery
        binary = img_norm > 0.8  # High threshold for bright objects
        
        # Remove small noise
        binary = ndimage.binary_opening(binary, structure=np.ones((2, 2)))
        
        # Label connected components
        labeled, num_features = ndimage.label(binary)
        
        # Extract properties of detected regions
        regions = measure.regionprops(labeled, img)
        
        # Filter regions based on size and shape
        vehicles = []
        for region in regions:
            area = region.area
            
            # Filter based on size
            if min_vehicle_size <= area <= max_vehicle_size:
                # Get vehicle properties
                centroid = region.centroid
                bbox = region.bbox
                intensity = region.mean_intensity
                
                # Add vehicle to list
                vehicles.append({
                    'centroid': centroid,
                    'bbox': bbox,
                    'area': area,
                    'intensity': intensity,
                    'timestamp': timestamps[i]
                })
        
        vehicle_detections.append(vehicles)
    
    # Analyze traffic patterns
    total_vehicles = sum(len(vehicles) for vehicles in vehicle_detections)
    avg_vehicles_per_image = total_vehicles / len(loaded_images) if loaded_images else 0
    
    # Analyze temporal patterns
    vehicles_by_time = {timestamp: len(vehicles) for timestamp, vehicles in zip(timestamps, vehicle_detections)}
    
    # Identify high traffic areas using clustering
    all_centroids = []
    for vehicles in vehicle_detections:
        for vehicle in vehicles:
            all_centroids.append(vehicle['centroid'])
    
    # If we have enough detections, perform clustering
    traffic_hotspots = []
    if all_centroids:
        all_centroids = np.array(all_centroids)
        
        # Use DBSCAN for clustering
        clustering = DBSCAN(eps=10, min_samples=3).fit(all_centroids)
        labels = clustering.labels_
        
        # Count number of unique clusters (excluding noise with label -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        # Extract hotspot information
        for i in range(n_clusters):
            cluster_points = all_centroids[labels == i]
            center = np.mean(cluster_points, axis=0)
            density = len(cluster_points)
            
            traffic_hotspots.append({
                'center': center,
                'density': density,
                'points': cluster_points.tolist()
            })
    
    return {
        'total_vehicles': total_vehicles,
        'avg_vehicles_per_image': avg_vehicles_per_image,
        'vehicles_by_time': vehicles_by_time,
        'traffic_hotspots': traffic_hotspots,
        'transform': transform,
        'crs': crs
    }

def predict_logistics(traffic_data, forecast_days=7):
    """
    Predict future logistics activity based on historical traffic patterns.
    
    Parameters
    ----------
    traffic_data : dict
        Output from analyze_traffic function
    forecast_days : int, optional
        Number of days to forecast, by default 7
    
    Returns
    -------
    dict
        Dictionary containing logistics predictions
    """
    # Extract time series data
    vehicles_by_time = traffic_data['vehicles_by_time']
    timestamps = list(vehicles_by_time.keys())
    vehicle_counts = list(vehicles_by_time.values())
    
    # Sort by timestamp
    sorted_data = sorted(zip(timestamps, vehicle_counts), key=lambda x: x[0])
    timestamps, vehicle_counts = zip(*sorted_data) if sorted_data else ([], [])
    
    # Convert to numpy arrays
    timestamps_arr = np.array([(ts - timestamps[0]).total_seconds() / 86400 for ts in timestamps])  # Convert to days
    vehicle_counts_arr = np.array(vehicle_counts)
    
    # Simple linear regression for prediction
    if len(timestamps_arr) > 1:
        # Fit linear model
        coeffs = np.polyfit(timestamps_arr, vehicle_counts_arr, 1)
        slope, intercept = coeffs
        
        # Generate forecast
        forecast_days_arr = np.arange(max(timestamps_arr) + 1, max(timestamps_arr) + forecast_days + 1)
        forecast_counts = slope * forecast_days_arr + intercept
        forecast_counts = np.maximum(forecast_counts, 0)  # Ensure non-negative counts
        
        # Convert back to datetime
        forecast_timestamps = [timestamps[0] + timedelta(days=float(day)) for day in forecast_days_arr]
        
        # Create forecast dictionary
        forecast = {ts: count for ts, count in zip(forecast_timestamps, forecast_counts)}
        
        # Calculate trend
        if slope > 0.5:
            trend = "Increasing traffic"
        elif slope < -0.5:
            trend = "Decreasing traffic"
        else:
            trend = "Stable traffic"
    else:
        # Not enough data for prediction
        forecast = {}
        trend = "Insufficient data"
        slope = 0
    
    return {
        'forecast': forecast,
        'trend': trend,
        'slope': slope,
        'historical_data': vehicles_by_time
    }

def visualize_traffic(image, traffic_data, output_file=None, figsize=(12, 10)):
    """
    Visualize traffic analysis results.
    
    Parameters
    ----------
    image : str or numpy.ndarray
        Background image for visualization
    traffic_data : dict
        Output from analyze_traffic function
    output_file : str, optional
        Path to save the figure, by default None
    figsize : tuple, optional
        Figure size, by default (12, 10)
    
    Returns
    -------
    matplotlib.figure.Figure
        Figure object
    """
    # Load image if file path is provided
    if isinstance(image, str):
        with rasterio.open(image) as src:
            img_data = src.read(1)  # Read first band
    else:
        img_data = image
    
    # Normalize image for display
    img_norm = (img_data - np.min(img_data)) / (np.max(img_data) - np.min(img_data))
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    # Display background image with traffic hotspots
    ax1.imshow(img_norm, cmap='gray')
    
    # Plot traffic hotspots
    for hotspot in traffic_data['traffic_hotspots']:
        center = hotspot['center']
        density = hotspot['density']
        
        # Size marker based on density
        size = np.sqrt(density) * 5
        
        # Plot hotspot
        ax1.plot(center[1], center[0], 'o', color='red', markersize=size, alpha=0.7)
        
        # Add text with density
        ax1.text(center[1] + 5, center[0] + 5, f'{density}', 
                color='white', fontsize=8, backgroundcolor='black')
    
    ax1.set_title('Traffic Hotspots')
    ax1.set_xlabel('Column')
    ax1.set_ylabel('Row')
    
    # Plot time series of vehicle counts
    vehicles_by_time = traffic_data['vehicles_by_time']
    timestamps = list(vehicles_by_time.keys())
    vehicle_counts = list(vehicles_by_time.values())
    
    # Sort by timestamp
    sorted_data = sorted(zip(timestamps, vehicle_counts), key=lambda x: x[0])
    timestamps, vehicle_counts = zip(*sorted_data) if sorted_data else ([], [])
    
    ax2.plot(timestamps, vehicle_counts, 'o-', color='blue')
    ax2.set_title('Vehicle Count Over Time')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Vehicle Count')
    ax2.grid(True)
    
    # Rotate x-axis labels for better readability
    plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
    
    # Add average line
    avg = traffic_data['avg_vehicles_per_image']
    ax2.axhline(y=avg, color='r', linestyle='--', label=f'Avg: {avg:.1f}')
    ax2.legend()
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    return fig