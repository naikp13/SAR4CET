import rasterio
import numpy as np
import os

def read_image(file_path):
    """
    Read an image file using rasterio.
    
    Parameters
    ----------
    file_path : str
        Path to the image file
    
    Returns
    -------
    tuple
        (image_data, metadata)
    """
    with rasterio.open(file_path) as src:
        image_data = src.read()
        metadata = src.meta
    
    return image_data, metadata

def write_image(data, output_path, metadata=None, dtype=None):
    """
    Write an image to a file using rasterio.
    
    Parameters
    ----------
    data : numpy.ndarray
        Image data to write
    output_path : str
        Path to write the image to
    metadata : dict, optional
        Metadata for the image, by default None
    dtype : str, optional
        Data type for the output image, by default None
    
    Returns
    -------
    str
        Path to the written file
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Determine the number of bands
    if data.ndim == 2:
        data = data[np.newaxis, :, :]
    
    # Set default metadata if not provided
    if metadata is None:
        height, width = data.shape[1], data.shape[2]
        count = data.shape[0]
        
        if dtype is None:
            dtype = data.dtype
        
        metadata = {
            'driver': 'GTiff',
            'height': height,
            'width': width,
            'count': count,
            'dtype': dtype,
            'crs': '+proj=latlong',
            'transform': rasterio.transform.from_bounds(
                0, 0, width, height, width, height
            )
        }
    
    # Update count if necessary
    if 'count' not in metadata or metadata['count'] != data.shape[0]:
        metadata['count'] = data.shape[0]
    
    # Write the image
    with rasterio.open(output_path, 'w', **metadata) as dst:
        dst.write(data)
    
    return output_path