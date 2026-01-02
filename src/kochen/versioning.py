#!/usr/bin/env python3
"""Performs versioning of kochen library files.

## How to use it

At the top of the script:

```
from kochen.versioning import get_namespace_versioning
version, version_cleanup, __getattr__ = \
    get_namespace_versioning(__name__, globals())
```

At relevant functions:

```
@version("0.2024.2")
def ...
```

At end of the script:

```
version_cleanup()
```



## How should versioning metadata be stored

Scripts should store metadata about the library version, but within the
script itself to avoid OS-specific metadata conventions (Linux and NT store
metadata using different methods). The way to store this should not be
via injecting into arbitrary docstrings, but to some common identifier.
A straightforward candidate is `import kochen` and their varieties, i.e.

```
import kochen  # some metadata here
```


## Accessing the main script

An import chain, in the most general sense, looks something like:

```
└─ main
    └─ helper
        └─ kochen
            └─ versioning
```

This makes it important to identify which file the `import kochen` line
is located for annotation. And also to annotate internal annotations within
the library itself to prepare for upgrading.

Another important note regarding the `__main__` module (which can be accessed
via `sys.modules`): the `__file__` attribute containing the filepath will
not exist if the main script is an interactive session. This likely means the
versioning functionality may need to be aborted if the 'kochen' library is
directly imported from the interactive session.

Some useful tools: `os.getcwd()`, `sys.modules['__main__'].__file__',


## Strategies for modifying files

Using `ast` as per [1], to build the abstract syntax tree of the file and
modifying the docstring, is possible. Main downside is in that comments will
be lost, since the parser will immediately discard comments. Useful mainly
for programmatically generated modules and functions instead. If keen on this
route, Cython's `unparse` (or `ast.unparse` as per Python 3.9) is useful for
recompiling the ast before writing into a file.


## Strategies for versioning

Got some inspiration from the way the 'os' library was written, i.e. exposing the
functions dynamically at compile time using the `__all__` mechanism.



## Terminology

    * 'requested_version':
        Set by import line, which determines the minimum supported version.
    * 'installed_version':
        Determined by currently installed version.
    * 'function_version':
        Set by @version decorator.

|            |    F <= I ?    |     F > I ?     |
|------------|----------------|-----------------|
| has F <= R |       OK       |    impossible   |
| only F > R | update request |    impossible   |

Note that F <= I is always true, since functions referenced in scripts will not
have a version pinned. See if this is needed in the future.

    * I == R: No issues
    * I > R: Search for latest F < R (< I)
    * I < R: Warn script user, then search for latest F < I (< R)


Changelog:
    2023-12-01 Justin: Init design document

References:
    [1]: https://stackoverflow.com/questions/53564301/insert-docstring-attributes-in-a-python-file

TODO:
    Fix import error when non-versioned and versioned functions coexists.
"""

import importlib.metadata
import inspect
import re
import readline
from functools import partial
from typing import Optional, Set, Dict, Tuple, Callable
from typing_extensions import TypeAlias

from sortedcontainers import SortedDict  # for O(logN) bisection methods

from kochen.logging import get_logger

__all__ = [
    "installed_version",
    "requested_version",  # library versioning
    "version",
    "search",
    "get_namespace_versioning",  # function versioning
]

logger = get_logger(__name__, level="info")

TARGET_LIBRARY = "kochen"
MAX_IMPORTSEARCH_DEPTH = 3
SEARCHED_MODULES: Set[str] = (
    set()
)  # cache visited modules, since imports are also a DAG
RE_VERSION_IMPORT = re.compile(
    r"""
    kochen[._\d\w]*\s*  # module or submodule name
    \#.*?  # non-greedy match comment text
    v([0-9]+)\.?([0-9]+)?\.?([0-9]+)?  # e.g. 'v83' / 'v83.104' / 'v83.104.92'
    """,
    re.VERBOSE,
)
RE_VERSION_IMPORTFROM = re.compile(
    r"""
    from\s+  # from...import statement
    kochen[.\d\w]*\s+  # module or submodule name
    import\s+
    [,_\d\w\s]*  # includes e.g. 'versioning as v2, blah'
    \#.*?  # non-greedy match comment text
    v([0-9]+)\.?([0-9]+)?\.?([0-9]+)?  # e.g. 'v83' / 'v83.104' / 'v83.104.92'
    """,
    re.VERBOSE,
)

