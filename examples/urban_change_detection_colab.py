# Urban Change Detection using SAR4CET in Google Colab
# This script demonstrates how to use the SAR4CET repository for urban change detection

# Install required packages
import sys
import subprocess

def run_command(cmd):
    """Run a shell command and return the output"""
    return subprocess.check_call(cmd, shell=True)

print("Installing required packages...")
run_command("pip install sentinelsat rasterio matplotlib numpy scikit-learn scikit-image geopandas shapely")

# Clone the SAR4CET repository
print("Cloning the SAR4CET repository...")
run_command("git clone https://github.com/naikp13/SAR4CET.git")

# Check if setup.py exists, create it if it doesn't
if not os.path.exists('./SAR4CET/setup.py'):
    print("setup.py not found, creating it...")
    setup_py_content = '''
from setuptools import setup, find_packages

setup(
    name="sar4cet",
    version="0.1.0",
    author="SAR4CET Team",
    author_email="example@example.com",
    description="Synthetic Aperture Radar for Change Detection Toolkit",
    long_description="A toolkit for SAR-based change detection",
    long_description_content_type="text/markdown",
    url="https://github.com/naikp13/SAR4CET",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy",
        "matplotlib",
        "rasterio",
        "scikit-learn",
        "scikit-image",
        "geopandas",
        "shapely",
        "pandas",
        "scipy",
        "sentinelsat",
          "pyproj",
          "fiona",
          "scikit-image",
          "opencv-python",
      ],
)
'''
    with open('./SAR4CET/setup.py', 'w') as f:
        f.write(setup_py_content)

# Install the package in development mode
print("Installing the package in development mode...")
run_command("pip install -e ./SAR4CET")

import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import rasterio
from rasterio.plot import show
import geopandas as gpd
from shapely.geometry import box
import warnings
warnings.filterwarnings('ignore')

# Import SAR4CET modules
try:
    from sar4cet import preprocessing, change_detection, visualization, utils
except ModuleNotFoundError:
    print("Could not import sar4cet. Trying alternative approaches...")
    import sys
    import os
    
    # Try different installation methods
    print("Attempting to install from local clone...")
    
    # Check if setup.py exists in the cloned repository
    if not os.path.exists('./SAR4CET/setup.py'):
        print("setup.py not found in cloned repository, creating it...")
        setup_py_content = '''
from setuptools import setup, find_packages

setup(
    name="sar4cet",
    version="0.1.0",
    author="SAR4CET Team",
    author_email="example@example.com",
    description="Synthetic Aperture Radar for Change Detection Toolkit",
    long_description="A toolkit for SAR-based change detection",
    long_description_content_type="text/markdown",
    url="https://github.com/naikp13/SAR4CET",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
         "numpy",
         "matplotlib",
         "rasterio",
         "scikit-learn",
         "scikit-image",
         "geopandas",
         "shapely",
         "pandas",
         "scipy",
         "sentinelsat",
         "pyproj",
         "fiona",
         "scikit-image",
         "opencv-python",
     ],
)
'''
        with open('./SAR4CET/setup.py', 'w') as f:
            f.write(setup_py_content)
    
    run_command("pip install -e ./SAR4CET")
    
    # Try direct installation from GitHub as a fallback
    print("Attempting to install directly from GitHub...")
    run_command("pip install git+https://github.com/naikp13/SAR4CET.git")
    
    # Add potential paths to sys.path
    sys.path.append('./SAR4CET')
    sys.path.append('.')
    
    # Check if the repository was cloned to a different directory
    if os.path.exists('SAR4CET'):
        sys.path.append('SAR4CET')
    
    # Try importing again
    try:
        from sar4cet import preprocessing, change_detection, visualization, utils
        print("Successfully imported sar4cet modules")
    except ModuleNotFoundError as e:
        print(f"Error importing sar4cet: {e}")
        print("Continuing with simulated data only...")
        
        # Define minimal stub versions of required modules to allow script to run
        class StubModule:
            def __getattr__(self, name):
                return lambda *args, **kwargs: None
        
        preprocessing = StubModule()
        change_detection = StubModule()
        visualization = StubModule()
        utils = StubModule()
        
        # Override specific functions needed for the script
        def omnibus_test(image_stack, alpha=0.01):
            """Stub implementation of omnibus test"""
            return (image_stack > 0).astype(int)  # Simple thresholding as placeholder
        
        change_detection.omnibus_test = omnibus_test
        
        # Define visualization functions
        def plot_changes(change_map, ax=None, title="Change Detection Results"):
            """Stub implementation of plot_changes"""
            if ax is None:
                fig, ax = plt.subplots(figsize=(10, 8))
            ax.imshow(change_map, cmap='viridis')
            ax.set_title(title)
            ax.set_axis_off()
            return ax
        
        def plot_time_series(time_series, dates=None, ax=None, title="Time Series"):
            """Stub implementation of plot_time_series"""
            if ax is None:
                fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(time_series)
            if dates:
                ax.set_xticks(range(len(dates)))
                ax.set_xticklabels(dates, rotation=45)
            ax.set_title(title)
            ax.set_ylabel('Backscatter (dB)')
            return ax
        
        def create_rgb_change_composite(images, stretch_percentile=2):
            """Stub implementation of create_rgb_change_composite"""
            if len(images) < 3:
                return np.zeros((images[0].shape[0], images[0].shape[1], 3))
            
            # Create a simple RGB composite
            rgb = np.zeros((images[0].shape[0], images[0].shape[1], 3))
            for i, img in enumerate(images[:3]):
                rgb[:, :, i] = img
            
            # Simple stretch
            for i in range(3):
                p_low, p_high = np.percentile(rgb[:, :, i], [stretch_percentile, 100-stretch_percentile])
                rgb[:, :, i] = np.clip((rgb[:, :, i] - p_low) / (p_high - p_low), 0, 1)
            
            return rgb
        
        visualization.plot_changes = plot_changes
        visualization.plot_time_series = plot_time_series
        visualization.create_rgb_change_composite = create_rgb_change_composite

