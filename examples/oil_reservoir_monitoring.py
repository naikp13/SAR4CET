#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Oil Reservoir Monitoring Example

This script demonstrates how to use the SAR4CET toolkit for monitoring oil reservoirs,
including tank volume estimation, traffic analysis, and anomaly detection.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import rasterio
from rasterio.plot import show

# Import SAR4CET modules
from sar4cet.preprocessing import search_sentinel1, download_sentinel1
from sar4cet.change_detection import detect_changes
from sar4cet.visualization import plot_changes, create_rgb_change_composite
from sar4cet.utils import read_image, write_image

# Import oil monitoring modules
from sar4cet.oil_monitoring import (
    estimate_tank_volume, detect_tank_changes,
    analyze_traffic, predict_logistics,
    detect_anomalies, classify_anomalies
)


def simulate_sar_data(num_images=5, image_size=(500, 500), num_tanks=5, seed=42):
    """
    Simulate SAR data for oil reservoir monitoring.
    
    Parameters
    ----------
    num_images : int, optional
        Number of images to generate, by default 5
    image_size : tuple, optional
        Size of images, by default (500, 500)
    num_tanks : int, optional
        Number of tanks to simulate, by default 5
    seed : int, optional
        Random seed, by default 42
    
    Returns
    -------
    tuple
        Tuple containing (image_series, timestamps, tank_locations)
    """
    np.random.seed(seed)
    
    # Generate base image with some terrain features
    base_image = np.random.normal(0.2, 0.05, image_size)
    
    # Add some terrain features
    x, y = np.meshgrid(np.linspace(0, 1, image_size[1]), np.linspace(0, 1, image_size[0]))
    terrain = 0.1 * np.sin(10 * x) * np.cos(8 * y)
    base_image += terrain
    
    # Generate tank locations
    tank_locations = []
    for _ in range(num_tanks):
        row = np.random.randint(50, image_size[0] - 50)
        col = np.random.randint(50, image_size[1] - 50)
        radius = np.random.randint(10, 30)
        tank_locations.append((row, col, radius))
    
    # Generate image series
    image_series = []
    timestamps = []
    
    base_time = datetime.now()
    
    for i in range(num_images):
        # Create a copy of the base image
        img = base_image.copy()
        
        # Add tanks with varying fill levels
        for row, col, radius in tank_locations:
            # Tank fill level varies over time
            fill_level = 0.5 + 0.3 * np.sin(i * np.pi / (num_images - 1))
            
            # Create tank
            y_grid, x_grid = np.ogrid[-row:image_size[0]-row, -col:image_size[1]-col]
            mask = x_grid*x_grid + y_grid*y_grid <= radius*radius
            
            # Add tank with bright rim and darker center based on fill level
            img[mask] = 0.8  # Bright rim
            
            # Create smaller mask for tank interior
            interior_radius = int(radius * 0.9)
            interior_mask = x_grid*x_grid + y_grid*y_grid <= interior_radius*interior_radius
            
            # Fill tank based on fill level
            fill_height = int(interior_radius * 2 * fill_level)
            fill_start = row - interior_radius + (interior_radius * 2 - fill_height)
            
            # Create fill mask
            fill_mask = interior_mask.copy()
            fill_mask[:fill_start, :] = False
            
            # Apply fill (darker than rim but brighter than background)
            img[fill_mask] = 0.4
        
        # Add some vehicles/activity around tanks
        for row, col, radius in tank_locations:
            # Add 1-3 vehicles near each tank
            num_vehicles = np.random.randint(1, 4)
            for _ in range(num_vehicles):
                # Position vehicle near tank
                vehicle_row = row + np.random.randint(-radius*3, radius*3)
                vehicle_col = col + np.random.randint(-radius*3, radius*3)
                
                # Ensure vehicle is within image bounds
                if (0 <= vehicle_row < image_size[0] and 0 <= vehicle_col < image_size[1]):
                    # Create small bright spot for vehicle
                    vehicle_size = np.random.randint(2, 5)
                    y_grid, x_grid = np.ogrid[-vehicle_row:image_size[0]-vehicle_row, 
                                             -vehicle_col:image_size[1]-vehicle_col]
                    vehicle_mask = x_grid*x_grid + y_grid*y_grid <= vehicle_size*vehicle_size
                    img[vehicle_mask] = 0.9  # Very bright
        
        # Add some random noise
        noise = np.random.normal(0, 0.05, image_size)
        img += noise
        
        # Clip values to valid range
        img = np.clip(img, 0, 1)
        
        # Add to series
        image_series.append(img)
        
        # Add timestamp (every 12 days for Sentinel-1 revisit)
        timestamps.append(base_time - timedelta(days=12 * (num_images - 1 - i)))
    
    # Add an anomaly in the last image
    if num_images > 0:
        last_img = image_series[-1].copy()
        
        # Choose a random tank to have an anomaly
        anomaly_tank = tank_locations[np.random.randint(0, len(tank_locations))]
        row, col, radius = anomaly_tank
        
        # Create a spill-like pattern extending from the tank
        spill_length = radius * 3
        spill_width = radius * 1.5
        spill_direction = np.random.uniform(0, 2 * np.pi)
        
        for r in range(image_size[0]):
            for c in range(image_size[1]):
                # Calculate distance from tank center
                dr = r - row
                dc = c - col
                dist = np.sqrt(dr*dr + dc*dc)
                
                # Calculate angle from tank center
                angle = np.arctan2(dr, dc)
                
                # Check if point is in the spill pattern
                angle_diff = np.abs((angle - spill_direction + np.pi) % (2 * np.pi) - np.pi)
                if (radius < dist < spill_length and angle_diff < spill_width / dist):
                    # Add spill effect (brighter than background)
                    last_img[r, c] = 0.7 - 0.3 * (dist - radius) / spill_length
        
        # Replace last image with anomaly
        image_series[-1] = last_img
    
    return image_series, timestamps, tank_locations


