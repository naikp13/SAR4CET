import numpy as np
import rasterio
import cv2
from scipy import ndimage
from skimage import feature, measure, segmentation
import matplotlib.pyplot as plt

def estimate_tank_volume(image, dem=None, min_diameter=10, max_diameter=100, threshold=0.2):
    """
    Estimate oil storage tank volumes from SAR imagery.
    
    Parameters
    ----------
    image : str or numpy.ndarray
        SAR image file path or numpy array
    dem : str or numpy.ndarray, optional
        Digital Elevation Model for height estimation, by default None
    min_diameter : int, optional
        Minimum tank diameter in pixels, by default 10
    max_diameter : int, optional
        Maximum tank diameter in pixels, by default 100
    threshold : float, optional
        Threshold for tank detection, by default 0.2
    
    Returns
    -------
    dict
        Dictionary containing tank locations, dimensions, and volume estimates
    """
    # Load image if file path is provided
    if isinstance(image, str):
        with rasterio.open(image) as src:
            img_data = src.read(1)  # Read first band
            transform = src.transform
            crs = src.crs
    else:
        img_data = image
        transform = None
        crs = None
    
    # Normalize image
    img_norm = (img_data - np.min(img_data)) / (np.max(img_data) - np.min(img_data))
    
    # Apply adaptive thresholding to identify potential tank regions
    binary = img_norm > threshold
    
    # Remove small objects
    binary = ndimage.binary_opening(binary, structure=np.ones((3, 3)))
    
    # Label connected components
    labeled, num_features = ndimage.label(binary)
    
    # Extract properties of detected regions
    regions = measure.regionprops(labeled, img_data)
    
    # Filter regions based on size and shape
    tanks = []
    for region in regions:
        # Calculate circularity
        area = region.area
        perimeter = region.perimeter
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        # Calculate equivalent diameter
        diameter = region.equivalent_diameter
        
        # Filter based on size and shape
        if (min_diameter <= diameter <= max_diameter and 
            circularity > 0.7):  # Tanks are typically circular
            
            # Get tank properties
            centroid = region.centroid
            bbox = region.bbox
            
            # Estimate height if DEM is provided
            height = None
            if dem is not None:
                if isinstance(dem, str):
                    with rasterio.open(dem) as src:
                        dem_data = src.read(1)
                else:
                    dem_data = dem
                
                # Extract height from DEM at tank location
                row, col = int(centroid[0]), int(centroid[1])
                if 0 <= row < dem_data.shape[0] and 0 <= col < dem_data.shape[1]:
                    height = dem_data[row, col]
            
            # Calculate volume (π * r² * h)
            radius = diameter / 2
            if height is not None:
                volume = np.pi * (radius ** 2) * height
            else:
                # Estimate height based on typical aspect ratio if DEM not available
                # Typical aspect ratio (height/diameter) for oil tanks ranges from 0.5 to 1.5
                aspect_ratio = 1.0  # Default assumption
                height = diameter * aspect_ratio
                volume = np.pi * (radius ** 2) * height
            
            # Convert pixel measurements to meters if transform is available
            if transform is not None:
                pixel_size_x = transform[0]
                pixel_size_y = abs(transform[4])
                avg_pixel_size = (pixel_size_x + pixel_size_y) / 2
                
                # Convert dimensions to meters
                diameter_m = diameter * avg_pixel_size
                radius_m = radius * avg_pixel_size
                
                # Recalculate volume in cubic meters
                if height is not None:
                    height_m = height  # Assuming height is already in meters if from DEM
                    volume = np.pi * (radius_m ** 2) * height_m
            
            # Add tank to list
            tanks.append({
                'centroid': centroid,
                'bbox': bbox,
                'diameter': diameter,
                'height': height,
                'volume': volume,
                'circularity': circularity
            })
    
    return {
        'tanks': tanks,
        'count': len(tanks),
        'transform': transform,
        'crs': crs
    }

