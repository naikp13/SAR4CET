import numpy as np
import cv2
from scipy import ndimage
from scipy.ndimage import gaussian_filter, sobel
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC, SVR
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
import geopandas as gpd
from skimage import feature, measure, morphology, filters
from skimage.segmentation import watershed
from skimage.feature import peak_local_max  # Fixed: was peak_local_maxima

def ultra_fast_sar_detection(sar_image, min_area=25, max_area=10000, sensitivity='medium'):
    """
    Ultra-fast SAR building detection using simple statistical thresholding.
    Optimized for SAR backscatter characteristics.
    """
    # Convert to dB if needed (minimal processing)
    if np.max(sar_image) > 10:
        img_db = 10 * np.log10(np.maximum(sar_image, 1e-10))
    else:
        img_db = sar_image.copy()
    
    # Simple percentile-based thresholding (SAR buildings are bright)
    if sensitivity == 'high':
        threshold_pct = 85
    elif sensitivity == 'low':
        threshold_pct = 95
    else:
        threshold_pct = 90
    
    threshold = np.percentile(img_db, threshold_pct)
    binary = img_db > threshold
    
    # Minimal morphology - just remove noise
    binary = ndimage.binary_opening(binary, structure=np.ones((2,2)))
    
    # Extract candidates with minimal processing
    labeled, num_features = ndimage.label(binary)
    candidates = []
    
    for i in range(1, num_features + 1):
        mask = labeled == i
        area = np.sum(mask)
        
        if min_area <= area <= max_area:
            rows, cols = np.where(mask)
            candidates.append({
                'id': f'fast_{i}',
                'mask': mask,
                'area': area,
                'bbox': (np.min(rows), np.min(cols), np.max(rows), np.max(cols)),
                'centroid': (np.mean(rows), np.mean(cols)),
                'detection_method': 'ultra_fast'
            })
    
    return candidates

def simple_sar_contrast_detection(sar_image, min_area=25, max_area=10000):
    """
    Simple contrast-based detection using local statistics.
    Exploits SAR building-background contrast.
    """
    # Minimal preprocessing
    img_smooth = ndimage.uniform_filter(sar_image, size=3)
    
    # Local contrast calculation (buildings have high local contrast)
    local_std = ndimage.generic_filter(img_smooth, np.std, size=5)
    
    # Simple threshold on local contrast
    contrast_threshold = np.percentile(local_std, 88)
    binary = local_std > contrast_threshold
    
    # Extract candidates
    labeled, num_features = ndimage.label(binary)
    candidates = []
    
    for i in range(1, num_features + 1):
        mask = labeled == i
        area = np.sum(mask)
        
        if min_area <= area <= max_area:
            rows, cols = np.where(mask)
            candidates.append({
                'id': f'contrast_{i}',
                'mask': mask,
                'area': area,
                'bbox': (np.min(rows), np.min(cols), np.max(rows), np.max(cols)),
                'centroid': (np.mean(rows), np.mean(cols)),
                'detection_method': 'contrast'
            })
    
    return candidates

def minimal_height_estimation(sar_image, candidates):
    """
    Ultra-simple height estimation based on SAR intensity.
    Uses empirical relationship between backscatter and building height.
    """
    heights = []
    
    for candidate in candidates:
        mask = candidate['mask']
        # Mean intensity in building area
        mean_intensity = np.mean(sar_image[mask])
        
        # Simple empirical height estimation (adjust coefficients as needed)
        # Based on typical SAR building signatures
        if mean_intensity > np.percentile(sar_image, 95):
            estimated_height = 15 + (mean_intensity - np.percentile(sar_image, 95)) * 2
        elif mean_intensity > np.percentile(sar_image, 90):
            estimated_height = 8 + (mean_intensity - np.percentile(sar_image, 90)) * 1.5
        else:
            estimated_height = 3 + (mean_intensity - np.percentile(sar_image, 80)) * 0.8
        
        # Clamp to reasonable range
        estimated_height = max(2, min(50, estimated_height))
        heights.append(estimated_height)
    
    return heights

