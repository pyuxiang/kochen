# Curve fitting

import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from uncertainties import ufloat

# Define function to fit
def sine(x, amplitude, phase, offset):
    return amplitude * np.sin(4*np.deg2rad(x) + phase) + offset

# Collect data
xs, ys, yerrs = data_collection()

# Perform fitting with optional parameters
popt, pcov = curve_fit(sine, xs, ys,
    p0=(1000, 0, 10),
    bounds=((-2000,-2*np.pi,0), (3000,2*np.pi,1500)),
)
perr = np.sqrt(np.diag(pcov))  # std deviation of fit
upopt = [ufloat(p, perr) for p, perr in zip(popt, perr)]  # convert into uncertainties

# Plot original data
p = plt.errorbar(xs, ys, yerrs, fmt="x", capsize=3, label=f"{qwp} (vis = {visibility}%)")

# Plot fitted data using same color
_xs = np.linspace(0, 180, 1000)
plt.plot(_xs, sine(_xs, *popt), color=p[0].get_color())

# Optionally specify size of legend before plotting
plt.legend(prop={"size": 8})
plt.tight_layout()
plt.show()
