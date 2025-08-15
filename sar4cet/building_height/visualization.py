import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from mpl_toolkits.axes_grid1 import make_axes_locatable

def plot_height_map(sar_image, building_detections, height_estimates, 
                   title="Building Height Estimation", figsize=(15, 10),
                   height_colormap='viridis', save_path=None):
    """
    Visualize building height estimation results on SAR imagery.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        Input SAR image
    building_detections : list
        List of building detection dictionaries
    height_estimates : numpy.ndarray
        Estimated heights for each building
    title : str
        Plot title
    figsize : tuple
        Figure size (width, height)
    height_colormap : str
        Colormap for height visualization
    save_path : str, optional
        Path to save the plot
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # Plot 1: SAR image with building detections
    ax1 = axes[0]
    im1 = ax1.imshow(sar_image, cmap='gray', aspect='equal')
    ax1.set_title('SAR Image with Building Detections')
    ax1.set_xlabel('Range (pixels)')
    ax1.set_ylabel('Azimuth (pixels)')
    
    # Overlay building detections
    for i, detection in enumerate(building_detections):
        bbox = detection['bbox']
        rect = patches.Rectangle(
            (bbox[1], bbox[0]), bbox[3] - bbox[1], bbox[2] - bbox[0],
            linewidth=2, edgecolor='red', facecolor='none', alpha=0.7
        )
        ax1.add_patch(rect)
        
        # Add building ID
        ax1.text(bbox[1], bbox[0] - 5, f'B{i+1}', 
                color='red', fontsize=8, fontweight='bold')
    
    # Plot 2: Height map
    ax2 = axes[1]
    im2 = ax2.imshow(sar_image, cmap='gray', aspect='equal', alpha=0.7)
    
    # Create height colormap
    if len(height_estimates) > 0:
        vmin, vmax = np.min(height_estimates), np.max(height_estimates)
        
        # Overlay building heights
        for i, (detection, height) in enumerate(zip(building_detections, height_estimates)):
            bbox = detection['bbox']
            
            # Color based on height
            norm_height = (height - vmin) / (vmax - vmin) if vmax > vmin else 0
            color = plt.cm.get_cmap(height_colormap)(norm_height)
            
            rect = patches.Rectangle(
                (bbox[1], bbox[0]), bbox[3] - bbox[1], bbox[2] - bbox[0],
                linewidth=2, edgecolor='white', facecolor=color, alpha=0.8
            )
            ax2.add_patch(rect)
            
            # Add height text
            center_x = (bbox[1] + bbox[3]) / 2
            center_y = (bbox[0] + bbox[2]) / 2
            ax2.text(center_x, center_y, f'{height:.1f}m', 
                    ha='center', va='center', color='white', 
                    fontsize=8, fontweight='bold')
    
    ax2.set_title('Estimated Building Heights')
    ax2.set_xlabel('Range (pixels)')
    ax2.set_ylabel('Azimuth (pixels)')
    
    # Add colorbar for heights
    if len(height_estimates) > 0:
        divider = make_axes_locatable(ax2)
        cax = divider.append_axes("right", size="5%", pad=0.1)
        sm = plt.cm.ScalarMappable(cmap=height_colormap, 
                                  norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, cax=cax)
        cbar.set_label('Height (m)', rotation=270, labelpad=20)
    
    plt.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.show()

def visualize_building_detections(sar_image, building_detections, 
                                 features=None, title="Building Detections",
                                 figsize=(12, 8), save_path=None):
    """
    Visualize building detection results with optional feature analysis.
    
    Parameters
    ----------
    sar_image : numpy.ndarray
        Input SAR image
    building_detections : list
        List of building detection dictionaries
    features : numpy.ndarray, optional
        Feature matrix for buildings
    title : str
        Plot title
    figsize : tuple
        Figure size (width, height)
    save_path : str, optional
        Path to save the plot
    """
    if features is not None:
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        axes = axes.flatten()
    else:
        fig, axes = plt.subplots(1, 1, figsize=(8, 8))
        axes = [axes]
    
    # Plot 1: SAR image with detections
    ax1 = axes[0]
    im1 = ax1.imshow(sar_image, cmap='gray', aspect='equal')
    ax1.set_title('Building Detections')
    ax1.set_xlabel('Range (pixels)')
    ax1.set_ylabel('Azimuth (pixels)')
    
    # Overlay building detections with different colors
    colors = plt.cm.Set3(np.linspace(0, 1, len(building_detections)))
    
    for i, (detection, color) in enumerate(zip(building_detections, colors)):
        bbox = detection['bbox']
        rect = patches.Rectangle(
            (bbox[1], bbox[0]), bbox[3] - bbox[1], bbox[2] - bbox[0],
            linewidth=2, edgecolor=color, facecolor='none', alpha=0.8
        )
        ax1.add_patch(rect)
        
        # Add building ID
        ax1.text(bbox[1], bbox[0] - 5, f'B{i+1}', 
                color=color, fontsize=10, fontweight='bold')
        
        # Add area information
        area = detection.get('area', 0)
        ax1.text(bbox[1], bbox[2] + 5, f'{area}px²', 
                color=color, fontsize=8)
    
    if features is not None and len(features) > 0:
        # Plot 2: Feature distribution - Intensity statistics
        ax2 = axes[1]
        intensity_features = features[:, :4]  # Assuming first 4 are intensity stats
        feature_names = ['Mean', 'Std', 'Min', 'Max']
        
        for i, name in enumerate(feature_names):
            ax2.hist(intensity_features[:, i], alpha=0.7, label=name, bins=10)
        
        ax2.set_title('Intensity Feature Distribution')
        ax2.set_xlabel('Feature Value')
        ax2.set_ylabel('Frequency')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Feature correlation heatmap
        ax3 = axes[2]
        if features.shape[1] > 1:
            # Select subset of features for visualization
            n_features = min(10, features.shape[1])
            corr_matrix = np.corrcoef(features[:, :n_features].T)
            
            im3 = ax3.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
            ax3.set_title('Feature Correlation Matrix')
            ax3.set_xticks(range(n_features))
            ax3.set_yticks(range(n_features))
            ax3.set_xticklabels([f'F{i+1}' for i in range(n_features)])
            ax3.set_yticklabels([f'F{i+1}' for i in range(n_features)])
            
            # Add colorbar
            divider = make_axes_locatable(ax3)
            cax = divider.append_axes("right", size="5%", pad=0.1)
            plt.colorbar(im3, cax=cax)
        
        # Plot 4: Building size distribution
        ax4 = axes[3]
        areas = [det.get('area', 0) for det in building_detections]
        if areas:
            ax4.hist(areas, bins=min(10, len(areas)), alpha=0.7, color='skyblue')
            ax4.set_title('Building Size Distribution')
            ax4.set_xlabel('Area (pixels²)')
            ax4.set_ylabel('Count')
            ax4.grid(True, alpha=0.3)
            
            # Add statistics
            mean_area = np.mean(areas)
            ax4.axvline(mean_area, color='red', linestyle='--', 
                       label=f'Mean: {mean_area:.0f}px²')
            ax4.legend()
    
    plt.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.show()

def plot_height_estimation_results(results, method_names=None, 
                                  figsize=(15, 10), save_path=None):
    """
    Plot comprehensive height estimation results and statistics.
    
    Parameters
    ----------
    results : dict or list
        Results from height estimation methods
    method_names : list, optional
        Names of the methods used
    figsize : tuple
        Figure size (width, height)
    save_path : str, optional
        Path to save the plot
    """
    if isinstance(results, dict):
        results = [results]
        method_names = method_names or ['Method 1']
    
    if method_names is None:
        method_names = [f'Method {i+1}' for i in range(len(results))]
    
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    axes = axes.flatten()
    
    # Collect all heights for comparison
    all_heights = []
    for result in results:
        if 'height_estimates' in result:
            all_heights.extend(result['height_estimates'])
    
    # Plot 1: Height distribution comparison
    ax1 = axes[0]
    for i, (result, name) in enumerate(zip(results, method_names)):
        if 'height_estimates' in result:
            heights = result['height_estimates']
            ax1.hist(heights, alpha=0.7, label=name, bins=15)
    
    ax1.set_title('Height Distribution by Method')
    ax1.set_xlabel('Estimated Height (m)')
    ax1.set_ylabel('Frequency')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Method comparison statistics
    ax2 = axes[1]
    stats_data = []
    labels = []
    
    for result, name in zip(results, method_names):
        if 'height_estimates' in result:
            heights = result['height_estimates']
            if len(heights) > 0:
                stats_data.append(heights)
                labels.append(name)
    
    if stats_data:
        bp = ax2.boxplot(stats_data, labels=labels, patch_artist=True)
        colors = plt.cm.Set3(np.linspace(0, 1, len(stats_data)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
    
    ax2.set_title('Height Estimation Statistics')
    ax2.set_ylabel('Height (m)')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Building count and coverage
    ax3 = axes[2]
    building_counts = []
    method_labels = []
    
    for result, name in zip(results, method_names):
        if 'building_detections' in result:
            count = len(result['building_detections'])
            building_counts.append(count)
            method_labels.append(name)
    
    if building_counts:
        bars = ax3.bar(method_labels, building_counts, 
                      color=plt.cm.Set3(np.linspace(0, 1, len(building_counts))),
                      alpha=0.7)
        ax3.set_title('Number of Buildings Detected')
        ax3.set_ylabel('Building Count')
        
        # Add value labels on bars
        for bar, count in zip(bars, building_counts):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    str(count), ha='center', va='bottom', fontweight='bold')
    
    # Plot 4: Height vs Area scatter (if area data available)
    ax4 = axes[3]
    for i, (result, name) in enumerate(zip(results, method_names)):
        if 'height_estimates' in result and 'building_detections' in result:
            heights = result['height_estimates']
            detections = result['building_detections']
            
            areas = [det.get('area', 0) for det in detections]
            if len(areas) == len(heights) and len(areas) > 0:
                color = plt.cm.Set3(i / len(results))
                ax4.scatter(areas, heights, alpha=0.7, label=name, 
                           color=color, s=50)
    
    ax4.set_title('Building Height vs Area')
    ax4.set_xlabel('Building Area (pixels²)')
    ax4.set_ylabel('Estimated Height (m)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle('Building Height Estimation Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Analysis plot saved to {save_path}")
    
    plt.show()