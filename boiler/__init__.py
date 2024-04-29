# __all__ explanation: https://stackoverflow.com/a/35710527

# from pathlib import Path as _Path

# _cwd = _Path(__file__).parent.glob("*.py")
# __all__ = [fn.stem for fn in _cwd if fn.stem != "__init__"]

# import scribbles.devices


"""
Sets whatever is exposed in the `scribbles` namespace.
"""

"""
from scribbles.v1 import pathutil
from scribbles.v2 import pathutil


# for subpackage_name in pathlib.Path().iterdir():
# from pathlib import Path as _Path
# _cwd = _Path(__file__, "..", "v2").glob("*.py")
# __all__ = [fn.stem for fn in _cwd if fn.stem != "__init__"]
# print(__all__)

# https://github.com/pyuxiang/gds-toolbox/blob/master/toolbox/parts/common/__init__.py
"""

import sys

# Backward compatibility for importlib.metadata
pyversion = f"{sys.version_info.major}.{sys.version_info.minor}"
if pyversion < "3.8":
    import importlib_metadata as imdata
else:
    import importlib.metadata as imdata

# Dynamically retrieve library version information
__version__ = imdata.version("scribbles")