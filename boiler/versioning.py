#!/usr/bin/env python3
"""Performs versioning of boiler library files.


## How should versioning metadata be stored

Scripts should store metadata about the library version, but within the
script itself to avoid OS-specific metadata conventions (Linux and NT store
metadata using different methods). The way to store this should not be
via injecting into arbitrary docstrings, but to some common identifier.
A straightforward candidate is `import boiler` and their varieties, i.e.

```
import boiler  # some metadata here
```


## Accessing the main script

An import chain, in the most general sense, looks something like:

```
└─ main
    └─ helper
        └─ boiler
            └─ versioning
```

This makes it important to identify which file the `import boiler` line
is located for annotation. And also to annotate internal annotations within
the library itself to prepare for upgrading.

Another important note regarding the `__main__` module (which can be accessed
via `sys.modules`): the `__file__` attribute containing the filepath will
not exist if the main script is an interactive session. This likely means the
versioning functionality may need to be aborted if the 'boiler' library is
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

import os
ll = lambda x: print("\n".join([f"{k}: {x[k]}" for k in x]))
# print(os.getcwd())
# print("Test submodule")


import ast
import sys
main = sys.modules["__main__"]
path = main.__file__

# Using ast.walk
# https://stackoverflow.com/a/9049549


# The first time importing of this module occurs, the module itself
# is frozen and the first versioning string will be read.
def walk_modules(path, depth=0, max_depth=2):
    """Should be a DAG."""
    if depth > max_depth:
        return

    with open(path) as file:
        root = ast.parse(file.read(), path)

    for node in ast.walk(root):
        if isinstance(node, ast.Import):
            module = None
        elif isinstance(node, ast.ImportFrom):
            module = node.module
        else:
            continue

        for n in node.names:
            # Get base module name, two main formats
            # import os as oss    -> (n.name = os, n.asname = oss)
            # from os import walk as walks -> (n.module = os, n.name = walk, n.asname = walks)
            targetmodule = n.name
            if module:
                targetmodule = module
            basemodule = targetmodule.split(".")[0]
            print(basemodule)

            # Get alias of imported thing
            alias = n.name
            if n.asname:
                alias = n.asname

            # end_lineno is generally valid, other than the syntax with
            # import boiler; ... in them. But this is only available from
            # Python 3.8 onwards. See [2]:
            # https://docs.python.org/3.8/library/ast.html#ast.get_source_segment
            #
            # Alternative is to enforce the following form when importing boiler
            # modules, and manually scanning for the end of line using '\\n'.
            #
            # Note that this is valid:
            # from boiler import (  # comment
            #     versioning
            # )
            print("  " * depth, node.lineno, targetmodule, n.name, alias)
            if basemodule == "boiler":
                print(path, node.lineno)
                return (path, node.lineno)
            try:
                next_module = sys.modules[targetmodule]
                result = walk_modules(next_module.__file__, depth+1, max_depth)
                if result is not None:
                    return result  # propagate result back down
            except KeyError:
                print("Ignore invalid search path")
                # print(sorted(sys.modules.keys()))
            except AttributeError:
                print("Not a file, continuing...")
            except UnicodeDecodeError:
                print("Problematic import")



path, lineno = walk_modules(main.__file__)
with open(path, "r+") as file:
    lines = file.readlines()
    print(lines[lineno-1].rstrip("\n"))

# walk_modules("/srv/samba/lightstick/by-scripts/parse_qkdserverlogs/parse_qkdserverlog.py")


# Identify whether library is part of stdlib
# New as of Python 3.10
# https://docs.python.org/3/library/sys.html#sys.stdlib_module_names
# sys.stdlib_module_names
