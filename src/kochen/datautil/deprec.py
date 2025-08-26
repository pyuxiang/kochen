import datetime as dt

import numpy as np

from kochen.versioning import deprecated


@deprecated("0.2025.4")
def data_decoder(dct):
    """Usage: json.load(..., object_hook=datetime_decoder)"""

    def _str2dt(x):
        return dt.datetime.strptime(x, "%Y%m%d_%H%M%S.%f")

    if "_dt" in dct:
        return _str2dt(dct["_dt"])
    if "_np" in dct:
        return np.array(dct["_np"])
    if "_dt_np" in dct:
        return np.array(list(map(_str2dt, dct["_dt_np"])))
    return dct