def estimate_building_heights(sar_image, dem=None, method='ultra_fast', 
                            min_building_area=25, max_building_area=10000,
                            detection_sensitivity='medium'):
    """
    Ultra-fast building height estimation for SAR images.
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
    
    print(f"Processing SAR image with shape: {img_data.shape}")
    print(f"Using ultra-fast method: {method}")
    
    # Ultra-fast detection methods
    if method == 'contrast':
        building_candidates = simple_sar_contrast_detection(img_data, min_building_area, max_building_area)
    else:  # 'ultra_fast' or default
        building_candidates = ultra_fast_sar_detection(img_data, min_building_area, max_building_area, detection_sensitivity)
    
    print(f"Detected {len(building_candidates)} building candidates")
    
    if not building_candidates:
        return {
            'buildings': [],
            'heights': [],
            'features': [],
            'transform': transform,
            'crs': crs,
            'method': method
        }
    
    # Ultra-simple height estimation
    heights = minimal_height_estimation(img_data, building_candidates)
    
    return {
        'buildings': building_candidates,
        'heights': heights,
        'features': [],  # No complex features needed
        'transform': transform,
        'crs': crs,
        'method': method
    }

def enhanced_preprocessing(sar_image, sensitivity='medium'):
    """
    Enhanced preprocessing with multi-scale filtering and edge detection.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        Input SAR image
    sensitivity : str
        Detection sensitivity level
    
    Returns
    -------
    dict
        Dictionary containing multiple processed image versions
    """
    # Convert to dB if not already
    if np.max(sar_image) > 10:  # Assume linear scale
        img_db = 10 * np.log10(np.maximum(sar_image, 1e-10))
    else:
        img_db = sar_image.copy()
    
    # Normalize to 0-255 range for processing
    img_normalized = cv2.normalize(img_db, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Multi-scale speckle filtering
    # Small scale - preserves fine details
    filtered_small = cv2.bilateralFilter(img_normalized, 5, 50, 50)
    
    # Medium scale - balances noise reduction and detail preservation
    filtered_medium = cv2.bilateralFilter(img_normalized, 9, 75, 75)
    
    # Large scale - strong noise reduction
    filtered_large = cv2.bilateralFilter(img_normalized, 15, 100, 100)
    
    # Edge detection using multiple methods
    edges_canny = cv2.Canny(filtered_medium, 50, 150)
    # Around line 160-162, replace:
    # edges_sobel = np.sqrt(sobel(filtered_medium, axis=0)**2 + sobel(filtered_medium, axis=1)**2)
    # edges_sobel = cv2.normalize(edges_sobel, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # With:
    # Replace the problematic lines with:
    edges_sobel = np.sqrt(sobel(filtered_medium, axis=0)**2 + sobel(filtered_medium, axis=1)**2)
    edges_sobel = np.clip(edges_sobel, 0, np.percentile(edges_sobel[np.isfinite(edges_sobel)], 99))
    edges_sobel = (edges_sobel / edges_sobel.max() * 255).astype(np.uint8) if edges_sobel.max() > 0 else np.zeros_like(edges_sobel, dtype=np.uint8)
    # Handle NaN and infinite values
    edges_sobel = np.nan_to_num(edges_sobel, nan=0.0, posinf=255.0, neginf=0.0)
    # Ensure the array is finite and has valid range
    if edges_sobel.max() > edges_sobel.min():
        edges_sobel = ((edges_sobel - edges_sobel.min()) / (edges_sobel.max() - edges_sobel.min()) * 255).astype(np.uint8)
    else:
        edges_sobel = np.zeros_like(edges_sobel, dtype=np.uint8)
    
    # Morphological operations for structure enhancement
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    
    # Top-hat transform to enhance bright structures
    tophat_small = cv2.morphologyEx(filtered_small, cv2.MORPH_TOPHAT, kernel_small)
    tophat_medium = cv2.morphologyEx(filtered_medium, cv2.MORPH_TOPHAT, kernel_medium)
    
    # Combine different scales based on sensitivity
    if sensitivity == 'high':
        # High sensitivity - use small scale filtering
        primary_filtered = filtered_small
        structure_enhanced = tophat_small
    elif sensitivity == 'low':
        # Low sensitivity - use large scale filtering
        primary_filtered = filtered_large
        structure_enhanced = tophat_medium
    else:
        # Medium sensitivity - balanced approach
        primary_filtered = filtered_medium
        structure_enhanced = (tophat_small + tophat_medium) // 2
    
    return {
        'original': img_normalized,
        'filtered': primary_filtered,
        'structure_enhanced': structure_enhanced,
        'edges_canny': edges_canny,
        'edges_sobel': edges_sobel,
        'filtered_scales': [filtered_small, filtered_medium, filtered_large]
    }

def enhanced_building_detection(processed_images, original_image, min_area=25, max_area=10000, sensitivity='medium'):
    """
    Enhanced building detection using multiple image processing techniques.
    
    Parameters
    ----------
    processed_images : dict
        Dictionary of processed images from enhanced_preprocessing
    original_image : numpy.ndarray
        Original SAR image
    min_area : int
        Minimum building area in pixels
    max_area : int
        Maximum building area in pixels
    sensitivity : str
        Detection sensitivity level
    
    Returns
    -------
    list
        List of building candidate dictionaries
    """
    filtered_img = processed_images['filtered']
    structure_enhanced = processed_images['structure_enhanced']
    edges = processed_images['edges_canny']
    
    # Adaptive thresholding based on sensitivity
    if sensitivity == 'high':
        threshold_percentile = 75
        min_area = max(15, min_area)  # Allow smaller buildings
    elif sensitivity == 'low':
        threshold_percentile = 90
        min_area = max(50, min_area)  # Require larger buildings
    else:
        threshold_percentile = 82
    
    # Multiple detection approaches
    candidates_list = []
    
    # Method 1: Intensity-based detection
    threshold = np.percentile(filtered_img, threshold_percentile)
    binary_intensity = filtered_img > threshold
    candidates_list.append(extract_candidates_from_binary(binary_intensity, original_image, min_area, max_area, 'intensity'))
    
    # Method 2: Structure enhancement based detection
    threshold_struct = np.percentile(structure_enhanced, threshold_percentile - 5)
    binary_struct = structure_enhanced > threshold_struct
    candidates_list.append(extract_candidates_from_binary(binary_struct, original_image, min_area, max_area, 'structure'))
    
    # Method 3: Edge-based detection
    # Dilate edges to create regions
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    edges_dilated = cv2.dilate(edges, kernel, iterations=2)
    # Fill holes in edge regions
    edges_filled = ndimage.binary_fill_holes(edges_dilated)
    candidates_list.append(extract_candidates_from_binary(edges_filled, original_image, min_area, max_area, 'edges'))
    
    # Method 4: Watershed segmentation for overlapping buildings
    watershed_candidates = watershed_building_detection(filtered_img, original_image, min_area, max_area)
    candidates_list.append(watershed_candidates)
    
    # Combine and deduplicate candidates
    all_candidates = []
    for candidates in candidates_list:
        all_candidates.extend(candidates)
    
    # Remove duplicates based on overlap
    unique_candidates = remove_duplicate_candidates(all_candidates)
    
    return unique_candidates

def multi_scale_building_detection(processed_images, original_image, min_area=25, max_area=10000):
    """
    Multi-scale building detection for different building sizes.
    
    Parameters
    ----------
    processed_images : dict
        Dictionary of processed images
    original_image : numpy.ndarray
        Original SAR image
    min_area : int
        Minimum building area
    max_area : int
        Maximum building area
    
    Returns
    -------
    list
        List of building candidates
    """
    all_candidates = []
    
    # Small buildings detection (high sensitivity)
    small_candidates = enhanced_building_detection(processed_images, original_image, 
                                                  min_area, min_area*10, 'high')
    all_candidates.extend(small_candidates)
    
    # Medium buildings detection (medium sensitivity)
    medium_candidates = enhanced_building_detection(processed_images, original_image, 
                                                   min_area*5, min_area*50, 'medium')
    all_candidates.extend(medium_candidates)
    
    # Large buildings detection (low sensitivity)
    large_candidates = enhanced_building_detection(processed_images, original_image, 
                                                  min_area*20, max_area, 'low')
    all_candidates.extend(large_candidates)
    
    # Remove duplicates
    unique_candidates = remove_duplicate_candidates(all_candidates)
    
    return unique_candidates

def extract_candidates_from_binary(binary_image, original_image, min_area, max_area, method_name):
    """
    Extract building candidates from binary image.
    
    Parameters
    ----------
    binary_image : numpy.ndarray
        Binary image with potential buildings
    original_image : numpy.ndarray
        Original SAR image
    min_area : int
        Minimum area
    max_area : int
        Maximum area
    method_name : str
        Name of detection method
    
    Returns
    -------
    list
        List of building candidates
    """
    # Clean up binary image
    binary_cleaned = morphology.remove_small_objects(binary_image, min_size=min_area//2)
    binary_cleaned = ndimage.binary_fill_holes(binary_cleaned)
    
    # Label connected components
    labeled, num_features = ndimage.label(binary_cleaned)
    
    candidates = []
    
    for i in range(1, num_features + 1):
        mask = labeled == i
        area = np.sum(mask)
        
        if min_area <= area <= max_area:
            # Get region properties
            rows, cols = np.where(mask)
            min_row, max_row = np.min(rows), np.max(rows)
            min_col, max_col = np.min(cols), np.max(cols)
            
            # Calculate centroid
            centroid_row = np.mean(rows)
            centroid_col = np.mean(cols)
            
            # Calculate additional geometric properties
            width = max_col - min_col + 1
            height = max_row - min_row + 1
            
            # Calculate shape properties
            perimeter = measure.perimeter(mask)
            solidity = area / cv2.contourArea(cv2.convexHull(np.column_stack((cols, rows))))
            
            candidates.append({
                'id': f"{method_name}_{i}",
                'mask': mask,
                'area': area,
                'bbox': (min_row, min_col, max_row, max_col),
                'centroid': (centroid_row, centroid_col),
                'width': width,
                'height': height,
                'perimeter': perimeter,
                'solidity': solidity,
                'detection_method': method_name
            })
    
    return candidates

def watershed_building_detection(filtered_image, original_image, min_area, max_area):
    """
    Watershed-based building detection for separating overlapping structures.
    
    Parameters
    ----------
    filtered_image : numpy.ndarray
        Filtered SAR image
    original_image : numpy.ndarray
        Original SAR image
    min_area : int
        Minimum area
    max_area : int
        Maximum area
    
    Returns
    -------
    list
        List of building candidates
    """
    # Find local maxima as seeds
    threshold = np.percentile(filtered_image, 85)
    binary = filtered_image > threshold
    
    # Distance transform
    distance = ndimage.distance_transform_edt(binary)
    
    # Around line 404, change:
    # local_maxima = peak_local_maxima(distance, min_distance=5, threshold_abs=2)
    # To:
    local_maxima = peak_local_max(distance, min_distance=5, threshold_abs=2)
    markers = np.zeros_like(distance, dtype=int)
    markers[tuple(local_maxima.T)] = np.arange(1, len(local_maxima) + 1)
    
    # Watershed segmentation
    labels = watershed(-distance, markers, mask=binary)
    
    # Extract candidates
    candidates = []
    for region_id in np.unique(labels):
        if region_id == 0:  # Skip background
            continue
        
        mask = labels == region_id
        area = np.sum(mask)
        
        if min_area <= area <= max_area:
            rows, cols = np.where(mask)
            min_row, max_row = np.min(rows), np.max(rows)
            min_col, max_col = np.min(cols), np.max(cols)
            
            centroid_row = np.mean(rows)
            centroid_col = np.mean(cols)
            
            width = max_col - min_col + 1
            height = max_row - min_row + 1
            
            candidates.append({
                'id': f"watershed_{region_id}",
                'mask': mask,
                'area': area,
                'bbox': (min_row, min_col, max_row, max_col),
                'centroid': (centroid_row, centroid_col),
                'width': width,
                'height': height,
                'detection_method': 'watershed'
            })
    
    return candidates

def remove_duplicate_candidates(candidates):
    """
    Remove duplicate building candidates based on overlap.
    
    Parameters
    ----------
    candidates : list
        List of building candidates
    
    Returns
    -------
    list
        List of unique candidates
    """
    if not candidates:
        return []
    
    # Sort by area (largest first)
    candidates_sorted = sorted(candidates, key=lambda x: x['area'], reverse=True)
    
    unique_candidates = []
    
    for candidate in candidates_sorted:
        is_duplicate = False
        
        for existing in unique_candidates:
            # Calculate overlap
            overlap = np.logical_and(candidate['mask'], existing['mask'])
            overlap_ratio = np.sum(overlap) / min(candidate['area'], existing['area'])
            
            if overlap_ratio > 0.5:  # 50% overlap threshold
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_candidates.append(candidate)
    
    return unique_candidates

def extract_enhanced_features(sar_image, building_candidate):
    """
    Extract enhanced features for building classification and height estimation.
    
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
    if len(building_pixels) == 0:
        building_pixels = [0]
    
    mean_intensity = np.mean(building_pixels)
    std_intensity = np.std(building_pixels)
    max_intensity = np.max(building_pixels)
    min_intensity = np.min(building_pixels)
    median_intensity = np.median(building_pixels)
    intensity_range = max_intensity - min_intensity
    
    # Geometric features
    area = building_candidate['area']
    width = building_candidate['width']
    height = building_candidate['height']
    aspect_ratio = width / height if height > 0 else 0
    compactness = (4 * np.pi * area) / (building_candidate.get('perimeter', 1) ** 2)
    solidity = building_candidate.get('solidity', 0)
    
    # Texture features using GLCM approximation
    contrast = np.var(building_pixels)
    homogeneity = 1.0 / (1.0 + contrast)
    
    # Local Binary Pattern features
    if roi.size > 0:
        lbp = feature.local_binary_pattern(roi, 8, 1, method='uniform')
        lbp_hist, _ = np.histogram(lbp.ravel(), bins=10, range=(0, 9))
        lbp_uniformity = np.sum(lbp_hist ** 2) / (lbp.size ** 2)
    else:
        lbp_uniformity = 0
    
    # Edge density
    edges = cv2.Canny(roi.astype(np.uint8), 50, 150)
    edge_density = np.sum(edges > 0) / roi.size if roi.size > 0 else 0
    
    # Context features (surrounding area analysis)
    context_features = analyze_building_context(sar_image, building_candidate)
    
    # Shadow analysis features
    shadow_features = analyze_building_shadow(sar_image, building_candidate)
    
    features = {
        # Statistical features
        'mean_intensity': mean_intensity,
        'std_intensity': std_intensity,
        'max_intensity': max_intensity,
        'min_intensity': min_intensity,
        'median_intensity': median_intensity,
        'intensity_range': intensity_range,
        
        # Geometric features
        'area': area,
        'width': width,
        'height': height,
        'aspect_ratio': aspect_ratio,
        'compactness': compactness,
        'solidity': solidity,
        
        # Texture features
        'contrast': contrast,
        'homogeneity': homogeneity,
        'lbp_uniformity': lbp_uniformity,
        'edge_density': edge_density,
        
        # Context features
        'context_mean': context_features['context_mean'],
        'context_std': context_features['context_std'],
        'intensity_contrast_ratio': context_features['intensity_contrast_ratio'],
        
        # Shadow features
        'shadow_length': shadow_features['shadow_length'],
        'shadow_direction': shadow_features['shadow_direction'],
        'shadow_intensity': shadow_features['shadow_intensity'],
        'shadow_contrast': shadow_features['shadow_contrast']
    }
    
    return features

