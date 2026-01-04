#!/usr/bin/env python3
"""Performs versioning of library submodule functions.

See `docs/versioning.md` for a blurb on how this works.

Changelog:
    2023-12-01 Justin: Init design document
    2026-01-02 Justin: Replace @version with @deprecated_after
"""

import importlib.metadata
import inspect
import re
import readline
import sys
from typing import Optional, Dict, Tuple, Callable

# To eventually include when doing arbitrary version lookups:
# from sortedcontainers import SortedDict  # for O(logN) bisection methods
from typing_extensions import TypeAlias

from kochen.logging import get_logger

__all__ = [
    "installed_version",  # actual installed library version
    "requested_version",  # library version requested by user at import
    "deprecated_after",  # marking functions for upcoming deprecation
]

logger = get_logger(__name__, level="info")

Version: TypeAlias = Tuple[int, int, int]
FuncVersion: TypeAlias = Tuple[Callable, Version]
Version2Func: TypeAlias = Dict[Version, Callable]


#####################
#  VERSION PINNING  #
#####################

RE_VERSION_IMPORT = re.compile(
    r"""
    import\s+  # import statement
    kochen[._\w\d]*\s*  # module or submodule name
    (?:as\s*[_\w\d]*\s*)?  # alias
    \#.*?  # non-greedy match comment text
    v([0-9]+)\.?([0-9]+)?\.?([0-9]+)?  # e.g. 'v83' / 'v83.104' / 'v83.104.92'
    """,
    re.VERBOSE,
)
RE_VERSION_IMPORTFROM = re.compile(
    r"""
    from\s+  # from...import statement
    kochen[._\w\d]*\s+  # module or submodule name
    import\s+
    [_\w\d\s,()*]*  # see tests for allowable syntax
    \#.*?  # non-greedy match comment text
    v([0-9]+)\.?([0-9]+)?\.?([0-9]+)?  # e.g. 'v83' / 'v83.104' / 'v83.104.92'
    """,
    re.VERBOSE,
)
RE_VERSION_LIB = re.compile(
    r"""
    ^([0-9]+)\.?([0-9]+)?\.?([0-9]+)?
    """,
    re.VERBOSE,
)


def _version_str2tuple(version_str: str) -> Version:
    """Extract version string and parse as a version tuple.

    'version_str' must follow exactly the format: "([0-9]+).?([0-9]+)?.?([0-9]+)?".
    This will be used to parse version strings specified in the library, as
    well as deprecated functions.

    This is not the actual function used for import line parsing: for that,
    see '_parse_version_pin()'.

    Examples:
        >>> _version_str2tuple("10")
        (10, 0, 0)
        >>> _version_str2tuple("10.20")
        (10, 20, 0)
        >>> _version_str2tuple("10.20.30")
        (10, 20, 30)
        >>> _version_str2tuple("10.20.30.post4+20250102")
        (10, 20, 30)

    Note:
        Old versioning system used to rely on build string to convey
        installation date, e.g. v0.1.2+20240921. This has been deprecated
        in favor of a simple (major, minor, patch) for PyPI-compatibility.

    TODO:
        This function may eventually require a change to convert "10" to
        "10.9999.9999" instead, to mark as a version cap. To review after
        implementing '@deprecated'.
    """
    result = RE_VERSION_LIB.search(version_str)
    assert result is not None, "Error parsing library version: check git tag format!"
    version = tuple((0 if n is None else int(n)) for n in result.groups())
    assert len(version) == 3
    return version


def _version_tuple2str(version_tuple: Version) -> str:
    """Convert a valid version 3-tuple into its string equivalent.

    Examples:
        >>> _version_tuple2str((1, 2, 3))
        '1.2.3'
    """
    return ".".join(map(str, version_tuple))


def _parse_version_pin(line: str) -> Optional[Version]:
    """Extracts requested version from the library import line."""
    idx_comment = line.find("#")
    idx_lib = line.find("kochen")
    if idx_comment == -1 or idx_lib == -1:
        return None

    # Exclude cases like: "import logging  # import kochen  # v0.1.2",
    if idx_comment < idx_lib:
        return None

    # Search for version pin
    if (result := RE_VERSION_IMPORT.search(line)) is None:
        if (_result := RE_VERSION_IMPORTFROM.search(line)) is None:
            return None
        result = _result

    # Force lowest minor/patch for most conservative compatibility
    # i.e. major.minor.patch
    version = tuple((0 if n is None else int(n)) for n in result.groups())
    assert len(version) == 3
    return version