Version: TypeAlias = Tuple[int, int, int]
FuncVersion: TypeAlias = Tuple[Callable, Version]
Version2Func: TypeAlias = Dict[Version, Callable]


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
    major, *remainder = version_str.split(".")
    minor = patch = 0
    if len(remainder) > 0:
        minor = remainder[0]
        if len(remainder) > 1:
            patch = remainder[1]
    return (int(major), int(minor), int(patch))


def _version_tuple2str(version_tuple: Version) -> str:
    """Convert a valid version 3-tuple into its string equivalent.

    Examples:
        >>> _version_tuple2str((1, 2, 3))
        '1.2.3'
    """
    return ".".join(map(str, version_tuple))


# Dynamically retrieve version of currently installed library
_installed_version_str = importlib.metadata.version(TARGET_LIBRARY)
installed_version = _version_str2tuple(_installed_version_str)


def _parse_version_pin(line: str) -> Optional[Version]:
    """Extracts requested version from the library import line."""
    if "#" not in line:
        return None

    if (result := RE_VERSION_IMPORT.search(line)) is None and (
        result2 := RE_VERSION_IMPORTFROM.search(line)
    ) is None:
        return None
    if result is None:
        result = result2  # pyright: ignore[reportPossiblyUnboundVariable]

    # Force lowest minor/patch for most conservative compatibility
    major, minor, patch = result.groups()
    if minor is None:
        minor = 0
    if patch is None:
        patch = 0
    requested_version = (int(major), int(minor), int(patch))
    return requested_version


# Execute the search for the import line
def _get_requested_version():
    """Returns the version requested by the import.

    Works by querying the current call stack to search for the relevant
    library import call. This works for all file-based imports, as well
    as selected REPLs which store the import line directly in the stack.

    Known REPLs where this is known to not work are:

    Known to work are: IPython.

    See documentation at 'kochen/docs/versioning.md'.
    """
    # Read from local history for REPLs
    idx = readline.get_current_history_length()
    line = readline.get_history_item(idx)
    if line is not None:
        version: Optional[Version] = _parse_version_pin(line)
        if version is not None:
            return version

    # Look for library import line
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

    """
    logger.warning(f"'{TARGET_LIBRARY}' could not be found")

    # Feedback to user importing results
    requested_version = _parse_version_pin(targetline)
    requested_version_str = _version_tuple2str(requested_version)
    if requested_version > installed_version:
        logger.warning(
            "Requested version is '%s', but '%s' is installed.",
            requested_version_str,
            _installed_version_str,
        )

    currency = ""
    if requested_version == installed_version:
        currency = "current:"
    elif requested_version > installed_version:
        currency = "future:"
    logger.debug(
        f"'{TARGET_LIBRARY}' loaded ({currency}v{requested_version_str}) "
        f"from {module_name}:{lineno}"
    )
    return requested_version
    """


requested_version = _get_requested_version()
__kochen_requested_version = requested_version


################
#  VERSIONING  #
################

# Stores all function references
# TODO: See how to reduce memory usage
__kochen_f_cache: Dict[
    Optional[str], Dict[str, FuncVersion]
] = {}  # store latest compatible version on reference
__kochen_f_refmap: Dict[Optional[str], Dict[str, Version2Func]] = {}


def version(version_str: str, namespace: Optional[str] = None):
    """Decorator for indicating version of a function.

    When the function is first called, the function is cached within
    a global cacher.

    For internal use within the 'kochen' library only.


    Example:
        >>> from kochen.versioning import version
        >>> @version("0.2024.1")
        ... def f():
        ...     return "hello world!"

    TODO:
        See how to extend this to other libraries.
    """
    # Convert to version tuple
    version_tuple = _version_str2tuple(version_str)

    def helper(f):
        # Cache function in loader for dynamic calls
        fname = f.__name__

        # Store all versioned functions
        ns = __kochen_f_refmap.setdefault(namespace, {})
        fmap = ns.setdefault(fname, SortedDict())
        fmap[version_tuple] = f

        # Cache latest compatible function
        if version_tuple <= __kochen_requested_version:
            ns = __kochen_f_cache.setdefault(namespace, {})
            _, prev_ver = ns.setdefault(fname, (f, version_tuple))
            if version_tuple > prev_ver:
                ns[fname] = (f, version_tuple)  # override with later

        return f

    return helper


