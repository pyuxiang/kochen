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
