import numpy as np
import rasterio
import cv2
from scipy import ndimage
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from datetime import datetime

def detect_anomalies(image_series, timestamps=None, roi=None, method='isolation_forest'):
    """
    Detect operational anomalies at oil facilities using time series of SAR images.
    
    Parameters
    ----------
    image_series : list
        List of SAR image file paths or numpy arrays
    timestamps : list, optional
        List of datetime objects corresponding to image acquisition times
    roi : tuple, optional
        Region of interest as (row_start, row_end, col_start, col_end)
    method : str, optional
        Anomaly detection method, by default 'isolation_forest'
        Options: 'isolation_forest', 'dbscan', 'threshold'
    
    Returns
    -------
    dict
        Dictionary containing anomaly detection results
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
        timestamps = [base_time - datetime.timedelta(days=i) for i in range(len(loaded_images)-1, -1, -1)]
    
    # Convert list of images to 3D array (time, height, width)
    image_stack = np.stack(loaded_images, axis=0)
    
    # Compute temporal statistics
    mean_image = np.mean(image_stack, axis=0)
    std_image = np.std(image_stack, axis=0)
    
    # Detect anomalies based on selected method
    if method == 'isolation_forest':
        anomalies = _isolation_forest_anomalies(image_stack, timestamps)
    elif method == 'dbscan':
        anomalies = _dbscan_anomalies(image_stack, timestamps)
    elif method == 'threshold':
        anomalies = _threshold_anomalies(image_stack, timestamps, mean_image, std_image)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return {
        'anomalies': anomalies,
        'mean_image': mean_image,
        'std_image': std_image,
        'transform': transform,
        'crs': crs
    }

def _isolation_forest_anomalies(image_stack, timestamps):
    """
    Detect anomalies using Isolation Forest algorithm.
    
    Parameters
    ----------
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    timestamps : list
        List of datetime objects
    
    Returns
    -------
    list
        List of detected anomalies
    """
    # Reshape image stack for anomaly detection
    n_times, height, width = image_stack.shape
    X = image_stack.reshape(n_times, height * width)
    
    # Apply PCA to reduce dimensionality if the data is too large
    if X.shape[1] > 1000:
        pca = PCA(n_components=min(100, n_times))
        X_pca = pca.fit_transform(X)
    else:
        X_pca = X
    
    # Apply Isolation Forest
    clf = IsolationForest(contamination=0.1, random_state=42)
    y_pred = clf.fit_predict(X_pca)
    
    # Find anomalous images (y_pred == -1)
    anomaly_indices = np.where(y_pred == -1)[0]
    
    # Create list of anomalies
    anomalies = []
    for idx in anomaly_indices:
        # Calculate anomaly score (negative of decision function, higher = more anomalous)
        score = -clf.decision_function(X_pca[idx].reshape(1, -1))[0]
        
        # Create anomaly object
        anomaly = {
            'timestamp': timestamps[idx],
            'index': idx,
            'score': score,
            'method': 'isolation_forest'
        }
        anomalies.append(anomaly)
    
    # Sort anomalies by score (most anomalous first)
    anomalies.sort(key=lambda x: x['score'], reverse=True)
    
    return anomalies

def _dbscan_anomalies(image_stack, timestamps):
    """
    Detect anomalies using DBSCAN clustering.
    
    Parameters
    ----------
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    timestamps : list
        List of datetime objects
    
    Returns
    -------
    list
        List of detected anomalies
    """
    # Reshape image stack for anomaly detection
    n_times, height, width = image_stack.shape
    X = image_stack.reshape(n_times, height * width)
    
    # Apply PCA to reduce dimensionality
    pca = PCA(n_components=min(20, n_times))
    X_pca = pca.fit_transform(X)
    
    # Apply DBSCAN
    clustering = DBSCAN(eps=3, min_samples=2).fit(X_pca)
    labels = clustering.labels_
    
    # Find anomalous images (label == -1)
    anomaly_indices = np.where(labels == -1)[0]
    
    # Create list of anomalies
    anomalies = []
    for idx in anomaly_indices:
        # Calculate distance to nearest cluster as anomaly score
        distances = []
        for label in set(labels):
            if label != -1:  # Skip noise points
                cluster_points = X_pca[labels == label]
                dist = np.min(np.linalg.norm(X_pca[idx] - cluster_points, axis=1))
                distances.append(dist)
        
        score = min(distances) if distances else 1.0
        
        # Create anomaly object
        anomaly = {
            'timestamp': timestamps[idx],
            'index': idx,
            'score': score,
            'method': 'dbscan'
        }
        anomalies.append(anomaly)
    
    # Sort anomalies by score (most anomalous first)
    anomalies.sort(key=lambda x: x['score'], reverse=True)
    
    return anomalies

def _threshold_anomalies(image_stack, timestamps, mean_image, std_image, threshold=3.0):
    """
    Detect anomalies using threshold-based method.
    
    Parameters
    ----------
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    timestamps : list
        List of datetime objects
    mean_image : numpy.ndarray
        Mean image
    std_image : numpy.ndarray
        Standard deviation image
    threshold : float, optional
        Z-score threshold for anomaly detection, by default 3.0
    
    Returns
    -------
    list
        List of detected anomalies
    """
    # Calculate z-scores for each image
    z_scores = np.zeros_like(image_stack)
    for i in range(image_stack.shape[0]):
        z_scores[i] = np.abs((image_stack[i] - mean_image) / (std_image + 1e-10))  # Avoid division by zero
    
    # Calculate mean z-score for each image
    mean_z_scores = np.mean(z_scores, axis=(1, 2))
    
    # Find anomalous images (mean z-score > threshold)
    anomaly_indices = np.where(mean_z_scores > threshold)[0]
    
    # Create list of anomalies
    anomalies = []
    for idx in anomaly_indices:
        # Create anomaly object
        anomaly = {
            'timestamp': timestamps[idx],
            'index': idx,
            'score': mean_z_scores[idx],
            'method': 'threshold'
        }
        anomalies.append(anomaly)
    
    # Sort anomalies by score (most anomalous first)
    anomalies.sort(key=lambda x: x['score'], reverse=True)
    
    return anomalies

def classify_anomalies(image_series, anomalies, roi=None):
    """
    Classify detected anomalies into different types.
    
    Parameters
    ----------
    image_series : list
        List of SAR image file paths or numpy arrays
    anomalies : list
        List of anomalies from detect_anomalies function
    roi : tuple, optional
        Region of interest as (row_start, row_end, col_start, col_end)
    
    Returns
    -------
    dict
        Dictionary containing classified anomalies
    """
    # Load images if file paths are provided
    loaded_images = []
    
    for image in image_series:
        if isinstance(image, str):
            with rasterio.open(image) as src:
                img_data = src.read(1)  # Read first band
        else:
            img_data = image
        
        # Apply ROI if provided
        if roi is not None:
            row_start, row_end, col_start, col_end = roi
            img_data = img_data[row_start:row_end, col_start:col_end]
        
        loaded_images.append(img_data)
    
    # Convert list of images to 3D array (time, height, width)
    image_stack = np.stack(loaded_images, axis=0)
    
    # Classify each anomaly
    classified_anomalies = []
    for anomaly in anomalies:
        idx = anomaly['index']
        anomaly_image = image_stack[idx]
        
        # Extract features for classification
        features = _extract_anomaly_features(anomaly_image, image_stack, idx)
        
        # Classify anomaly based on features
        anomaly_type = _classify_based_on_features(features)
        
        # Add classification to anomaly
        classified_anomaly = anomaly.copy()
        classified_anomaly['type'] = anomaly_type
        classified_anomaly['features'] = features
        
        classified_anomalies.append(classified_anomaly)
    
    # Group anomalies by type
    anomaly_types = {}
    for anomaly in classified_anomalies:
        anomaly_type = anomaly['type']
        if anomaly_type not in anomaly_types:
            anomaly_types[anomaly_type] = []
        anomaly_types[anomaly_type].append(anomaly)
    
    return {
        'classified_anomalies': classified_anomalies,
        'anomaly_types': anomaly_types
    }

def _extract_anomaly_features(anomaly_image, image_stack, idx):
    """
    Extract features for anomaly classification.
    
    Parameters
    ----------
    anomaly_image : numpy.ndarray
        Anomalous image
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    idx : int
        Index of anomaly in image stack
    
    Returns
    -------
    dict
        Dictionary of features
    """
    # Calculate temporal difference
    if idx > 0:
        prev_image = image_stack[idx - 1]
        diff_prev = anomaly_image - prev_image
    else:
        diff_prev = np.zeros_like(anomaly_image)
    
    if idx < image_stack.shape[0] - 1:
        next_image = image_stack[idx + 1]
        diff_next = anomaly_image - next_image
    else:
        diff_next = np.zeros_like(anomaly_image)
    
    # Calculate statistics
    mean_value = np.mean(anomaly_image)
    std_value = np.std(anomaly_image)
    max_value = np.max(anomaly_image)
    min_value = np.min(anomaly_image)
    
    # Calculate gradient magnitude
    grad_x = ndimage.sobel(anomaly_image, axis=1)
    grad_y = ndimage.sobel(anomaly_image, axis=0)
    gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
    mean_gradient = np.mean(gradient_magnitude)
    
    # Calculate texture features (GLCM)
    # Simplified version using standard deviation as texture measure
    texture = std_value
    
    # Calculate bright and dark spot counts
    mean_all = np.mean(image_stack)
    std_all = np.std(image_stack)
    bright_spots = np.sum(anomaly_image > (mean_all + 2 * std_all))
    dark_spots = np.sum(anomaly_image < (mean_all - 2 * std_all))
    
    return {
        'mean_value': mean_value,
        'std_value': std_value,
        'max_value': max_value,
        'min_value': min_value,
        'mean_gradient': mean_gradient,
        'texture': texture,
        'bright_spots': bright_spots,
        'dark_spots': dark_spots,
        'mean_diff_prev': np.mean(np.abs(diff_prev)),
        'mean_diff_next': np.mean(np.abs(diff_next))
    }

def _classify_based_on_features(features):
    """
    Classify anomaly based on extracted features.
    
    Parameters
    ----------
    features : dict
        Dictionary of features
    
    Returns
    -------
    str
        Anomaly type
    """
    # Simple rule-based classification
    if features['bright_spots'] > 100 and features['mean_gradient'] > 10:
        return 'sudden_activity'  # Sudden increase in activity (e.g., flaring)
    elif features['dark_spots'] > 100 and features['mean_diff_prev'] > 5:
        return 'shutdown'  # Facility shutdown or reduction in activity
    elif features['std_value'] > 2 * features['texture']:
        return 'structural_change'  # Structural changes to facility
    elif features['mean_diff_prev'] > 3 and features['mean_diff_next'] > 3:
        return 'temporary_event'  # Temporary event (e.g., maintenance)
    elif features['bright_spots'] > 50 and features['mean_value'] > 1.5 * features['min_value']:
        return 'spill'  # Potential spill or leak
    else:
        return 'unknown'  # Unknown anomaly type

def visualize_anomalies(image_series, anomalies, output_file=None, figsize=(15, 10)):
    """
    Visualize detected anomalies.
    
    Parameters
    ----------
    image_series : list
        List of SAR image file paths or numpy arrays
    anomalies : dict
        Output from classify_anomalies function
    output_file : str, optional
        Path to save the figure, by default None
    figsize : tuple, optional
        Figure size, by default (15, 10)
    
    Returns
    -------
    matplotlib.figure.Figure
        Figure object
    """
    # Load images if file paths are provided
    loaded_images = []
    for image in image_series:
        if isinstance(image, str):
            with rasterio.open(image) as src:
                img_data = src.read(1)  # Read first band
        else:
            img_data = image
        loaded_images.append(img_data)
    
    # Get classified anomalies
    classified_anomalies = anomalies['classified_anomalies']
    
    # Create figure
    n_anomalies = min(4, len(classified_anomalies))  # Show at most 4 anomalies
    fig, axes = plt.subplots(2, n_anomalies, figsize=figsize)
    
    # If only one anomaly, reshape axes for indexing
    if n_anomalies == 1:
        axes = axes.reshape(2, 1)
    
    # Plot each anomaly
    for i in range(n_anomalies):
        anomaly = classified_anomalies[i]
        idx = anomaly['index']
        anomaly_type = anomaly['type']
        score = anomaly['score']
        timestamp = anomaly['timestamp']
        
        # Get anomaly image
        anomaly_image = loaded_images[idx]
        
        # Normalize for display
        img_norm = (anomaly_image - np.min(anomaly_image)) / (np.max(anomaly_image) - np.min(anomaly_image))
        
        # Plot anomaly image
        axes[0, i].imshow(img_norm, cmap='viridis')
        axes[0, i].set_title(f"Anomaly {i+1}: {anomaly_type}\nScore: {score:.2f}")
        
        # If not the first anomaly, calculate difference with previous image
        if idx > 0:
            prev_image = loaded_images[idx - 1]
            diff_image = anomaly_image - prev_image
            
            # Normalize difference for display
            diff_min = np.min(diff_image)
            diff_max = np.max(diff_image)
            diff_norm = (diff_image - diff_min) / (diff_max - diff_min) if diff_max > diff_min else diff_image
            
            # Plot difference image
            im = axes[1, i].imshow(diff_norm, cmap='RdBu_r', vmin=-1, vmax=1)
            axes[1, i].set_title(f"Difference with Previous\n{timestamp}")
            
            # Add colorbar
            plt.colorbar(im, ax=axes[1, i], fraction=0.046, pad=0.04)
        else:
            axes[1, i].text(0.5, 0.5, "No previous image", 
                          horizontalalignment='center', verticalalignment='center',
                          transform=axes[1, i].transAxes)
            axes[1, i].set_xticks([])
            axes[1, i].set_yticks([])
    
    # Add overall title
    plt.suptitle("Detected Operational Anomalies", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust for suptitle
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    return fig