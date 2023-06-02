#!/usr/bin/env python3
# Justin, 2023-06-02
# Plot Bloch vector into 2D colormap
# Essentially HSL...

import numpy as np
import matplotlib.pyplot as plt

cmap = plt.get_cmap("hsv")
res = 1000
xs = np.linspace(0, 1, res)
ys = np.linspace(-1, 1, res)

xx, yy = np.meshgrid(xs, ys)
zz = cmap(xx)
hsize = len(zz)//2
print(zz)
zz[hsize:,:,:3] = 1 - (1 - zz[hsize:,:,:3]) * (1 - yy[hsize:,:,None])
zz[:hsize,:,:3] = zz[:hsize,:,:3] * (1 + yy[:hsize,:,None])

# raise
plt.pcolormesh(xx, yy, zz)
plt.show()
