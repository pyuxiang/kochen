from numpy import interp as lininterp
from scipy import interpolate

# Cubic interpolation
def cubicinterp(new_xs, old_xs, old_ys):
    spfn = interpolate.splrep(old_xs, old_ys)
    return list(map(lambda x: interpolate.splev(x, spfn), new_xs))