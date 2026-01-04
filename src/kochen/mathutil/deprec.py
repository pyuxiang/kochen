import numpy as np
import scipy
import scipy.optimize

from kochen.versioning import deprecated_after

# Remember this adage:
#   There is always some numpy function out there that will
#   solve your data processing problem.
#
# ... at this point, I feel it would be well-served to document
# what functions would be used in numpy, then try to write a
# wrapper over them. In other words, stop reinventing the wheel!


@deprecated_after("0.2024.4")
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
        s = xs[i - 1]
        e = xs[i]
        _ = [y for i, y in enumerate(yy) if s <= xx[i] < e]
        ys.append(np.mean(_))
    xs += (xs[1] - xs[0]) / 2  # put in center of bin
    # print(xs, ys)
    return list(xs)[:-1], ys


@deprecated_after("0.2024.2")
def rejection_sampling(f, samples=100, support=(0, 1)):
    """Performs rejection sampling for a continuous distribution.

    Can be faster than scipy's scipy.NumericalInversePolynomial if
    sampling < 10 million samples, and support is near optimal.
    """
    left, right = support
    assert left < right

    # Find maximum value
    xs = np.linspace(left, right, 10001)
    ys = f(xs)
    assert (ys >= 0).all()  # check is a proper probability distribution
    x0 = xs[np.argmax(ys)]  # generate a guess
    xtol = (right - left) * 1e-5
    (fmax,) = scipy.optimize.fmin(lambda x: -f(x), x0=x0, xtol=xtol, disp=0)  # pyright: ignore[reportAssignmentType], unwilling to fix deprecated function :p

    # Use a default uniform distribution
    result = []
    sample_shortfall = samples
    acceptance_rate = 1
    while len(result) < samples:
        sample_target = min(
            int(np.ceil(sample_shortfall / acceptance_rate * 1.2)), 1000000
        )

        qs = np.random.uniform(left, right, sample_target)
        us = np.random.uniform(0, 1, sample_target)
        rs = qs[us < f(qs) / f(fmax) / 1.01]
        result.extend(rs)

        sample_shortfall -= len(rs)
        acceptance_rate = len(rs) / sample_target
    return result[:samples]
