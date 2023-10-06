import functools
import inspect

import numpy as np
import scipy
import scipy.optimize
import uncertainties

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


def smooth(xs: np.ndarray, window: int = 1):
    """Simple smoothening by averaging fixed number of data points.

    Contexts:
        Useful in cases where data is noisy, and there are many data points
        from high resolution sampling. Originally from QT5201S HW2 when
        cleaning up datapoints imported from nanosecond-resolution oscilloscope
        over a range spanning tens of microseconds.

    Examples:
        Clean up noisy/excessive data:

        >>> xs = np.arange(1000)*np.pi/100
        >>> ys = np.sin(xs)
        >>> xs = smooth(xs, window=20)
        >>> ys = smooth(ys, window=20)  # same window for consistency with xs
    """
    result = []
    for i in range(xs.size//window):
        result.append(np.mean(xs[window*i:window*(i+1)]))
    return np.array(result)

def bin(xx, yy: np.ndarray, start: float, end: float, n: int):
    """Perform smoothening by averaging over x-valued bins.

    Deprecated - this existed in an era where I didn't know numpy.

    Contexts:
        Useful when x-data is not monotonically increasing, such as in a loop.
        Binning can be performed to subsequently do partial derivatives over x-axis.

    Examples:
        >>> xs, ys = bin(voltages, charges, -10, 10, 51)  # 51 points between -10V to 10V
    """
    xs = np.linspace(start, end, n)
    ys = []
    for i in range(1, xs.size):
        s = xs[i-1]; e = xs[i]
        _ = [y for i, y in enumerate(yy) if s <= xx[i] < e]
        ys.append(np.mean(_))
    xs += (xs[1]-xs[0])/2  # put in center of bin
    # print(xs, ys)
    return list(xs)[:-1], ys

def bin(xs, *yss, range=(0,1), bins=10, mode="lin"):
    """Perform smoothening by averaging over x-valued bins.

    Multi-argument 'yss' is specifically used so that binning can be done for
    inhomogenous data types as well. Mode should be one of 'lin' or
    'exp'.

    Arguments:
        xs: Data for binning, should be of numeric type.
        yss: Data for binning.
        mode: Determines whether bin widths are linear or geometric.

    Examples:
        >>> xs = np.arange(7)
        >>> ys = [ np.linspace(0, 6, 7), np.linspace(0, 60, 7) ]
        >>> rs = bin(xs, *ys, range=(0,6), bins=3)
        >>> np.all(np.array(rs) == [[0.5,2.5,4.5,6],[0.5,2.5,4.5,6],[5,25,45,60]])
        True
    """

    # Calculate desired bins, noting the right constraint for binning extremes
    start, end = range
    if mode == "lin":
        bs = np.linspace(start, end, bins+1)
    elif mode == "exp":
        bs = np.geomspace(start, end, bins+1)
    else:
        raise ValueError("'mode' should be one of {'lin', 'exp'}")

    idxs = np.digitize(xs, bs) - 1
    inputs = [xs, *yss]
    results = [np.bincount(idxs, weights=input, minlength=bins+1) for input in inputs]
    sizes = [np.bincount(idxs, minlength=bins+1) for input in inputs]
    results = [result/size for result, size in zip(results, sizes)]
    return results

def subsample(xs, *yss, range=(0,1), separation=1, mode="min"):
    """Perform subsampling.

    Examples:
        >>> xs = np.arange(7)
        >>> ys = [ np.linspace(0, 6, 7), np.linspace(0, 60, 7) ]
        >>> rs = subsample(xs, *ys, range=(0,6), separation=2)
        >>> np.all(np.array(rs) == [[0,2,4,6],[0,2,4,6],[0,20,40,60]])
        True
    """
    if mode == "min":
        # Construct choice by minimum
        idxs = np.zeros(len(xs)).astype(bool)
        prev_idx = 0; idxs[0] = True
        for curr_idx, x in enumerate(xs):
            if (x - xs[prev_idx]) < separation:
                continue
            idxs[curr_idx] = True
            prev_idx = curr_idx
    elif mode == "step":
        # Construct equal step spacing
        # Choose points higher than or equal to current step
        pass
    else:
        raise ValueError("'mode' should be one of {'min', 'step'}")

    return [np.array(xs)[idxs], *[np.array(ys)[idxs] for ys in yss]]



def pairfilter(pred, *xs):
    """Perform group-based filtering based on filtering predicate.

    Args:
        pred: Predicate for filtering, must have same number of arguments
              as number of datarows supplied.
        xs: Variable number of datarows for filtering.

    Contexts:
        Originally from QT5201S homework 2, when calculations of instantaneous
        gradient yielded spurious results near endpoints. Similarly used to
        isolate features near zero-point, to calculate a mean value.

    Note:
        This can probably be more efficiently implemented using numpy
        row-operation conventions.

    Examples:
        >>> x1 = np.linspace(0, 1, 101)
        >>> x2 = np.linspace(1, 2, 100)
        >>> pred = lambda x,y: (x > 0.5) and (y < 1.7)
        >>> _ = pairfilter(pred, x1, x2)
    """
    data = list(zip(*xs))  # group individual data points
    return list(zip(*[x for (*x,) in data if pred(*x)]))

def manual_integration(ts, xs):
    """

    Context:
        Riemann summation for discrete integration. Dynamic programming.
    """
    width = ts[1] - ts[0]
    xs = [(x*width) for x in xs]  # update values to area
    integral = [xs[0]]  # boundary condition
    for i in range(1, len(xs)):
        integral.append(integral[-1] + xs[i])
    return integral

def manual_derivative(xs, ys):
    """

    Context:
        Instantaneous derivative.

    Note:
        numpy probably has something more straightforward, can replace with
        function while substituting the theory here.
    """
    derivatives = []
    for i in range(1, len(ys)):
        derivatives.append((ys[i]-ys[i-1])/(xs[i]-xs[i-1]))
    xs = xs[1:]
    return xs, derivatives

def arange(start, stop, step):
    """Alternative to np.arange with endpoint as default.

    Uses np.linspace to minimize floating point errors.
      - Relies on (stop-start) being an integer multiple of step.
      - Assumes number of decimal places in start/stop < that in step.

    This includes the use of a precision finding step.

    Examples:
        >>> arange(0, 100, 0.1) == np.linspace(0, 100, 1001)
        >>> arange(0, 100, 0.1) != np.arange(0, 100, 0.1)
        ... #        yields floating-point errors --/^
    """
    values = np.linspace(start, stop, round((stop-start)/step)+1)
    # Clean up of potential floating point errors
    dp = find_dp(step)
    return np.array(list(map(lambda v: round(v, dp), values)))

def find_dp(n):
    """A more robust method of finding decimal place.

    Note:
        This is a better alternative to 'len(str(float(step)).split(".")[1])'.
        Only issue is the hardcoded precision size, and the log efficiency.
    """
    # TODO (Justin, 2022-11-29):
    #   Add code to check in opp. direction if precision passes.
    #   To accomodate for larger numbers.
    for precision in range(-10, 10):
        diff = abs(n - round(n, precision))
        if diff < 1e-12:
            break
    return precision

def gc_product(*args, repeat=1):
    """Gray-code equivalent of Cartesian product 'itertools.product'.

    Typically use case for when performing multivariate parameter scan for
    real devices, e.g. voltage/temperature scans, by minimizing number of
    large parameter jumps. Note that this is a binary-reflected n-bit Gray
    code.

    Further work needed to implement this as a balanced Gray code instead,
    to distribute transitions evenly across different devices. See
    'lrgc_product' for current implementation work.

    Examples:

        >>> from itertools import product
        >>> xs = "abc"
        >>> " ".join(["".join(c) for c in product(xs, repeat=2)])  # regular product
        'aa ab ac ba bb bc ca cb cc'
        >>> " ".join(["".join(c) for c in gc_product(xs, repeat=2)])
        'aa ab ac bc bb ba ca cb cc'

        # Works for arbitrary number of groups
        >>> xs = [0, 1]
        >>> " ".join(["".join(map(str, b)) for b in product(xs, repeat=3)])
        '000 001 010 011 100 101 110 111'
        >>> " ".join(["".join(map(str, b)) for b in gc_product(xs, repeat=3)])
        '000 001 011 010 110 111 101 100'

    References:
        [1]: Original source from SO, https://stackoverflow.com/a/61149719
    """
    pools = [tuple(pool) for pool in args] * repeat
    result = [[]]
    for pool in pools:
        result = [x+[y] for i, x in enumerate(result) for y in (
            reversed(pool) if i % 2 else pool)]
    for prod in result:
        yield tuple(prod)

def lrgc_product(*args):
    """Long-run Gray code variant of Cartesian product.

    WARNING: Not implemented! This is not as trivial as using 2-bit balanced
    Gray code and substituting individual pools.

    Typically use case for when performing multivariate parameter scan for
    real devices, e.g. voltage/temperature scans, by minimizing number of
    large parameter jumps (as with 'gc_product') as well as number of
    transitions, as a long-run (near-balanced) Gray code.

    2-bit LRGC sequences were precomputed and lifted from [3], up to 8-bits.
    For more bits, either compute using [2] or cross-reference original
    paper in [1].

    References:
        [1]: Original source for brute-force search of near-optimal LRGC,
             2003 Goddyn, Gvozdjak, "Binary gray codes with long bit runs"
             link: https://www.combinatorics.org/ojs/index.php/eljc/article/download/v10i1r27/pdf
        [2]: Implementation of [1], https://stackoverflow.com/a/66555635
        [3]: LRGC sequences computed using [2], https://gist.github.com/kylemcdonald/8c03de4ae1928ab5f3d203245549e802
    """
    raise NotImplementedError("n-bit balanced Gray code not implemented.")

    # WIP...
    if len(args) > 8:
        raise NotImplementedError("Gray codes for more than 8 sequences currently not implemented.")

    pools = [tuple(pool) for pool in args]
    sequence = _get_lrgc_sequence(len(args))
    pass


def _get_lrgc_sequence(num_bits):
    """Cached LRGC sequences, to avoid bloating memory."""
    assert 1 <= num_bits <= 8 and type(num_bits) == int
    if num_bits == 1:
        return (0,)
    if num_bits == 2:
        return (0,1,3,2)
    if num_bits == 3:
        return (0,1,3,2,6,7,5,4)
    if num_bits == 4:
        return (0,1,3,7,15,11,9,8,12,13,5,4,6,14,10,2)
    if num_bits == 5:
        return (0,1,3,7,15,31,29,25,17,16,18,2,10,14,12,28,20,21,23,19,27,11,9,13,5,4,6,22,30,26,24,8)
    if num_bits == 6:
        return (0,1,3,7,15,31,63,62,58,42,40,32,36,37,5,21,17,25,27,11,10,14,46,38,54,50,48,49,33,41,9,13,29,28,30,26,18,2,34,35,39,55,53,61,57,56,24,8,12,4,6,22,23,19,51,59,43,47,45,44,60,52,20,16)
    if num_bits == 7:
        return (0,32,33,35,39,103,111,127,125,93,89,81,80,16,18,2,10,42,46,44,60,124,116,117,119,87,83,91,75,11,9,13,5,37,36,38,54,118,126,122,120,88,72,64,65,1,3,7,15,47,63,61,57,121,113,112,114,82,66,74,78,14,12,28,20,52,53,55,51,115,123,107,105,73,77,69,68,4,6,22,30,62,58,56,40,104,96,97,99,67,71,79,95,31,29,25,17,49,48,50,34,98,106,110,108,76,92,84,85,21,23,19,27,59,43,41,45,109,101,100,102,70,86,94,90,26,24,8)
    if num_bits == 8:
        return (0,32,33,97,99,103,71,79,95,223,221,253,249,241,177,176,178,146,130,2,10,14,46,44,60,124,116,84,85,87,215,211,219,251,235,171,169,173,141,133,132,4,6,38,54,62,126,122,120,88,72,200,192,193,225,227,231,167,175,143,159,157,29,25,17,49,48,112,114,98,66,74,78,206,204,236,252,244,180,181,183,151,147,19,27,11,43,41,45,109,101,69,68,70,198,214,222,254,250,186,184,168,136,128,129,1,3,35,39,47,111,127,125,93,89,217,209,208,240,242,226,162,170,138,142,140,12,28,20,52,53,117,119,115,83,91,75,203,201,233,237,229,165,164,166,134,150,22,30,26,58,56,40,104,96,64,65,67,195,199,207,239,255,191,189,185,153,145,144,16,18,50,34,42,106,110,108,76,92,220,212,213,245,247,243,179,187,155,139,137,9,13,5,37,36,100,102,118,86,94,90,218,216,248,232,224,160,161,163,131,135,7,15,31,63,61,57,121,113,81,80,82,210,194,202,234,238,174,172,188,156,148,149,21,23,55,51,59,123,107,105,73,77,205,197,196,228,230,246,182,190,158,154,152,24,8)

def gaussian(x, A, μ, σ):
    """Evaluates the Gaussian function."""
    return A * np.exp(-(x-μ)**2/(2.*σ**2))

def gaussian_bg(x, A, μ, σ, bg):
    """Evaluates the Gaussian function with non-zero background."""
    return A * np.exp(-(x-μ)**2/(2.*σ**2)) + bg

def gaussian_pdf(x, μ, σ):
    """Evaluates the Gaussian PDF."""
    A = 1/(σ * np.sqrt(2 * np.pi))
    return gaussian(x, A, μ, σ)

def fit(f, xs, ys, errors: bool = False, labels: bool = False, *args, **kwargs):
    popt, pcov = scipy.optimize.curve_fit(f, xs, ys, *args, **kwargs)
    if not errors and not labels:
        return popt  # defaults to standard

    perr = np.sqrt(np.diag(pcov))
    pvals = [uncertainties.ufloat(*p) for p in zip(popt, perr)]
    argnames = list(inspect.signature(f).parameters.keys())[1:]
    pretty_pvals = [str(pval).split("+/-") for pval in pvals]
    plabels = [f"{a} = {v} ± {u}" for a, (v,u) in zip(argnames, pretty_pvals)]  # {:P} for pretty-print alternative

    ret = pvals if errors else popt
    if labels:
        return ret, plabels
    return ret

def histogram(a, bins=10, range=None, symmetric: bool = False, endpoint: bool = False, **kwargs):
    """Convenience for slight adjustments to 'np.histogram'.

    Mitigates a couple of small bugs, e.g. `np.histogram([0,1,2], bins=2, range=(0,2))`
    returns `[1,2]` instead of the expected `[1,1]` with the last bound being exclusive.

    Args:
        a: As per 'numpy.histogram'.
        bins: As per 'numpy.histogram'.
        range: As per 'numpy.histogram'.
        symmetric: Whether bin labels should be aligned to center of bin.
        endpoint: Whether right-bound of range should be a bin.

    Examples:
        >>> a = [0, 1, 2, 1, 3]; range = (0, 3)
        >>> p = lambda x, y: print(list(zip(x.astype(np.int64), y)))

        # Buggy np.histogram
        >>> ys, xs = np.histogram(a, bins=3, range=range)
        >>> p(xs, ys)  # note 'xs' also has an extra value
        [(0, 1), (1, 2), (2, 2)]

        # Expected behaviour
        >>> ys, xs = histogram(a, bins=3, range=range)
        >>> p(xs, ys)
        [(0, 1), (1, 2), (2, 1)]

        # ... with extra endpoint
        >>> ys, xs = histogram(a, bins=4, range=range, endpoint=True)
        >>> p(xs, ys)
        [(0, 1), (1, 2), (2, 1), (3, 1)]

        # ... with symmetrical behaviour
        >>> ys, xs = histogram(a, bins=5, range=(-2,2), symmetric=True, endpoint=True)
        >>> p(xs, ys)
        [(-2, 0), (-1, 0), (0, 1), (1, 2), (2, 1)]

        # ... without endpoint
        >>> ys, xs = histogram(a, bins=4, range=(-2,2), symmetric=True)
        >>> p(xs, ys)
        [(-2, 0), (-1, 0), (0, 1), (1, 2)]
    """
    # Align with 'np.histogram' behaviour
    if range is None:
        range = (np.min(a), np.max(a))

    # Calculate bin width and amount to extend right bound
    if endpoint:
        width = (range[1] - range[0]) / (bins - 1)
        extend = 2 * width
    else:
        width = (range[1] - range[0]) / bins
        extend = width

    # Left-bias bins by half-width for symmetric bins
    left, right = range
    if symmetric:
        left -= width / 2
        right -= width / 2

    # Extend range to avoid right-exclusive error
    ys, xs = np.histogram(a, bins=bins+1, range=(left,right+extend), **kwargs)

    # Return results
    if not symmetric:
        return ys[:-1], xs[:-2]
    return ys[:-1], (xs[1:-1] + xs[:-2]) / 2