def detect_tank_changes(image_t1, image_t2, dem=None, **kwargs):
    """
    Detect changes in oil storage tank volumes between two time periods.
    
    Parameters
    ----------
    image_t1 : str or numpy.ndarray
        SAR image at time 1
    image_t2 : str or numpy.ndarray
        SAR image at time 2
    dem : str or numpy.ndarray, optional
        Digital Elevation Model for height estimation, by default None
    **kwargs : dict
        Additional arguments to pass to estimate_tank_volume
    
    Returns
    -------
    dict
        Dictionary containing tank changes
    """
    # Estimate tank volumes at both time periods
    tanks_t1 = estimate_tank_volume(image_t1, dem, **kwargs)
    tanks_t2 = estimate_tank_volume(image_t2, dem, **kwargs)
    
    # Match tanks between time periods based on location
    matched_tanks = []
    for tank1 in tanks_t1['tanks']:
        centroid1 = tank1['centroid']
        
        # Find closest tank in time 2
        min_dist = float('inf')
        closest_tank = None
        
        for tank2 in tanks_t2['tanks']:
            centroid2 = tank2['centroid']
            dist = np.sqrt((centroid1[0] - centroid2[0])**2 + (centroid1[1] - centroid2[1])**2)
            
            if dist < min_dist and dist < tank1['diameter'] / 2:  # Must be within radius
                min_dist = dist
                closest_tank = tank2
        
        if closest_tank is not None:
            # Calculate volume change
            volume_change = closest_tank['volume'] - tank1['volume']
            percent_change = (volume_change / tank1['volume']) * 100 if tank1['volume'] > 0 else 0
            
            matched_tanks.append({
                'centroid': tank1['centroid'],
                'volume_t1': tank1['volume'],
                'volume_t2': closest_tank['volume'],
                'volume_change': volume_change,
                'percent_change': percent_change
            })
    
    # Find new tanks (in t2 but not in t1)
    new_tanks = []
    for tank2 in tanks_t2['tanks']:
        centroid2 = tank2['centroid']
        is_new = True
        
        for tank1 in tanks_t1['tanks']:
            centroid1 = tank1['centroid']
            dist = np.sqrt((centroid1[0] - centroid2[0])**2 + (centroid1[1] - centroid2[1])**2)
            
            if dist < tank2['diameter'] / 2:  # Within radius
                is_new = False
                break
        
        if is_new:
            new_tanks.append(tank2)
    
    # Find removed tanks (in t1 but not in t2)
    removed_tanks = []
    for tank1 in tanks_t1['tanks']:
        centroid1 = tank1['centroid']
        is_removed = True
        
        for tank2 in tanks_t2['tanks']:
            centroid2 = tank2['centroid']
            dist = np.sqrt((centroid1[0] - centroid2[0])**2 + (centroid1[1] - centroid2[1])**2)
            
            if dist < tank1['diameter'] / 2:  # Within radius
                is_removed = False
                break
        
        if is_removed:
            removed_tanks.append(tank1)
    
    return {
        'matched_tanks': matched_tanks,
        'new_tanks': new_tanks,
        'removed_tanks': removed_tanks,
        'total_volume_change': sum(tank['volume_change'] for tank in matched_tanks),
        'transform': tanks_t1['transform'],
        'crs': tanks_t1['crs']
    }

def visualize_tank_changes(image, tank_changes, output_file=None, figsize=(12, 10)):
    """
    Visualize tank volume changes.
    
    Parameters
    ----------
    image : str or numpy.ndarray
        Background image for visualization
    tank_changes : dict
        Output from detect_tank_changes function
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
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Display background image
    ax.imshow(img_norm, cmap='gray')
    
    # Plot matched tanks with volume changes
    for tank in tank_changes['matched_tanks']:
        centroid = tank['centroid']
        percent_change = tank['percent_change']
        
        # Determine color based on change (red for decrease, green for increase)
        if percent_change < -5:  # Significant decrease
            color = 'red'
        elif percent_change > 5:  # Significant increase
            color = 'green'
        else:  # Minor change
            color = 'yellow'
        
        # Plot tank location with color indicating change
        ax.plot(centroid[1], centroid[0], 'o', color=color, markersize=10, 
                alpha=0.7, label=f'{percent_change:.1f}%')
        
        # Add text with percent change
        ax.text(centroid[1] + 5, centroid[0] + 5, f'{percent_change:.1f}%', 
                color='white', fontsize=8, backgroundcolor='black')
    
    # Plot new tanks
    for tank in tank_changes['new_tanks']:
        centroid = tank['centroid']
        ax.plot(centroid[1], centroid[0], 's', color='blue', markersize=10, 
                alpha=0.7, label='New')
    
    # Plot removed tanks
    for tank in tank_changes['removed_tanks']:
        centroid = tank['centroid']
        ax.plot(centroid[1], centroid[0], 'x', color='purple', markersize=10, 
                alpha=0.7, label='Removed')
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right')
    
    # Add title and labels
    ax.set_title('Oil Storage Tank Volume Changes')
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')
    
    # Add total volume change information
    total_change = tank_changes['total_volume_change']
    ax.text(0.02, 0.02, f'Total Volume Change: {total_change:.2f} m³', 
            transform=ax.transAxes, color='white', fontsize=10, 
            backgroundcolor='black')
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    return fig