#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example script for using SAR4CET to detect changes in Sentinel-1 SAR imagery.

This example demonstrates the complete workflow:
1. Download Sentinel-1 data for an area of interest
2. Preprocess the data (calibration, terrain correction)
3. Perform change detection
4. Visualize the results
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directory to path to import sar4cet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sar4cet import preprocessing, change_detection, visualization

# Define area of interest (AOI) - Example: San Francisco Bay Area
aoi = [-122.5, 37.5, -122.0, 38.0]  # [lon_min, lat_min, lon_max, lat_max]

# Define time period
start_date = "2020-01-01"
end_date = "2020-12-31"

def main():
    # Create directories for data and results
    os.makedirs('data', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    
    # Step 1: Download Sentinel-1 data using openEO API
    print("Searching for Sentinel-1 data via openEO...")
    try:
        # Note: This requires setting COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET environment variables
        # Or will use interactive authentication if credentials are not set
        products = preprocessing.search_sentinel1_openeo(aoi, start_date, end_date)
        
        if not products:
            print("No Sentinel-1 data found for the specified area and time period.")
            print("Using sample data for demonstration...")
            # Use sample data for demonstration
            input_files = simulate_sample_data()
        else:
            print(f"Found {len(products)} Sentinel-1 scenes.")
            print("Downloading data...")
            input_files = preprocessing.download_sentinel1_openeo(aoi, start_date, end_date, download_dir='data')
    except Exception as e:
        print(f"Error downloading data: {e}")
        print("Using sample data for demonstration...")
        # Use sample data for demonstration
        input_files = simulate_sample_data()
    
    # Step 2: Preprocess the data
    print("\nPreprocessing data...")
    try:
        processed_files = preprocessing.apply_rtc(input_files, output_dir='processed')
        print(f"Processed {len(processed_files)} files.")
    except Exception as e:
        print(f"Error preprocessing data: {e}")
        print("Using simulated processed data for demonstration...")
        processed_files = input_files  # Just use the simulated data
    
    # Step 3: Perform change detection
    print("\nPerforming change detection...")
    try:
        # Load processed images (or simulated data)
        images = load_images(processed_files)
        
        # Apply change detection
        changes = change_detection.detect_changes(images, method='omnibus', significance=0.01)
        print("Change detection completed.")
        
        # Step 4: Visualize results
        print("\nVisualizing results...")
        # Plot change detection results
        fig = visualization.plot_changes(changes, output_file='results/change_detection_results.png')
        plt.close(fig)
        
        # Create RGB composite
        fig = visualization.create_rgb_change_composite(changes, output_file='results/change_rgb_composite.png')
        plt.close(fig)
        
        # Plot time series for selected points
        # Select a few points with changes
        points = [(100, 100), (150, 150), (200, 200)]
        fig = visualization.plot_time_series(images, points, output_file='results/time_series.png')
        plt.close(fig)
        
        print("\nResults saved to 'results' directory.")
        print("Done!")
        
    except Exception as e:
        print(f"Error in change detection or visualization: {e}")

def simulate_sample_data():
    """
    Create simulated SAR data for demonstration purposes.
    
    Returns
    -------
    list
        List of simulated file paths
    """
    print("Creating simulated SAR data...")
    
    # Create simulated file paths
    simulated_files = [f"simulated_data_{i}.tif" for i in range(5)]
    
    return simulated_files

def load_images(file_paths):
    """
    Load images from file paths or create simulated data if files don't exist.
    
    Parameters
    ----------
    file_paths : list
        List of image file paths
    
    Returns
    -------
    numpy.ndarray
        3D array of images (time, height, width)
    """
    # Check if files exist
    if all(os.path.exists(f) for f in file_paths):
        # Load actual images (implementation depends on file format)
        # This is a placeholder - in a real implementation, you would load the actual images
        print("Loading actual image data...")
        # Placeholder implementation
        images = [np.ones((512, 512)) for _ in file_paths]
    else:
        # Create simulated data
        print("Creating simulated image data...")
        
        # Create a 3D array with 5 time steps and 512x512 spatial dimensions
        images = np.zeros((5, 512, 512))
        
        # Base landscape - random terrain
        base = np.random.normal(0, 1, (512, 512))
        base = np.exp(base)  # Make it positive (like SAR backscatter)
        
        # Add some structures
        for i in range(50):
            x = np.random.randint(0, 512)
            y = np.random.randint(0, 512)
            size = np.random.randint(10, 50)
            base[max(0, x-size//2):min(512, x+size//2), max(0, y-size//2):min(512, y+size//2)] += np.random.uniform(1, 3)
        
        # Normalize
        base = base / base.max()
        
        # Create time series with changes
        for t in range(5):
            images[t] = base.copy()
            
            # Add some changes in each time step
            for i in range(10):
                x = np.random.randint(0, 512)
                y = np.random.randint(0, 512)
                size = np.random.randint(10, 30)
                change_value = np.random.uniform(0.5, 2.0)
                images[t, max(0, x-size//2):min(512, x+size//2), max(0, y-size//2):min(512, y+size//2)] *= change_value
        
        # Add speckle noise (characteristic of SAR)
        for t in range(5):
            speckle = np.random.gamma(shape=1.0, scale=0.3, size=(512, 512))
            images[t] *= speckle
    
    return np.stack(images, axis=0)

if __name__ == "__main__":
    main()