def analyze_building_context(sar_image, building_candidate):
    """
    Analyze the context around a building candidate.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        SAR image
    building_candidate : dict
        Building candidate information
    
    Returns
    -------
    dict
        Context analysis results
    """
    bbox = building_candidate['bbox']
    min_row, min_col, max_row, max_col = bbox
    
    # Define context area (2x the building size)
    context_size = max(max_row - min_row, max_col - min_col)
    context_radius = context_size
    
    center_row = (min_row + max_row) // 2
    center_col = (min_col + max_col) // 2
    
    # Extract context region
    context_min_row = max(0, center_row - context_radius)
    context_max_row = min(sar_image.shape[0], center_row + context_radius)
    context_min_col = max(0, center_col - context_radius)
    context_max_col = min(sar_image.shape[1], center_col + context_radius)
    
    context_region = sar_image[context_min_row:context_max_row, context_min_col:context_max_col]
    
    # Calculate context statistics
    context_mean = np.mean(context_region)
    context_std = np.std(context_region)
    
    # Calculate intensity contrast ratio
    building_mean = building_candidate.get('mean_intensity', np.mean(sar_image[building_candidate['mask']]))
    intensity_contrast_ratio = building_mean / context_mean if context_mean > 0 else 1.0
    
    return {
        'context_mean': context_mean,
        'context_std': context_std,
        'intensity_contrast_ratio': intensity_contrast_ratio
    }

