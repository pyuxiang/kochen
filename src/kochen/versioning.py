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

import ast
import importlib.metadata
import re
import sys
from functools import partial
from typing import Optional, Set

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
RE_VERSION_STRING = re.compile(r"#.*\sv([0-9]+)\.?([0-9]+)?\.?([0-9]+)?")


def _version_str2tuple(version_str):
    major, *remainder = version_str.split(".")
    minor = patch = 0
    if len(remainder) > 0:
        minor = remainder[0]
        if len(remainder) > 1:
            patch = remainder[1].split("+")[0]  # remove local build version
    return tuple(map(int, (major, minor, patch)))


def _version_tuple2str(version_tuple):
    return ".".join(map(str, version_tuple))


# Dynamically retrieve library version information
installed_version_str = importlib.metadata.version(TARGET_LIBRARY)
installed_version = _version_str2tuple(installed_version_str)


def _search_importline(path, depth=0, max_depth=MAX_IMPORTSEARCH_DEPTH):
    """Search for the line reference to import of target library.

    This code works by looking up currently imported modules of the root
    script, and performing a depth-first search. The presence of this line
    is guaranteed via 'sys.modules', since the cascaded library imports will be
    cached, and the target library is likely not used as part of stdlib.

    To limit performance impact of this runtime search, import the library
    in the root script directly. Future possible work in adding an import
    comment for the target library automatically in the root script, possibly
    with the use of the 'isort' module.

    If the root script is an interactive session, this function will not
    trigger (i.e. the latest version of the library will always be used).

    This function ideally will only be triggered once, since the imported
    library will be frozen (so any subsequent import statements will use the
    cached library instead). The use of the `ast` module for searching is
    nominally ideal since the code traversal in running code should be close
    to the manual traversal of the syntax tree, and import statements which
    are part of comments are safely ignored.

    Code adapted from an implementation from StackOverflow [1].

    Max depth needs to be implemented since stdlib is treated like a regular
    library, until the names are frozen from Python 3.10 onwards.

    References:
        [1]: Code source, https://stackoverflow.com/a/9049549
        [2]: AST get_source_segment documentation, https://docs.python.org/3.8/library/ast.html#ast.get_source_segment
        [3]: Standard library module names, https://docs.python.org/3/library/sys.html#sys.stdlib_module_names
    """

    # Terminate search if too deep
    if depth > max_depth:
        return

    # Parse file as AST
    try:
        with open(path) as file:
            root = ast.parse(file.read(), path)
    except (
        UnicodeDecodeError,
        FileNotFoundError,
    ):  # ignore file if cannot decode properly
        return

    for node in ast.walk(root):
        # Process node only if they are import statements
        if isinstance(node, ast.Import):
            module = None
        elif isinstance(node, ast.ImportFrom):
            module = node.module
        else:
            continue

        # Only need to identify the base library of the module
        for n in node.names:
            targetmodule: str = module if module else n.name
            basemodule = targetmodule.split(".")[0]

            # Get line number where the version information is expected,
            # by traversing down concatenated lines, i.e. '\\n'.
            # Note: 'node.end_lineno' is only available from Python 3.8 [2]
            if basemodule == TARGET_LIBRARY:
                # Find importing module name
                name = None
                for name, _module in sys.modules.items():
                    if hasattr(_module, "__file__") and _module.__file__ == path:
                        break
                if name is not None:
                    lineno = node.lineno  # 1-indexed
                    with open(path) as file:
                        lines = file.readlines()
                    while lines[lineno - 1].endswith("\\\n"):
                        lineno += 1
                    return name, path, lineno

            # Cache modules
            if targetmodule in SEARCHED_MODULES:
                continue
            else:
                SEARCHED_MODULES.add(targetmodule)

            # Ignore modules that have not been imported, or if not a file,
            # e.g. stdlib or C extensions
            try:
                next_module = sys.modules[targetmodule]
                target = next_module.__file__
            except (KeyError, AttributeError):
                continue

            # Ignore modules without filepath
            if target is None:
                continue

            # Continue traversal and terminate immediately upon completion
            result = _search_importline(target, depth + 1, max_depth)
            if result is not None:
                return result


def _parse_importline(line, installed_version):
    """Extracts requested version from the line."""
    if "#" not in line or (result := RE_VERSION_STRING.search(line)) is None:
        return installed_version

    # Force lowest minor/patch for most conservative compatibility
    major, minor, patch = result.groups()
    if minor is None:
        minor = 0
    if patch is None:
        patch = 0
    requested_version = tuple(map(int, (major, minor, patch)))
    return requested_version


# Execute the search for the import line
def _get_requested_version():
    """Returns the version requested by the import.

    Works by starting the search from the main module run by the user,
    and performing a depth-first search using '_search_importline'.

    TODO:
        Update file with the current library version.
    """
    # For Python <3.13, the REPL script does not belong to any package
    try:
        main_module = sys.modules["__main__"]
        path_main = main_module.__file__
    except (KeyError, AttributeError):  # ignore interactive sessions
        return installed_version

    # For Python >=3.13, the REPL is assigned to package '_pyrepl' and __file__
    # is no longer unset.
    if main_module.__package__ == "_pyrepl":
        return installed_version

    # Abandon if no import line was found (can happen if the search depth
    # is too shallow, in which case we try to search a bit deeper each time)
    # We stop when we cannot find it with a depth of 3.
    # TODO(2024-05-06):
    #   Optimize this by ignoring known built-in and commonly-used libraries.
    for max_depth in range(4):
        SEARCHED_MODULES.clear()
        result = _search_importline(path_main, max_depth=max_depth)
        if result is not None:
            break
    else:
        logger.warning(f"'{TARGET_LIBRARY}' could not be found")
        return installed_version

    # Import line found: read from file
    module_name, path, lineno = result
    with open(path, "r+") as file:
        lines = file.readlines()
        targetline = lines[lineno - 1].rstrip("\n")

    # Feedback to user importing results
    # The stated version number is used regardless, for use in editable
    # package installations for testing new features (rather than
    # falling back to the installed version).
    requested_version = _parse_importline(targetline, installed_version)
    requested_version_str = _version_tuple2str(requested_version)
    if requested_version > installed_version:
        logger.warning(
            "Requested version is '%s', but '%s' is installed.",
            requested_version_str,
            installed_version_str,
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


requested_version = _get_requested_version()
__kochen_requested_version = requested_version


################
#  VERSIONING  #
################

# Stores all function references
# TODO: See how to reduce memory usage
__kochen_f_cache = {}  # store latest compatible version on reference
__kochen_f_refmap = {}


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
