import numpy as np

from kochen.versioning import deprecated_after


# Older functionality without 'initial' parameter built-in, and with *args param
@deprecated_after("0.2026.8")
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