def analyze_building_shadow(sar_image, building_candidate):
    """
    Enhanced shadow analysis for height estimation.
    
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
    
    # Define search area for shadow detection
    search_radius = max(building_candidate['width'], building_candidate['height']) * 4
    
    shadow_length = 0
    shadow_direction = 0
    shadow_intensity = np.mean(sar_image)  # Default to image mean
    shadow_contrast = 0
    
    rows, cols = sar_image.shape
    center_row, center_col = int(centroid[0]), int(centroid[1])
    
    # Search in multiple directions for shadows
    best_shadow_score = 0
    
    for angle in np.linspace(0, 2*np.pi, 16):  # More directions for better accuracy
        dx = int(search_radius * np.cos(angle))
        dy = int(search_radius * np.sin(angle))
        
        end_row = center_row + dy
        end_col = center_col + dx
        
        if 0 <= end_row < rows and 0 <= end_col < cols:
            # Sample intensity along this direction
            line_length = int(np.sqrt(dx**2 + dy**2))
            if line_length > 5:  # Minimum shadow length
                x_coords = np.linspace(center_col, end_col, line_length)
                y_coords = np.linspace(center_row, end_row, line_length)
                
                # Get intensities along the line
                intensities = []
                for x, y in zip(x_coords, y_coords):
                    if 0 <= int(y) < rows and 0 <= int(x) < cols:
                        intensities.append(sar_image[int(y), int(x)])
                
                if len(intensities) > 5:
                    intensities = np.array(intensities)
                    
                    # Look for shadow pattern (low intensity region)
                    min_intensity = np.min(intensities)
                    mean_intensity = np.mean(intensities)
                    
                    # Calculate shadow score based on intensity drop and length
                    building_intensity = np.mean(sar_image[building_candidate['mask']])
                    intensity_drop = building_intensity - min_intensity
                    shadow_score = intensity_drop * line_length
                    
                    if shadow_score > best_shadow_score:
                        best_shadow_score = shadow_score
                        shadow_intensity = min_intensity
                        shadow_direction = angle
                        shadow_length = line_length
                        shadow_contrast = intensity_drop
    
    return {
        'shadow_length': shadow_length,
        'shadow_direction': shadow_direction,
        'shadow_intensity': shadow_intensity,
        'shadow_contrast': shadow_contrast
    }

def classify_buildings(building_features, building_candidates):
    """
    Classify building candidates using machine learning.
    
    Parameters
    ----------
    building_features : list
        List of feature dictionaries
    building_candidates : list
        List of building candidates
    
    Returns
    -------
    list
        List of validated building candidates
    """
    if not building_features:
        return []
    
    # Convert features to array format
    feature_names = [
        'mean_intensity', 'std_intensity', 'max_intensity', 'median_intensity',
        'area', 'width', 'height', 'aspect_ratio', 'compactness', 'solidity',
        'contrast', 'homogeneity', 'lbp_uniformity', 'edge_density',
        'context_mean', 'context_std', 'intensity_contrast_ratio',
        'shadow_length', 'shadow_contrast'
    ]
    
    X = np.array([[features.get(name, 0) for name in feature_names] 
                  for features in building_features])
    
    # Handle NaN and infinite values
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
    
    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Simple rule-based classification (in practice, would use trained model)
    valid_indices = []
    
    for i, (features, candidate) in enumerate(zip(building_features, building_candidates)):
        # Rule-based classification criteria
        is_valid = True
        
        # Check intensity contrast
        if features.get('intensity_contrast_ratio', 0) < 1.1:
            is_valid = False
        
        # Check geometric properties
        if features.get('area', 0) < 15:  # Very small areas
            is_valid = False
        
        if features.get('aspect_ratio', 0) > 10 or features.get('aspect_ratio', 0) < 0.1:
            is_valid = False  # Too elongated
        
        # Check compactness (buildings should be reasonably compact)
        if features.get('compactness', 0) < 0.1:
            is_valid = False
        
        # Check edge density (buildings should have some structure)
        if features.get('edge_density', 0) < 0.01:
            is_valid = False
        
        if is_valid:
            valid_indices.append(i)
    
    # Return valid building candidates
    valid_buildings = [building_candidates[i] for i in valid_indices]
    
    return valid_buildings

def estimate_heights_ml_regression(building_features, building_candidates):
    """
    Estimate building heights using machine learning regression.
    
    Parameters
    ----------
    building_features : list
        List of feature dictionaries
    building_candidates : list
        List of building candidates
    
    Returns
    -------
    list
        List of height estimates in meters
    """
    if not building_candidates:
        return []
    
    height_estimates = []
    
    for i, candidate in enumerate(building_candidates):
        # Find corresponding features
        features = None
        for j, feat in enumerate(building_features):
            if j < len(building_candidates) and building_candidates[j] == candidate:
                features = feat
                break
        
        if features is None:
            height_estimates.append(10.0)  # Default height
            continue
        
        # Enhanced height estimation using multiple factors
        base_height = 3.0  # Minimum building height
        
        # Intensity-based estimation
        intensity_factor = max(0, features.get('intensity_contrast_ratio', 1.0) - 1.0)
        intensity_height = intensity_factor * 15.0
        
        # Area-based estimation
        area = features.get('area', 100)
        area_height = np.sqrt(area) * 0.3
        
        # Shadow-based estimation
        shadow_length = features.get('shadow_length', 0)
        shadow_height = shadow_length * 0.2  # Simplified shadow-to-height ratio
        
        # Geometric factor
        compactness = features.get('compactness', 0.5)
        geometric_factor = 1.0 + (1.0 - compactness) * 0.5  # More complex shapes tend to be taller
        
        # Combine estimates
        estimated_height = (base_height + intensity_height + area_height + shadow_height) * geometric_factor
        
        # Clamp to reasonable range
        estimated_height = np.clip(estimated_height, 3.0, 200.0)
        
        height_estimates.append(estimated_height)
    
    return height_estimates

def estimate_heights_shadow_analysis(sar_image, building_candidates):
    """
    Estimate building heights using enhanced shadow analysis.
    
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
    incidence_angle = 35.0  # degrees
    pixel_spacing = 0.5  # meters
    
    for candidate in building_candidates:
        shadow_features = analyze_building_shadow(sar_image, candidate)
        shadow_length_pixels = shadow_features['shadow_length']
        shadow_length_meters = shadow_length_pixels * pixel_spacing
        
        # Enhanced height estimation from shadow length
        if shadow_length_meters > 1.0:  # Minimum meaningful shadow
            # Use shadow geometry: h = L * tan(θ)
            estimated_height = shadow_length_meters * np.tan(np.radians(incidence_angle))
            
            # Apply correction factors based on shadow quality
            shadow_contrast = shadow_features.get('shadow_contrast', 0)
            if shadow_contrast > 0:
                confidence_factor = min(1.0, shadow_contrast / 10.0)  # Normalize contrast
                estimated_height *= confidence_factor
            
            estimated_height = np.clip(estimated_height, 3.0, 200.0)
        else:
            # Fallback to area-based estimation
            area = candidate['area']
            estimated_height = 3.0 + np.sqrt(area) * 0.2
            estimated_height = np.clip(estimated_height, 3.0, 50.0)
        
        height_estimates.append(estimated_height)
    
    return height_estimates

