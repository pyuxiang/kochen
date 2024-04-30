# __all__ explanation: https://stackoverflow.com/a/35710527

# from pathlib import Path as _Path

# _cwd = _Path(__file__).parent.glob("*.py")
# __all__ = [fn.stem for fn in _cwd if fn.stem != "__init__"]

# import kochen.devices


"""
Sets whatever is exposed in the `kochen` namespace.
"""

"""
from kochen.v1 import pathutil
from kochen.v2 import pathutil


# for subpackage_name in pathlib.Path().iterdir():
# from pathlib import Path as _Path
# _cwd = _Path(__file__, "..", "v2").glob("*.py")
# __all__ = [fn.stem for fn in _cwd if fn.stem != "__init__"]
# print(__all__)

# https://github.com/pyuxiang/gds-toolbox/blob/master/toolbox/parts/common/__init__.py
"""

# Trigger versioning process
import kochen.versioning

__version__ = kochen.versioning.installed_version