# Define your area of interest (AOI) for an urban area
# Example: San Francisco, CA
def create_aoi_bbox(min_lon=-122.5, min_lat=37.7, max_lon=-122.3, max_lat=37.8):
    """Create a bounding box for the area of interest"""
    return box(min_lon, min_lat, max_lon, max_lat)

# Create a GeoDataFrame from the AOI
def create_aoi_geodataframe(aoi_bbox):
    """Create a GeoDataFrame from the AOI bounding box"""
    gdf = gpd.GeoDataFrame(index=[0], crs='EPSG:4326', geometry=[aoi_bbox])
    return gdf

# Function to simulate SAR data for testing when actual data download is not possible
def simulate_sar_data(num_images=3, width=500, height=500):
    """Simulate SAR data for testing"""
    # Create a directory to store simulated data
    os.makedirs('simulated_data', exist_ok=True)
    
    # Generate simulated SAR images with urban features
    image_paths = []
    dates = []
    
    # Base image with urban-like features
    base = np.random.gamma(shape=1.0, scale=0.3, size=(height, width))
    
    # Add some structures that look like buildings
    for i in range(20):
        x = np.random.randint(50, width-100)
        y = np.random.randint(50, height-100)
        size_x = np.random.randint(20, 80)
        size_y = np.random.randint(20, 80)
        base[y:y+size_y, x:x+size_x] = np.random.gamma(shape=5.0, scale=0.5, size=(size_y, size_x))
    
    # Generate time series with changes
    for i in range(num_images):
        # Copy the base image
        img = base.copy()
        
        # Add some changes for each time step
        if i > 0:
            # Add or remove some buildings
            for _ in range(5):
                x = np.random.randint(50, width-100)
                y = np.random.randint(50, height-100)
                size_x = np.random.randint(20, 60)
                size_y = np.random.randint(20, 60)
                if np.random.rand() > 0.5:
                    # Add a building
                    img[y:y+size_y, x:x+size_x] = np.random.gamma(shape=5.0, scale=0.5, size=(size_y, size_x))
                else:
                    # Remove a building
                    img[y:y+size_y, x:x+size_x] = np.random.gamma(shape=1.0, scale=0.3, size=(size_y, size_x))
        
        # Save the image
        date = datetime.now() - timedelta(days=(num_images-i)*15)
        dates.append(date.strftime('%Y%m%d'))
        
        filename = f'simulated_data/sar_image_{dates[i]}.tif'
        
        # Create a GeoTIFF
        transform = rasterio.transform.from_bounds(-122.5, 37.7, -122.3, 37.8, width, height)
        with rasterio.open(
            filename, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=img.dtype,
            crs='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs',
            transform=transform
        ) as dst:
            dst.write(img, 1)
        
        image_paths.append(filename)
    
    return image_paths, dates

