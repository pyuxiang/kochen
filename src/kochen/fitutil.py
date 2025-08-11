import numpy as np


def gaussian(x, A, μ, σ):
    """Evaluates the Gaussian function."""
    return A * np.exp(-((x - μ) ** 2) / (2.0 * σ**2))


def gaussian_bg(x, A, μ, σ, bg):
    """Evaluates the Gaussian function with non-zero background."""
    return A * np.exp(-((x - μ) ** 2) / (2.0 * σ**2)) + bg


def gaussian_pdf(x, μ, σ):
    """Evaluates the Gaussian PDF."""
    A = 1 / (σ * np.sqrt(2 * np.pi))
    return gaussian(x, A, μ, σ)


def fit(f, xs, ys, errors: bool = False, labels: bool = False, *args, **kwargs):
    import uncertainties
    import inspect
    import scipy

    popt, pcov = scipy.optimize.curve_fit(f, xs, ys, *args, **kwargs)
    if not errors and not labels:
        return popt  # defaults to standard

    perr = np.sqrt(np.diag(pcov))
    pvals = [uncertainties.ufloat(*p) for p in zip(popt, perr)]
    argnames = list(inspect.signature(f).parameters.keys())[1:]
    pretty_pvals = [str(pval).split("+/-") for pval in pvals]
    plabels = [
        f"{a} = {v} ± {u}" for a, (v, u) in zip(argnames, pretty_pvals)
    ]  # {:P} for pretty-print alternative

    ret = pvals if errors else popt
    if labels:
        return ret, plabels
    return ret


def estimate_gaussian_params(xs, ys):
    """Estimate parameters for Gaussian fit of unimodal 'ys'.

    Returns a four-tuple representing the amplitude, mean, stddev, and
    background. Note that the amplitude here absorbs the PDF coefficient,
    i.e. '1/[sqrt(2*pi)*sigma]'.

    The signal-noise ratio should be decent (i.e. >1) for the FWHM search to
    be reasonably accurate.
    """
    assert len(xs) == len(ys)

    # Estimate amplitude
    argmax = np.argmax(ys)
    max = ys[argmax]
    center = xs[argmax]

    # Estimate background
    # Note: Using min will always yield an underestimate, so not used
    background = np.min([ys[0], ys[-1]])
    amplitude = max - background

    # Estimate stddev
    # Peak is included to guarantee first iteration is a bisection
    # Left-bias to ensure value always available
    left = np.searchsorted(ys[: argmax + 1], max / 2, "left")
    right = np.searchsorted(-ys[argmax:], -max / 2, "right") + argmax
    stddev = (xs[right - 1] - xs[left]) / 2.35482

    return (amplitude, center, stddev, background)


def lmfit_patch():
    """Add support for running guesses on CompositeModel, and adds a new Constant2dModel"""
    import lmfit

    def composite_guess(self, data, x, y, **kwargs):
        p1 = self.left.guess(data, x, y, **kwargs)
        p2 = self.right.guess(data, x, y, **kwargs)
        return p1 + p2

    lmfit.model.CompositeModel.guess = composite_guess

    class Constant2dModel(lmfit.Model):
        def __init__(self):
            def constant(x, y, c=0.0):
                return c * np.ones(np.shape(x))

            super().__init__(constant, independent_vars=["x", "y"])

        def guess(self, data, x=None, y=None, **kwargs):
            return self.make_params(c=np.mean(data))

    lmfit.models.Constant2dModel = Constant2dModel
