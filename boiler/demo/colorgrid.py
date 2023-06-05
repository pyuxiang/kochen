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

import sys
from typing import Callable

import colorspacious
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

def get_ciecam02_cmap(j: float = 60, c: float = 45, h: float = 0, resolution: int = 256):
    """See [2] for a description of the CIECAM02 colorspace.
    
    Most modern monitors (circa 2023) support 24-bit color depth, or about
    a million colors, which is also roughly what the human eye can discern.

    Using a resolution of 1024 points in hue (and another 1024 in lightness) and
    viewing the color on my regular monitor, I'd be hard pressed to identify the
    pixelation / color boundaries, so 1024 is probably a good upper bound.
    
    For the particular use case of mapping polar angles to color, a resolution of
    360/256 = 1.5 degrees (~2% error in projection) is probably sufficient, i.e.
    'resolution' = 256.
    """
    hue_angles = np.linspace(0, 360, resolution, endpoint=False) + h
    chroma = np.ones(resolution) * c
    lightness = np.ones(resolution) * j  # up to 65-ish?

    cbar = np.zeros((resolution, 3))
    cbar[:,0] = lightness
    cbar[:,1] = chroma
    cbar[:,2] = hue_angles
    cbar_rgb = colorspacious.cspace_convert(cbar, "JCh", "sRGB1")
    return ListedColormap(cbar_rgb)

def generate_cgrid(cmap, resolution: int = 256):
    """Returns a 2D color mapping, and convenience function to obtain RGB."""

    # Generate mesh grid for sampling
    xs = np.linspace(0, 1, resolution + 1)
    xx, yy = np.meshgrid(xs, xs)

    # Apply cmap with last value looping to first color (modulo 1)
    _xx = np.array(xx)
    _xx[:,-1] = 0
    zz = cmap(_xx)
    hsize = len(zz)//2

    # Interpolate with white
    zz[hsize:,:,:3] = 1 - (1 - zz[hsize:,:,:3]) * (1 - yy[hsize:,:,None]) * 2

    # Interpolate with black
    zz[:hsize,:,:3] = zz[:hsize,:,:3] * yy[:hsize,:,None] * 2

    def get_color(x: list, y: list):
        """Returns a (R,G,B) tuple from normalized x and y.
        
        'x' represents hue, while 'y' represents lightness.
        """
        x = np.array(x); y = np.array(y)
        if np.any((x < 0) | (x > 1) | (y < 0) | (y > 1)):
            raise ValueError("'x' and 'y' must be normalized to within [0,1].")
        xc = np.round(x * (resolution)).astype(np.int32)  # expand to {0, ..., 1000}
        yc = np.round(y * (resolution)).astype(np.int32)
        return zz[yc, xc]
    
    return get_color, (xx, yy, zz)

def generate_ciecam02_cgrid(resolution: int = 256) -> Callable:
    """Convenience function that returns (x,y) to color function."""
    cmap = get_ciecam02_cmap(resolution=resolution)
    get_color, _ = generate_cgrid(cmap, resolution=resolution)
    return get_color

if __name__ == "__main__":

    # Alternatively, use one of matplotlib's cyclic maps
    # cmap = plt.get_cmap("hsv")
    cmap = get_ciecam02_cmap()
    get_color, (xx, yy, zz) = generate_cgrid(cmap)
    plt.pcolormesh(xx, yy, zz)
    plt.show()

    # Example usage
    ys = np.linspace(0, 1, 10000)
    xs = np.arange(len(ys))
    c = get_color(ys, ys)  # vary in both lightness and hue
    plt.scatter(xs, ys, color=c)
    plt.show()

    # Demonstration of resolution effect
    rs = np.round(np.geomspace(2, 1024, 10)).astype(np.int32)
    for r in rs:
        cmap = get_ciecam02_cmap(resolution=r)
        get_color, (xx, yy, zz) = generate_cgrid(cmap, resolution=r)
        plt.subplots(figsize=(6, 5), dpi=max(128, r//2))
        plt.pcolormesh(xx, yy, zz)
        plt.title(f"CIECAM02 with resolution {r}")
        plt.xticks(np.linspace(0, 1, 5))
        plt.yticks(np.linspace(0, 1, 5))
        plt.savefig(f"ciecam02_resolution_{r:0>4d}.png")
        plt.close()
    else:
        sys.exit(0)  # free up system memory if plotting