# In estimate_building_heights function, replace lines 56-67 with:
    # Fast preprocessing for better performance
    processed_img = fast_preprocessing(img_data, detection_sensitivity)
    
    # Fast building detection methods
    if method == 'shadow_analysis':
        building_candidates = fast_shadow_analysis(processed_img, img_data,
                                                  min_building_area, max_building_area)
    elif method == 'multi_scale':
        # Use fast detection with different thresholds instead of multi-scale
        candidates_high = fast_building_detection(processed_img, img_data, min_building_area, max_building_area, 'high')
        candidates_low = fast_building_detection(processed_img, img_data, min_building_area*2, max_building_area, 'low')
        building_candidates = candidates_high + candidates_low
        building_candidates = remove_duplicate_candidates(building_candidates)
    else:  # enhanced_detection or default
        building_candidates = fast_building_detection(processed_img, img_data,
                                                     min_building_area, max_building_area,
                                                     detection_sensitivity)

def fast_preprocessing(sar_image, sensitivity='medium'):
    """
    Fast preprocessing using simple filtering and edge detection.
    """
    # Convert to dB if needed
    if np.max(sar_image) > 10:
        img_db = 10 * np.log10(np.maximum(sar_image, 1e-10))
    else:
        img_db = sar_image.copy()
    
    # Simple normalization
    img_normalized = cv2.normalize(img_db, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Single fast filter instead of multiple bilateral filters
    filtered = cv2.medianBlur(img_normalized, 5)
    
    # Simple edge detection
    edges = cv2.Canny(filtered, 50, 150)
    
    return {
        'original': img_normalized,
        'filtered': filtered,
        'edges': edges
    }

def fast_building_detection(processed_images, original_image, min_area=25, max_area=10000, sensitivity='medium'):
    """
    Fast building detection using simple thresholding and morphology.
    """
    filtered_img = processed_images['filtered']
    
    # Simple adaptive threshold based on sensitivity
    if sensitivity == 'high':
        threshold_percentile = 75
    elif sensitivity == 'low':
        threshold_percentile = 90
    else:
        threshold_percentile = 82
    
    # Single threshold-based detection
    threshold = np.percentile(filtered_img, threshold_percentile)
    binary = filtered_img > threshold
    
    # Simple morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    # Extract candidates
    candidates = extract_candidates_from_binary(binary, original_image, min_area, max_area, 'fast')
    
    return candidates

def fast_shadow_analysis(processed_images, original_image, min_area=25, max_area=10000):
    """
    Fast shadow-based building detection using simple gradient analysis.
    """
    filtered_img = processed_images['filtered']
    
    # Simple gradient calculation for shadow detection
    grad_x = cv2.Sobel(filtered_img, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(filtered_img, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
    
    # Threshold for shadow edges
    shadow_threshold = np.percentile(gradient_magnitude, 85)
    shadow_edges = gradient_magnitude > shadow_threshold
    
    # Simple morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    shadow_regions = cv2.morphologyEx(shadow_edges.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    
    # Extract candidates
    candidates = extract_candidates_from_binary(shadow_regions, original_image, min_area, max_area, 'shadow')
    
    return candidates