def main():
    """
    Main function to demonstrate oil reservoir monitoring.
    """
    print("SAR4CET Oil Reservoir Monitoring Example")
    print("-" * 50)
    
    # Check if we have real Sentinel-1 data
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # For this example, we'll use simulated data
    print("Generating simulated SAR data for oil reservoir...")
    image_series, timestamps, tank_locations = simulate_sar_data(num_images=5)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save simulated images for reference
    for i, (img, timestamp) in enumerate(zip(image_series, timestamps)):
        filename = os.path.join(output_dir, f"simulated_sar_{i}.tif")
        
        # Create a simple GeoTIFF
        with rasterio.open(
            filename,
            'w',
            driver='GTiff',
            height=img.shape[0],
            width=img.shape[1],
            count=1,
            dtype=img.dtype,
            crs='+proj=latlong',
            transform=rasterio.transform.from_bounds(0, 0, 1, 1, img.shape[1], img.shape[0])
        ) as dst:
            dst.write(img, 1)
        
        print(f"Saved simulated image {i} to {filename}")
    
    print("\n1. Tank Volume Estimation")
    print("-" * 30)
    
    # Estimate tank volumes in the first image
    print("Estimating tank volumes...")
    tank_results = estimate_tank_volume(image_series[0], min_diameter=5, max_diameter=50, threshold=0.6)
    
    print(f"Detected {tank_results['count']} tanks")
    for i, tank in enumerate(tank_results['tanks']):
        print(f"  Tank {i+1}: Diameter = {tank['diameter']:.1f} pixels, Volume = {tank['volume']:.1f} units")
    
    # Detect changes in tank volumes between first and last image
    print("\nDetecting changes in tank volumes...")
    tank_changes = detect_tank_changes(image_series[0], image_series[-1], 
                                     min_diameter=5, max_diameter=50, threshold=0.6)
    
    print(f"Matched {len(tank_changes['matched_tanks'])} tanks between images")
    for i, tank in enumerate(tank_changes['matched_tanks']):
        print(f"  Tank {i+1}: Volume change = {tank['volume_change']:.1f} units ({tank['percent_change']:.1f}%)")
    
    # Visualize tank changes
    print("Visualizing tank changes...")
    from sar4cet.oil_monitoring.tank_volume import visualize_tank_changes
    fig = visualize_tank_changes(image_series[-1], tank_changes)
    plt.savefig(os.path.join(output_dir, "tank_volume_changes.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print("\n2. Traffic Analysis")
    print("-" * 30)
    
    # Analyze traffic patterns
    print("Analyzing traffic patterns...")
    traffic_results = analyze_traffic(image_series, timestamps, min_vehicle_size=2, max_vehicle_size=10)
    
    print(f"Total vehicles detected: {traffic_results['total_vehicles']}")
    print(f"Average vehicles per image: {traffic_results['avg_vehicles_per_image']:.1f}")
    print(f"Traffic hotspots: {len(traffic_results['traffic_hotspots'])}")
    
    # Predict logistics activity
    print("\nPredicting logistics activity...")
    logistics_prediction = predict_logistics(traffic_results, forecast_days=7)
    
    print(f"Traffic trend: {logistics_prediction['trend']}")
    print("Forecast for next 7 days:")
    for date, count in sorted(logistics_prediction['forecast'].items()):
        print(f"  {date.strftime('%Y-%m-%d')}: {count:.1f} vehicles")
    
    # Visualize traffic
    print("Visualizing traffic analysis...")
    from sar4cet.oil_monitoring.traffic_analysis import visualize_traffic
    fig = visualize_traffic(image_series[-1], traffic_results)
    plt.savefig(os.path.join(output_dir, "traffic_analysis.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print("\n3. Anomaly Detection")
    print("-" * 30)
    
    # Detect operational anomalies
    print("Detecting operational anomalies...")
    anomaly_results = detect_anomalies(image_series, timestamps, method='isolation_forest')
    
    print(f"Detected {len(anomaly_results['anomalies'])} anomalies")
    for i, anomaly in enumerate(anomaly_results['anomalies']):
        print(f"  Anomaly {i+1}: Score = {anomaly['score']:.3f}, Date = {anomaly['timestamp'].strftime('%Y-%m-%d')}")
    
    # Classify anomalies
    print("\nClassifying anomalies...")
    classified_results = classify_anomalies(image_series, anomaly_results['anomalies'])
    
    print("Anomaly types:")
    for anomaly_type, anomalies in classified_results['anomaly_types'].items():
        print(f"  {anomaly_type}: {len(anomalies)} anomalies")
    
    # Visualize anomalies
    print("Visualizing anomalies...")
    from sar4cet.oil_monitoring.anomaly_detection import visualize_anomalies
    fig = visualize_anomalies(image_series, classified_results)
    plt.savefig(os.path.join(output_dir, "anomaly_detection.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print("\nAll results saved to:", output_dir)
    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()