def deprecated(version_str: str, namespace: Optional[str] = None):
    """Decorator for indicating version of a function.

    When the function is first called, the function is cached within
    a global cacher.

    For internal use within the 'kochen' library only.

    Example:
        >>> from kochen.versioning import version
        >>> @version("0.2024.1")
        ... def f():
        ...     return "hello world!"

    TODO:
        See how to extend this to other libraries.

        Problem is:
            1. Need cumbersome method of deprecation + cumbersome pinning of functions
               to current library.
            2. Need to override __getattr__. Not very friendly...
    """
    # Convert to version tuple
    version_tuple = _version_str2tuple(version_str)

    def helper(f: Callable):
        # Cache function in loader for dynamic calls
        fname: str = f.__name__  # TODO: Check str assumption
        module: str = f.__module__

        # Special case (dumping ground for deprecated functions)
        if module.endswith(".deprec"):
            module = module[:-7]  # remove suffix

        # Store all versioned functions
        ns = __kochen_f_refmap.setdefault(namespace, {})
        fmap = ns.setdefault(fname, SortedDict())
        fmap[version_tuple] = f

        # Cache latest compatible function
        if version_tuple <= __kochen_requested_version:
            ns = __kochen_f_cache.setdefault(namespace, {})
            _, prev_ver = ns.setdefault(fname, (f, version_tuple))
            if version_tuple > prev_ver:
                ns[fname] = (f, version_tuple)  # override with later

        return f

    return helper


# Cache reference to 'version' internally within 'versioning.py'
# This assignment necessary to avoid conflicts with global 'version'
# when submodules define it as well
__kochen_version = version


def mock_version(version_str, namespace=None):
    """Replacement to quickly disable versioning."""

    def helper(f):
        return f

    return helper


def get_namespace_version(namespace):
    """Returns 'version' with a fixed namespace, for module-wide versioning."""
    return partial(__kochen_version, namespace=namespace)


def cleanup(globals_ref, namespace=None):
    """Clears function references from namespace.

    Typically used at the end of the module using the versioning system.

    'module.__getattr__' will only call if the associated attribute is
    missing from the definition in the module, i.e.

        del test_identitytest

    To avoid burdening the user with manual cleanup, this function does the
    same thing, by looking up function names that have been stored by 'version'
    and popping these off the module's references. The call is replaced by,

        cleanup(globals())

    Note the 'globals_ref' needs to be passed because the scope of globals is restricted to the module within which it is defined, i.e. using 'globals()'
    within 'versioning.cleanup' will return the globals in 'versioning'.
    """
    if globals_ref is None:
        return
    if (ns := __kochen_f_refmap.get(namespace)) is None:
        return
    for fname in ns.keys():
        if fname in globals_ref:
            globals_ref.pop(fname)
    return


__kochen_cleanup = cleanup


def search(fname, namespace=None):
    """Returns latest compatible function."""
    if (ns := __kochen_f_cache.get(namespace)) is None or (
        result := ns.get(fname)
    ) is None:
        raise AttributeError(f"'{fname}' is not versioned/does not exist.")
    f, version_tuple = result
    return f


__kochen_search = search


def get_namespace_search(namespace):
    return partial(__kochen_search, namespace=namespace)


def get_namespace_versioning(namespace, globals_ref=None):
    """Convenience function.

    Example:

        #!/usr/bin/env python3
        from kochen.versioning import get_namespace_versioning
        version, version_cleanup, __getattr__ = \
            get_namespace_versioning(__name__, globals())

        @version("0.2024.1")
        def f(value):
            return value

        version_cleanup()
    """
    version = get_namespace_version(namespace)
    cleanup = partial(__kochen_cleanup, globals_ref, namespace=namespace)
    search = get_namespace_search(namespace)
    return version, cleanup, search


def _search_versioned(fname, version, namespace=None):
    """Returns desired function cached."""
    raise NotImplementedError
    # Check if function already cached
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
