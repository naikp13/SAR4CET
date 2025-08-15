import numpy as np
import cv2
from scipy import ndimage
from sklearn.ensemble import RandomForestRegressor
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
import geopandas as gpd

def estimate_building_heights(sar_image, dem=None, method='bounding_box_regression', 
                            min_building_area=100, max_building_area=10000):
    """
    Estimate building heights from single SAR imagery using bounding box regression networks.
    
    Based on the methodology from "Large-scale building height retrieval from single SAR imagery 
    based on bounding box regression networks".
    
    Parameters
    ----------
    sar_image : str or numpy.ndarray
        Input SAR image (ICEYE spotlight mode data)
    dem : str or numpy.ndarray, optional
        Digital Elevation Model for terrain height correction
    method : str, optional
        Height estimation method, by default 'bounding_box_regression'
    min_building_area : int, optional
        Minimum building area in pixels, by default 100
    max_building_area : int, optional
        Maximum building area in pixels, by default 10000
    
    Returns
    -------
    dict
        Dictionary containing building detections and height estimates
    """
    # Load SAR image
    if isinstance(sar_image, str):
        with rasterio.open(sar_image) as src:
            img_data = src.read(1)
            transform = src.transform
            crs = src.crs
    else:
        img_data = sar_image
        transform = None
        crs = None
    
    # Preprocess image for building detection
    processed_img = preprocess_sar_for_buildings(img_data)
    
    # Extract building candidates
    building_candidates = extract_building_candidates(processed_img, 
                                                    min_building_area, 
                                                    max_building_area)
    
    # Extract features for each building candidate
    building_features = []
    for candidate in building_candidates:
        features = extract_building_features(img_data, candidate)
        building_features.append(features)
    
    # Estimate heights using bounding box regression
    if method == 'bounding_box_regression':
        height_estimates = estimate_heights_bbox_regression(building_features)
    elif method == 'shadow_analysis':
        height_estimates = estimate_heights_shadow_analysis(img_data, building_candidates)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Combine results
    results = {
        'buildings': building_candidates,
        'heights': height_estimates,
        'features': building_features,
        'transform': transform,
        'crs': crs,
        'method': method
    }
    
    return results

def preprocess_sar_for_buildings(sar_image):
    """
    Preprocess SAR image for building detection.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        Input SAR image
    
    Returns
    -------
    numpy.ndarray
        Preprocessed image
    """
    # Convert to dB if not already
    if np.max(sar_image) > 10:  # Assume linear scale
        img_db = 10 * np.log10(sar_image + 1e-10)
    else:
        img_db = sar_image
    
    # Apply speckle filtering
    filtered = cv2.bilateralFilter(img_db.astype(np.float32), 9, 75, 75)
    
    # Enhance building structures using morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    enhanced = cv2.morphologyEx(filtered, cv2.MORPH_TOPHAT, kernel)
    
    return enhanced

def extract_building_candidates(processed_image, min_area=100, max_area=10000):
    """
    Extract building candidates from preprocessed SAR image.
    
    Parameters
    ----------
    processed_image : numpy.ndarray
        Preprocessed SAR image
    min_area : int
        Minimum building area in pixels
    max_area : int
        Maximum building area in pixels
    
    Returns
    -------
    list
        List of building candidate dictionaries
    """
    # Adaptive thresholding to identify bright targets (buildings)
    threshold = np.percentile(processed_image, 85)
    binary = processed_image > threshold
    
    # Remove small noise
    binary = ndimage.binary_opening(binary, structure=np.ones((3, 3)))
    
    # Label connected components
    labeled, num_features = ndimage.label(binary)
    
    building_candidates = []
    
    for i in range(1, num_features + 1):
        # Get region properties
        mask = labeled == i
        area = np.sum(mask)
        
        # Filter by area
        if min_area <= area <= max_area:
            # Get bounding box
            rows, cols = np.where(mask)
            min_row, max_row = np.min(rows), np.max(rows)
            min_col, max_col = np.min(cols), np.max(cols)
            
            # Calculate centroid
            centroid_row = np.mean(rows)
            centroid_col = np.mean(cols)
            
            building_candidates.append({
                'id': i,
                'mask': mask,
                'area': area,
                'bbox': (min_row, min_col, max_row, max_col),
                'centroid': (centroid_row, centroid_col),
                'width': max_col - min_col,
                'height': max_row - min_row
            })
    
    return building_candidates

def extract_building_features(sar_image, building_candidate):
    """
    Extract features for building height estimation.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        Original SAR image
    building_candidate : dict
        Building candidate information
    
    Returns
    -------
    dict
        Dictionary of extracted features
    """
    mask = building_candidate['mask']
    bbox = building_candidate['bbox']
    min_row, min_col, max_row, max_col = bbox
    
    # Extract region of interest
    roi = sar_image[min_row:max_row+1, min_col:max_col+1]
    roi_mask = mask[min_row:max_row+1, min_col:max_col+1]
    
    # Statistical features
    building_pixels = roi[roi_mask]
    mean_intensity = np.mean(building_pixels)
    std_intensity = np.std(building_pixels)
    max_intensity = np.max(building_pixels)
    min_intensity = np.min(building_pixels)
    
    # Geometric features
    area = building_candidate['area']
    width = building_candidate['width']
    height = building_candidate['height']
    aspect_ratio = width / height if height > 0 else 0
    compactness = (4 * np.pi * area) / (width * height) if width * height > 0 else 0
    
    # Texture features (using GLCM approximation)
    contrast = np.var(building_pixels)
    
    # Shadow analysis features
    # Look for potential shadow areas around the building
    shadow_features = analyze_building_shadow(sar_image, building_candidate)
    
    features = {
        'mean_intensity': mean_intensity,
        'std_intensity': std_intensity,
        'max_intensity': max_intensity,
        'min_intensity': min_intensity,
        'area': area,
        'width': width,
        'height': height,
        'aspect_ratio': aspect_ratio,
        'compactness': compactness,
        'contrast': contrast,
        'shadow_length': shadow_features['shadow_length'],
        'shadow_direction': shadow_features['shadow_direction'],
        'shadow_intensity': shadow_features['shadow_intensity']
    }
    
    return features