# Main function to run the urban change detection workflow
def run_urban_change_detection(use_simulated_data=True):
    """Run the urban change detection workflow"""
    print("Starting urban change detection workflow...")
    
    if use_simulated_data:
        print("Using simulated SAR data...")
        image_paths, dates = simulate_sar_data(num_images=3)
        print(f"Generated {len(image_paths)} simulated SAR images")
    else:
        # Set up Copernicus Open Access Hub credentials
        # You need to register at https://scihub.copernicus.eu/dhus/
        username = input("Enter your Copernicus Open Access Hub username: ")
        password = input("Enter your Copernicus Open Access Hub password: ")
        
        # Create AOI
        aoi_bbox = create_aoi_bbox()
        aoi_gdf = create_aoi_geodataframe(aoi_bbox)
        
        # Define time period
        start_date = '20220101'
        end_date = '20220401'
        
        # Search for Sentinel-1 data
        print("Searching for Sentinel-1 data...")
        products = preprocessing.search_sentinel1(
            aoi=aoi_gdf,
            start_date=start_date,
            end_date=end_date,
            username=username,
            password=password
        )
        
        if len(products) == 0:
            print("No Sentinel-1 data found. Using simulated data instead.")
            image_paths, dates = simulate_sar_data(num_images=3)
        else:
            # Download Sentinel-1 data
            print(f"Found {len(products)} Sentinel-1 products. Downloading...")
            downloaded_files = preprocessing.download_sentinel1(
                products=products,
                username=username,
                password=password,
                output_dir='sentinel1_data'
            )
            
            # Preprocess the data
            print("Preprocessing Sentinel-1 data...")
            calibrated_files = []
            for file in downloaded_files:
                # Calibrate
                cal_file = preprocessing.calibrate_data(
                    input_file=file,
                    calibration_type='Sigma0',
                    output_db=True
                )
                calibrated_files.append(cal_file)
            
            # Apply speckle filtering
            filtered_files = []
            for file in calibrated_files:
                filt_file = preprocessing.apply_speckle_filter(
                    input_file=file,
                    filter_type='Lee',
                    filter_size=5
                )
                filtered_files.append(filt_file)
            
            # Apply terrain correction
            image_paths = []
            for file in filtered_files:
                tc_file = preprocessing.apply_rtc(
                    input_file=file
                )
                image_paths.append(tc_file)
            
            # Extract dates from filenames
            dates = [os.path.basename(file).split('_')[4] for file in image_paths]
    
    # Perform change detection
    print("Performing change detection...")
    
    # Read the images
    images = []
    for path in image_paths:
        with rasterio.open(path) as src:
            img = src.read(1)
            images.append(img)
    
    # Convert list to numpy array
    image_stack = np.array(images)
    
    # Apply Omnibus change detection
    print("Applying Omnibus change detection...")
    omnibus_result = change_detection.omnibus_test(image_stack, alpha=0.01)
    
    # Visualize the results
    print("Visualizing results...")
    fig, ax = plt.subplots(figsize=(10, 8))
    visualization.plot_changes(omnibus_result, ax=ax, title="Urban Change Detection Results")
    plt.savefig('urban_change_detection_result.png')
    
    # Create RGB change composite
    if len(images) >= 3:
        print("Creating RGB change composite...")
        rgb_composite = visualization.create_rgb_change_composite(
            [images[0], images[1], images[2]],
            stretch_percentile=2
        )
        
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(rgb_composite)
        ax.set_title("RGB Change Composite")
        ax.set_axis_off()
        plt.savefig('rgb_change_composite.png')
    
    # Plot time series for a sample point
    print("Plotting time series for a sample point...")
    sample_row = image_stack.shape[1] // 2
    sample_col = image_stack.shape[2] // 2
    time_series = image_stack[:, sample_row, sample_col]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    visualization.plot_time_series(
        time_series,
        dates=dates,
        ax=ax,
        title=f"Backscatter Time Series at Point ({sample_row}, {sample_col})"
    )
    plt.savefig('time_series_plot.png')
    
    print("Urban change detection workflow completed!")
    print("Results saved as:")
    print("  - urban_change_detection_result.png")
    print("  - rgb_change_composite.png")
    print("  - time_series_plot.png")

# Run the workflow
if __name__ == "__main__":
    # By default, use simulated data to avoid requiring Copernicus credentials
    run_urban_change_detection(use_simulated_data=True)
    
    # To use real Sentinel-1 data, set use_simulated_data to False
    # run_urban_change_detection(use_simulated_data=False)