# Execute the search for the import line
def _get_requested_version():
    """Returns the version requested by the import.

    Works by querying the current call stack to search for the relevant
    library import call. This works for all file-based imports, as well
    as REPLs which cache import lines in their history files.

    Notes:
        There is a potential of pinning the version wrongly from a previous
        history file, with the following reproduction steps:

          1. Python REPL is activated.
          2. 'import kochen  # [VERSION_PIN]' is called.
          3. REPL is exited without another command, e.g. via Ctrl-D EOF.
          4. 'import kochen' is passed into new REPL via stdin, e.g.
             'echo "import kochen" | python -i'

        This arises from the use of last readline cached line from the
        previous session. In practice the chances of this happening is slim,
        especially since step 4 is very unusual, and we would still like
        to preserve version pinning functionality for user REPL prototyping.

    See documentation at 'kochen/docs/versioning.md'.
    """
    # Read from local history for CPython REPLs
    idx = readline.get_current_history_length()
    if idx > 0:
        line: Optional[str] = readline.get_history_item(idx)
        if line is not None:
            version: Optional[Version] = _parse_version_pin(line)
            if version is not None:
                return version

    # Look for file-based library import line
    stack = inspect.stack(context=1)
    try:
        for frame in reversed(stack):
            context = frame.code_context
            if context is None:
                continue

            (line,) = context  # since only 1 line of context requested
            version: Optional[Version] = _parse_version_pin(line)
            if version is not None:
                return version

    finally:
        # Remove references to frames to avoid reference cycles,
        # see <https://docs.python.org/3/library/inspect.html#inspect.FrameInfo>
        for frame in stack:
            del frame

    return installed_version


# Dynamically retrieve version of currently installed library
installed_version = _version_str2tuple(importlib.metadata.version("kochen"))
requested_version = _get_requested_version()


#####################
#  VERSION MARKING  #
#####################

_track_versions: Dict[Optional[str], Dict[str, Version]] = {}


def deprecated_after(version_str: str, namespace: Optional[str] = None):
    """Decorator to mark function as deprecated."""
    # Convert to version tuple
    version_tuple = _version_str2tuple(version_str)

    def helper(f: Callable):
        # Cache function in loader for dynamic calls
        fname: str = f.__name__  # TODO: Check str assumption
        module: str = f.__module__

        # Identify namespace where function belongs to
        _namespace = namespace
        if _namespace is None:
            _namespace = module
            if (idx := module.rfind(".")) != -1:  # up one level if nested
                _namespace = module[:idx]

        # Cache earliest compatible function
        if version_tuple >= requested_version:  # not yet deprecated
            nmap = _track_versions.setdefault(_namespace, {})
            if (fname not in nmap) or (version_tuple < nmap[fname]):
                nmap[fname] = version_tuple
                setattr(sys.modules[_namespace], fname, f)

        # Store versioned function for explicit lookup
        # __kochen_f_refmap: Dict[Optional[str], Dict[str, Version2Func]] = {}
        # nmap = __kochen_f_refmap.setdefault(_namespace, {})
        # fmap = nmap.setdefault(fname, SortedDict())
        # fmap[version_tuple] = f

        return f

    return helper


def _search_versioned(fname, version, namespace=None):
    """Returns desired function cached."""
    raise NotImplementedError
    # Check if function already cached
    __kochen_f_cache: Dict[
        Optional[str], Dict[str, FuncVersion]
    ] = {}  # store latest compatible version on reference
    if fname in __kochen_f_cache:
        return __kochen_f_cache[fname]

    # Search for function
    __kochen_f_refmap = {}
    if (ns := __kochen_f_refmap.get(namespace)) is None or (
        fmap := ns.get(fname)
    ) is None:
        raise AttributeError(f"'{fname}' is not versioned/does not exist.")

    # TODO: Pull relevant version
    # 'fmap' is effectively a set of version numbers
    idx = fmap.bisect_right(version) - 1
    found_version, f = fmap.peekitem(idx)
    __kochen_f_cache[fname] = f
    return f