def analyze_building_shadow(sar_image, building_candidate):
    """
    Analyze shadow characteristics for height estimation.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        SAR image
    building_candidate : dict
        Building candidate information
    
    Returns
    -------
    dict
        Shadow analysis results
    """
    centroid = building_candidate['centroid']
    bbox = building_candidate['bbox']
    
    # Define search area around building for shadow detection
    search_radius = max(building_candidate['width'], building_candidate['height']) * 3
    
    # Look for dark areas (potential shadows) around the building
    # This is a simplified shadow detection - in practice, would use
    # SAR geometry and acquisition parameters
    
    shadow_length = 0
    shadow_direction = 0
    shadow_intensity = 0
    
    # Simplified shadow detection based on intensity gradients
    rows, cols = sar_image.shape
    center_row, center_col = int(centroid[0]), int(centroid[1])
    
    # Search in different directions for shadows
    for angle in np.linspace(0, 2*np.pi, 8):
        dx = int(search_radius * np.cos(angle))
        dy = int(search_radius * np.sin(angle))
        
        end_row = center_row + dy
        end_col = center_col + dx
        
        if 0 <= end_row < rows and 0 <= end_col < cols:
            # Sample intensity along this direction
            line_length = int(np.sqrt(dx**2 + dy**2))
            if line_length > 0:
                x_coords = np.linspace(center_col, end_col, line_length)
                y_coords = np.linspace(center_row, end_row, line_length)
                
                # Get intensities along the line
                intensities = []
                for x, y in zip(x_coords, y_coords):
                    if 0 <= int(y) < rows and 0 <= int(x) < cols:
                        intensities.append(sar_image[int(y), int(x)])
                
                if intensities:
                    min_intensity = np.min(intensities)
                    if min_intensity < shadow_intensity or shadow_intensity == 0:
                        shadow_intensity = min_intensity
                        shadow_direction = angle
                        shadow_length = line_length
    
    return {
        'shadow_length': shadow_length,
        'shadow_direction': shadow_direction,
        'shadow_intensity': shadow_intensity
    }

def estimate_heights_bbox_regression(building_features):
    """
    Estimate building heights using bounding box regression approach.
    
    Parameters
    ----------
    building_features : list
        List of feature dictionaries for each building
    
    Returns
    -------
    list
        List of height estimates in meters
    """
    if not building_features:
        return []
    
    # Convert features to array format
    feature_names = ['mean_intensity', 'std_intensity', 'max_intensity', 'area', 
                    'width', 'height', 'aspect_ratio', 'compactness', 'contrast',
                    'shadow_length', 'shadow_intensity']
    
    X = np.array([[features.get(name, 0) for name in feature_names] 
                  for features in building_features])
    
    # Normalize features
    X_normalized = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-10)
    
    # Simple height estimation model (in practice, this would be a trained neural network)
    # This is a placeholder implementation
    height_estimates = []
    
    for features in building_features:
        # Empirical height estimation based on SAR characteristics
        # This would be replaced by a trained bounding box regression network
        
        base_height = 3.0  # Minimum building height
        
        # Height estimation based on intensity and area
        intensity_factor = features['mean_intensity'] / 10.0  # Normalize
        area_factor = np.sqrt(features['area']) / 20.0
        shadow_factor = features['shadow_length'] / 50.0
        
        estimated_height = base_height + (intensity_factor * 10) + (area_factor * 5) + (shadow_factor * 8)
        
        # Clamp to reasonable range
        estimated_height = np.clip(estimated_height, 3.0, 200.0)
        
        height_estimates.append(estimated_height)
    
    return height_estimates

def estimate_heights_shadow_analysis(sar_image, building_candidates):
    """
    Estimate building heights using shadow analysis.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        SAR image
    building_candidates : list
        List of building candidates
    
    Returns
    -------
    list
        List of height estimates in meters
    """
    height_estimates = []
    
    # SAR acquisition parameters (would be read from metadata in practice)
    # These are typical values for ICEYE spotlight mode
    incidence_angle = 35.0  # degrees
    pixel_spacing = 0.5  # meters
    
    for candidate in building_candidates:
        shadow_features = analyze_building_shadow(sar_image, candidate)
        shadow_length_pixels = shadow_features['shadow_length']
        shadow_length_meters = shadow_length_pixels * pixel_spacing
        
        # Height estimation from shadow length
        # h = L * tan(θ), where L is shadow length and θ is incidence angle
        if shadow_length_meters > 0:
            estimated_height = shadow_length_meters * np.tan(np.radians(incidence_angle))
            estimated_height = np.clip(estimated_height, 3.0, 200.0)
        else:
            estimated_height = 10.0  # Default height if no shadow detected
        
        height_estimates.append(estimated_height)
    
    return height_estimates