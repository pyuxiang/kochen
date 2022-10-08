import numpy as np
import scipy

# Linear interpolation
def lininterp(new_xs, old_xs, old_ys):
    """Performs a linear interpolation.
    
    Examples:
        >>> xs = np.linspace(0, 2*np.pi, 11)
        >>> ys = np.sin(xs)
        >>> new_xs = np.linspace(0, 2*np.pi, 7)
        >>> new_ys = lininterp(new_xs, xs, ys)
    """
    return np.interp(new_xs, old_xs, old_ys)

# Cubic interpolation
def cubicinterp(new_xs, old_xs, old_ys):
    """Performs a cubic spline interpolation.

    Examples:
        >>> xs = np.linspace(0, 2*np.pi, 11)
        >>> ys = np.sin(xs)
        >>> new_xs = np.linspace(0, 2*np.pi, 7)
        >>> new_ys = cubicinterp(new_xs, xs, ys)
    """
    spfn = scipy.interpolate.splrep(old_xs, old_ys)
    return np.array([scipy.interpolate.splev(x, spfn) for x in new_xs])