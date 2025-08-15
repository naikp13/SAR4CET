import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap

def plot_changes(change_data, output_file=None, figsize=(12, 10)):
    """
    Plot change detection results.
    
    Parameters
    ----------
    change_data : dict
        Dictionary containing change maps from detect_changes function
    output_file : str, optional
        Path to save the figure, by default None
    figsize : tuple, optional
        Figure size, by default (12, 10)
    
    Returns
    -------
    matplotlib.figure.Figure
        Figure object
    """
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    
    # Plot first change
    first_change = change_data['first_change']
    im1 = axes[0].imshow(first_change, cmap='viridis')
    axes[0].set_title('First Change')
    plt.colorbar(im1, ax=axes[0], label='Time Step')
    
    # Plot change frequency
    change_frequency = change_data['change_frequency']
    im2 = axes[1].imshow(change_frequency, cmap='hot')
    axes[1].set_title('Change Frequency')
    plt.colorbar(im2, ax=axes[1], label='Number of Changes')
    
    # Plot change magnitude
    change_magnitude = change_data['change_magnitude']
    im3 = axes[2].imshow(change_magnitude, cmap='jet')
    axes[2].set_title('Change Magnitude')
    plt.colorbar(im3, ax=axes[2], label='Magnitude')
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    return fig

def plot_time_series(image_stack, points, output_file=None, figsize=(12, 6)):
    """
    Plot time series of SAR backscatter values at selected points.
    
    Parameters
    ----------
    image_stack : numpy.ndarray
        3D array of images (time, height, width)
    points : list
        List of (row, col) tuples for points to plot
    output_file : str, optional
        Path to save the figure, by default None
    figsize : tuple, optional
        Figure size, by default (12, 6)
    
    Returns
    -------
    matplotlib.figure.Figure
        Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Convert to dB scale
    image_stack_db = 10 * np.log10(image_stack + 1e-10)
    
    # Time steps
    time_steps = np.arange(image_stack.shape[0])
    
    # Plot time series for each point
    for i, (row, col) in enumerate(points):
        values = image_stack_db[:, row, col]
        ax.plot(time_steps, values, marker='o', label=f'Point {i+1} ({row}, {col})')
    
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Backscatter (dB)')
    ax.set_title('SAR Backscatter Time Series')
    ax.grid(True)
    ax.legend()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    return fig

def create_rgb_change_composite(change_data, output_file=None, figsize=(10, 8)):
    """
    Create an RGB composite visualization of change detection results.
    
    Parameters
    ----------
    change_data : dict
        Dictionary containing change maps from detect_changes function
    output_file : str, optional
        Path to save the figure, by default None
    figsize : tuple, optional
        Figure size, by default (10, 8)
    
    Returns
    -------
    matplotlib.figure.Figure
        Figure object
    """
    # Normalize data for RGB composite
    first_change = change_data['first_change']
    change_frequency = change_data['change_frequency']
    change_magnitude = change_data['change_magnitude']
    
    # Normalize to 0-1 range
    if first_change.max() > 0:
        r = first_change / first_change.max()
    else:
        r = first_change
        
    if change_frequency.max() > 0:
        g = change_frequency / change_frequency.max()
    else:
        g = change_frequency
        
    if change_magnitude.max() > 0:
        b = change_magnitude / change_magnitude.max()
    else:
        b = change_magnitude
    
    # Create RGB composite
    rgb = np.stack([r, g, b], axis=-1)
    
    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(rgb)
    ax.set_title('Change Detection RGB Composite')
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')
    
    # Add legend
    ax.text(0.01, 0.01, 'Red: First Change\nGreen: Change Frequency\nBlue: Change Magnitude', 
            transform=ax.transAxes, fontsize=10, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    return fig