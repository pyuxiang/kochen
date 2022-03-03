"""
Sets whatever is exposed in the `boiler` namespace.
"""

from boiler.v1 import pathutil
from boiler.v2 import pathutil


# for subpackage_name in pathlib.Path().iterdir():
# from pathlib import Path as _Path
# _cwd = _Path(__file__, "..", "v2").glob("*.py")
# __all__ = [fn.stem for fn in _cwd if fn.stem != "__init__"]
# print(__all__)

# https://github.com/pyuxiang/gds-toolbox/blob/master/toolbox/parts/common/__init__.py