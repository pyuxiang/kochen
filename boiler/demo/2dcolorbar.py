#!/usr/bin/env python3
# Justin, 2023-06-02
# Generate a cylindrical colormap using CIECAM02 colorspace.
#
# Useful for plotting points on a spherical surface, e.g.
# a Bloch/Poincare sphere, where x = arcsin(theta), and y = arctan(phi)/(pi/2).
#
# Abused the definition of lightness a little, by performing a linear interpolation
# with white and black. This makes it magnitudes faster than doing the conversion
# from actual lightness values in CIECAM02
#
# [1]: Some ideas, https://stackoverflow.com/questions/23712207/cyclic-colormap-without-visual-distortions-for-use-in-phase-angle-plots
# [2]: CIECAM02 parameters, https://en.wikipedia.org/wiki/CIECAM02
# [3]: Alternative colormaps, https://colorcet.holoviz.org/user_guide/Continuous.html
#      and corresponding paper, https://arxiv.org/abs/1509.03700
# [4]: Presentation on color theory, https://www.youtube.com/watch?v=xAoljeRJ3lU&t=898s
# [5]: Ideas for colorbar visualization,
#      https://stackoverflow.com/questions/38693563/how-to-make-a-bi-variate-or-2-dimension-colormap-with-matplotlib
#      https://stackoverflow.com/questions/45626482/how-can-i-add-a-2d-colorbar-or-a-color-wheel-to-matplotlib

import colorspacious
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

def get_ciecam02_cmap(L: float = 60, C: float = 45, h: float = 0):
    hue_angles = np.linspace(0, 360, 256, endpoint=False) + h
    chroma = np.ones(256) * C
    lightness = np.ones(256) * L  # up to 65-ish?

    cbar = np.zeros((256, 3))
    cbar[:,0] = lightness
    cbar[:,1] = chroma
    cbar[:,2] = hue_angles
    cbar_rgb = colorspacious.cspace_convert(cbar, "JCh", "sRGB1")
    return ListedColormap(cbar_rgb)

def generate_cgrid(cmap, resolution: int = 1000):
    """Returns a 2D color mapping, and convenience function to obtain RGB."""

    # Generate mesh grid for sampling
    xs = np.linspace(0, 1, resolution + 1)
    ys = np.linspace(-1, 1, resolution + 1)
    xx, yy = np.meshgrid(xs, ys)
    zz = cmap(xx)
    hsize = len(zz)//2

    # Interpolate with white
    zz[hsize:,:,:3] = 1 - (1 - zz[hsize:,:,:3]) * (1 - yy[hsize:,:,None])

    # Interpolate with black
    zz[:hsize,:,:3] = zz[:hsize,:,:3] * (1 + yy[:hsize,:,None])

    def get_color(x: list, y: list):
        """Returns a (R,G,B) tuple from normalized x and y.
        
        'x' represents hue, while 'y' represents lightness.
        """
        x = np.array(x); y = np.array(y)
        if np.any((x < 0) | (x > 1) | (y < 0) | (y > 1)):
            raise ValueError("'x' and 'y' must be normalized to within [0,1].")
        xc = np.round(x * resolution).astype(np.int32)  # expand to {0, ..., 1000}
        yc = np.round(y * resolution).astype(np.int32)
        return zz[xc,yc]
    
    # Generate cgrid axes that align to 'get_color' indices
    ns = np.linspace(0, 1, resolution + 1)
    xn, yn = np.meshgrid(ns, ns)
    return get_color, (xn, yn, zz)

# Alternatively, use one of matplotlib's cyclic maps
# cmap = plt.get_cmap("hsv")
cmap = get_ciecam02_cmap()
get_color, (xx, yy, zz) = generate_cgrid(cmap, resolution=2000)
plt.pcolormesh(xx, yy, zz)
plt.show()

# Example usage
ys = np.linspace(0, 1, 10000)
xs = np.arange(len(ys))
c = get_color(ys, ys)  # vary in both lightness and hue
plt.scatter(xs, ys, color=c)
plt.show()
