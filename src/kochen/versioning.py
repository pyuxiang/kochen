#!/usr/bin/env python3
"""Performs versioning of boiler library files.


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


Changelog:
    2023-12-01 Justin: Init design document

References:
    [1]: https://stackoverflow.com/questions/53564301/insert-docstring-attributes-in-a-python-file
"""

import ast
import re
import sys

TARGET_LIBRARY = "kochen"
MAX_IMPORTSEARCH_DEPTH = 3
SEARCHED_MODULES = set()  # cache visited modules, since imports are also a DAG
RE_VERSION_STRING = re.compile(r"#.*\sv([0-9]+)\.([0-9]+)")

def _search_importline(path, depth=0, max_depth=MAX_IMPORTSEARCH_DEPTH):
    """Search for first line reference to import of target library.

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
    except UnicodeDecodeError:  # ignore file if cannot decode properly
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
            targetmodule = module if module else n.name
            basemodule = targetmodule.split(".")[0]

            # Get line number where the version information is expected,
            # by traversing down concatenated lines, i.e. '\\n'.
            # Note: 'node.end_lineno' is only available from Python 3.8 [2]
            if basemodule == TARGET_LIBRARY:
                # Find importing module name
                for name, module in sys.modules.items():
                    if hasattr(module, "__file__") and module.__file__ == path:
                        break
                lineno = node.lineno  # 1-indexed
                with open(path) as file:
                    lines = file.readlines()
                while lines[lineno-1].endswith("\\\n"):
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

            # Continue traversal and terminate immediately upon completion
            result = _search_importline(target, depth+1, max_depth)
            if result is not None:
                return result


try:
    path_main = sys.modules["__main__"].__file__
    name, path, lineno = _search_importline(path_main)

    # Open file as writable
    with open(path, "r+") as file:
        lines = file.readlines()
        targetline = lines[lineno-1].rstrip("\n")

        # Check for version string
        VERSION_FOUND = False
        if "#" in targetline:
            result = RE_VERSION_STRING.search(targetline)
            if result:
                major, minor = result.groups()
                print(
                    f"'{TARGET_LIBRARY}' loaded (v{major}.{minor}) "
                    f"from {name}:{lineno}"
                )
                VERSION_FOUND = True

        if not VERSION_FOUND:
            version = sys.modules[TARGET_LIBRARY].__version__
            major, minor, *_ = version.split(".")
            print(
                f"'{TARGET_LIBRARY}' loaded (latest:v{major}.{minor}) "
                f"from {name}:{lineno}"
            )

except (KeyError, AttributeError):  # ignore interactive sessions
    pass
