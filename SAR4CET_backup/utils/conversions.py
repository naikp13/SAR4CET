import numpy as np

def db_to_linear(db_values):
    """
    Convert decibel values to linear scale.
    
    Parameters
    ----------
    db_values : numpy.ndarray
        Array of values in decibel scale
    
    Returns
    -------
    numpy.ndarray
        Array of values in linear scale
    """
    return 10 ** (db_values / 10.0)

def linear_to_db(linear_values):
    """
    Convert linear scale values to decibels.
    
    Parameters
    ----------
    linear_values : numpy.ndarray
        Array of values in linear scale
    
    Returns
    -------
    numpy.ndarray
        Array of values in decibel scale
    """
    # Add small value to avoid log of zero
    return 10.0 * np.log10(linear_values + 1e-10)