import numpy as np
from scipy.stats import chi2
import rasterio
import os

def detect_changes(images, method='omnibus', significance=0.01):
    """
    Detect changes in a time series of SAR images.
    
    Parameters
    ----------
    images : list
        List of image file paths or numpy arrays
    method : str, optional
        Change detection method to use, by default 'omnibus'
        Options: 'omnibus', 'ratio', 'difference'
    significance : float, optional
        Significance level for statistical tests, by default 0.01
    
    Returns
    -------
    dict
        Dictionary containing change maps and metadata
    """
    # Load images if file paths are provided
    if isinstance(images[0], str):
        loaded_images = []
        metadata = None
        
        for img_path in images:
            with rasterio.open(img_path) as src:
                img_data = src.read(1)  # Read first band
                if metadata is None:
                    metadata = src.meta
                loaded_images.append(img_data)
        
        images = loaded_images
    else:
        metadata = None
    
    # Convert list of images to 3D array (time, height, width)
    image_stack = np.stack(images, axis=0)
    
    # Apply selected change detection method
    if method == 'omnibus':
        changes = omnibus_test(image_stack, significance)
    elif method == 'ratio':
        changes = ratio_test(image_stack)
    elif method == 'difference':
        changes = difference_test(image_stack)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return {
        'first_change': changes['first_change'],
        'change_frequency': changes['change_frequency'],
        'change_magnitude': changes['change_magnitude'],
        'metadata': metadata
    }

def omnibus_test(image_stack, significance=0.01):
    """
    Apply the omnibus test for change detection in a time series of SAR images.
    Based on the method described in Conradsen et al. (2016).
    
    Parameters
    ----------
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    significance : float, optional
        Significance level for the test, by default 0.01
    
    Returns
    -------
    dict
        Dictionary containing change maps
    """
    k = image_stack.shape[0]  # Number of images
    rows, cols = image_stack.shape[1], image_stack.shape[2]
    
    # Initialize output arrays
    first_change = np.zeros((rows, cols), dtype=np.uint8)
    change_frequency = np.zeros((rows, cols), dtype=np.uint8)
    change_magnitude = np.zeros((rows, cols), dtype=np.float32)
    
    # Number of looks (assumed to be 5 for Sentinel-1 GRD)
    n_looks = 5
    
    # Critical value based on significance level
    critical_value = chi2.ppf(1 - significance, 2)
    
    # Compute omnibus test statistic for each pixel
    for i in range(1, k):
        # Subset of images up to current time
        subset = image_stack[:i+1]
        
        # Compute mean of all images
        mean_all = np.mean(subset, axis=0)
        
        # Compute mean of previous images
        mean_prev = np.mean(subset[:-1], axis=0)
        
        # Compute ratio of means
        ratio = mean_all / mean_prev
        
        # Compute test statistic
        test_statistic = -2 * n_looks * np.log(ratio)
        
        # Identify changes
        changes = test_statistic > critical_value
        
        # Update first change map
        mask = (first_change == 0) & changes
        first_change[mask] = i
        
        # Update change frequency map
        change_frequency[changes] += 1
        
        # Update change magnitude map
        change_magnitude[changes] = np.maximum(change_magnitude[changes], test_statistic[changes])
    
    return {
        'first_change': first_change,
        'change_frequency': change_frequency,
        'change_magnitude': change_magnitude
    }

def ratio_test(image_stack):
    """
    Apply a simple ratio test for change detection between consecutive SAR images.
    
    Parameters
    ----------
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    
    Returns
    -------
    dict
        Dictionary containing change maps
    """
    k = image_stack.shape[0]  # Number of images
    rows, cols = image_stack.shape[1], image_stack.shape[2]
    
    # Initialize output arrays
    first_change = np.zeros((rows, cols), dtype=np.uint8)
    change_frequency = np.zeros((rows, cols), dtype=np.uint8)
    change_magnitude = np.zeros((rows, cols), dtype=np.float32)
    
    # Threshold for ratio test (can be adjusted)
    threshold = 1.5
    
    # Compute ratio between consecutive images
    for i in range(1, k):
        # Compute ratio
        ratio = image_stack[i] / (image_stack[i-1] + 1e-10)  # Add small value to avoid division by zero
        
        # Identify changes (ratio > threshold or ratio < 1/threshold)
        changes = (ratio > threshold) | (ratio < 1/threshold)
        
        # Update first change map
        mask = (first_change == 0) & changes
        first_change[mask] = i
        
        # Update change frequency map
        change_frequency[changes] += 1
        
        # Update change magnitude map (using log ratio as magnitude)
        log_ratio = np.abs(np.log(ratio))
        change_magnitude[changes] = np.maximum(change_magnitude[changes], log_ratio[changes])
    
    return {
        'first_change': first_change,
        'change_frequency': change_frequency,
        'change_magnitude': change_magnitude
    }

def difference_test(image_stack):
    """
    Apply a simple difference test for change detection between consecutive SAR images.
    
    Parameters
    ----------
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    
    Returns
    -------
    dict
        Dictionary containing change maps
    """
    k = image_stack.shape[0]  # Number of images
    rows, cols = image_stack.shape[1], image_stack.shape[2]
    
    # Initialize output arrays
    first_change = np.zeros((rows, cols), dtype=np.uint8)
    change_frequency = np.zeros((rows, cols), dtype=np.uint8)
    change_magnitude = np.zeros((rows, cols), dtype=np.float32)
    
    # Convert to dB scale
    image_stack_db = 10 * np.log10(image_stack + 1e-10)
    
    # Threshold for difference test in dB (can be adjusted)
    threshold = 3.0  # 3 dB change
    
    # Compute difference between consecutive images
    for i in range(1, k):
        # Compute difference
        diff = np.abs(image_stack_db[i] - image_stack_db[i-1])
        
        # Identify changes
        changes = diff > threshold
        
        # Update first change map
        mask = (first_change == 0) & changes
        first_change[mask] = i
        
        # Update change frequency map
        change_frequency[changes] += 1
        
        # Update change magnitude map
        change_magnitude[changes] = np.maximum(change_magnitude[changes], diff[changes])
    
    return {
        'first_change': first_change,
        'change_frequency': change_frequency,
        'change_magnitude': change_magnitude
    }