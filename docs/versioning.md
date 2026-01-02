# Versioning

## Control flow trace

Here is a simplified control flow chart when Python is first run, and then with REPL activated. This is obtained by tracing the source.
Relevant files for Python 3.8:

* [Modules/main.c](https://github.com/python/cpython/blob/39b2f82717a69dde7212bc39b673b0f55c99e6a3/Modules/main.c)
* [Python/pythonrun.c](https://github.com/python/cpython/blob/39b2f82717a69dde7212bc39b673b0f55c99e6a3/Python/pythonrun.c)
* [Parser/parsetok.c](https://github.com/python/cpython/blob/39b2f82717a69dde7212bc39b673b0f55c99e6a3/Parser/parsetok.c)

```
(Modules/main.c) Py_RunMain
└ pymain_run_python
  ├ pymain_import_readline  # imports GNU readline library (or abstraction of it)
  ├ pymain_run_command      # for example; specialization depending on entry type (e.g. command, module, stdin)
  │ └ (Python/pythonrun.c) PyRun_SimpleStringFlags          # run string with compiler flags + init main and globals/locals
  │   └ PyRun_StringFlags                                   # + arena malloc
  │     ├ PyParser_ASTFromStringObject                      # string -> module
  │     │ ├ (Parser/parsetok.c) PyParser_ParseStringObject
  │     │ │ ├ PySys_Audit                                   # raise 'compile' audit event
  │     │ │ ├ PyTokenizer_FromUTF8                          # string -> tokens
  │     │ │ └ parsetok                                      # tokens -> node
  │     │ └ PyAST_FromNodeObject                            # node -> module
  │     └ run_mod
  │       ├ PyAST_CompileObject                             # module -> code object
  │       ├ PySys_Audit                                     # raise 'exec' audit event (run bytecode)
  │       └ run_eval_code_obj
  │         └ (Python/ceval.c) PyEval_EvalCode              # frame created here
  │
  └ pymain_repl
    └ (Python/pythonrun.c) PyRun_AnyFileFlags  # with <stdin> as file
      └ PyRun_AnyFileExFlags
        └ PyRun_InteractiveLoopFlags           # REPL starts here, if requested
          └ PyRun_InteractiveOneObjectEx       # line execution
            ├ PyParser_ASTFromFileObject       # file -> module
            └ run_mod
```

Firstly, for Python <3.13, the C-based [readline GNU library](https://cgit.git.savannah.gnu.org/cgit/readline.git/tree/history.h)
is used as backend to store history (before compiling REPL command into bytecode).
This means the only sensible way to read the actual code context is to use the `readline` interface provided as a
[builtin library](https://docs.python.org/3.8/library/readline.html#module-readline) (see also the
[source](https://github.com/python/cpython/blob/3.8/Modules/readline.c#L693)).

Secondly, for Python >=3.13, the REPL has a fancier interface based on PyPy's REPL (see [PEP-762](https://peps.python.org/pep-0762/)),
and is stored in the new [`_pyrepl` package](https://github.com/python/cpython/blob/3.13/Lib/_pyrepl), together with a
Python-based [`readline`](https://github.com/python/cpython/blob/3.13/Lib/_pyrepl/readline.py) wrapper.
This makes accessing the history more consistent across different backends.

Thirdly, unless Python was injected with [auditing hooks](https://docs.python.org/3/library/sys.html#auditing) prior to execution
(via `sys.addaudithook((event_name: str, args: tuple) -> Any)`), there doesn't seem to be a method to retrieve
the original source code supplied via stdin during the initial code call. This is because any source is immediately
compiled into a code object before being passed for frame creation, and reads from stdin are not duplicated
outside of the `readline` interface. This means that version pinning comments cannot be retrieved.

### Call stack frames

This is the call stack printed during the version request, e.g.
in 'kochen.versioning._get_requested_version()'.

```
┌─────────────────────────────────────────────┐
│ Frame(                                      │
│   filename='.../src/kochen/versioning.py',  │
│   function='_get_requested_version',        │
│   code_context=['    inspect.stack()\n'],   │
│ )                                           │
├─────────────────────────────────────────────┤
│ ...                                         │
├─────────────────────────────────────────────┤
│ Frame(                                      │
│   filename='<frozen importlib._bootstrap>', │
│   function='_find_and_load',                │
│   code_context=None,                        │
│ )                                           │
├─────────────────────────────────────────────┤
│ Frame(                                      │
│   filename='<stdin>-0',                     │
│   function=None,                            │
│   code_context=None,                        │
│ )                                           │
└─────────────────────────────────────────────┘
```

We can observe the comments stripped from the executing code object, by
inspecting the base of the call stack and noting the boundary lengths referencing
the source code does not include whitespace and comments.

### IPython notes

The `readline` interface is inactive in IPython, which opts for its own command history via `<module '__main__'>.In`.
This in principle can be used to obtain the version pin...

```python
# Edge case: IPython via "<module '__main__'>.In"
main_module = sys.modules["__main__"]
if hasattr(main_module, "In"):
    line: str = main_module.In[-1]
    version = _parse_version_pin(line)
    if version is not None:
        return version
```

...although in practice the stack trace already holds the code context, so this method is not needed.

### CPython notes

REPL can be checked as follows:

```python
try:
    main_module = sys.modules["__main__"]
    path_main = main_module.__file__
except (KeyError, AttributeError):
    return  # REPL, CPython <3.13

if main_module.__package__ == "_pyrepl":
    return  # REPL, CPython >=3.13

return  # no REPL
```

## Version pinning syntax

See [here](https://docs.python.org/3/reference/grammar.html) for the full import statement grammar,
with the import statements reproduced below. Valid name identifiers can be found in
[here](https://docs.python.org/3/reference/lexical_analysis.html#names-identifiers-and-keywords),
specifically `[_\w][_\w\d]*` (non-ASCII identifiers are technically also supported as per
[PEP-3131](https://peps.python.org/pep-3131/),
but will require more complex regex parsing; unicode identifiers can easily be separately assigned in
follow-up reassignments).

<details>
<summary>Import statement grammar</summary>

```
import_stmt:
    | import_name
    | import_from

import_name:
    | 'import' dotted_as_names
import_from:
    | 'from' ('.' | '...')* dotted_name 'import' import_from_targets
    | 'from' ('.' | '...')+ 'import' import_from_targets
import_from_targets:
    | '(' import_from_as_names [','] ')'
    | import_from_as_names !','
    | '*'
import_from_as_names:
    | ','.import_from_as_name+
import_from_as_name:
    | NAME ['as' NAME ]

dotted_as_names:
    | ','.dotted_as_name+
dotted_as_name:
    | dotted_name ['as' NAME ]
dotted_name:
    | dotted_name '.' NAME
    | NAME
```

All of the above is supported during version pinning,
with the exception of relative "import_from" (starting with a dot),
since this library is not intended to be addressed as a local library.

</details>

The expected syntax for imports are:

```python
import kochen  # v0.1.2
import kochen as k  # v0.1.2
import kochen.versioning  # v0.1.2
from kochen.versioning import *  # v0.1.2
from kochen import versioning  # v0.1.2
from kochen import (  # v0.1.2
    versioning,
)
```

Note that the version pin must be located on the same line as the library being referenced.
This is because the code context provided during stack lookup does not consider the AST,
but simply the first line of the executing statement.
These version pinning syntaxes are thus not accommodated for to reduce pinning complexity
(not to mention some of these are weird rules to follow, with the exception of the last one):

```python
import \
    kochen as k  # v0.1.2; NO PINNING
from kochen \
    import versioning  # v0.1.2; NO PINNING
from kochen import (
    versioning,
)  # v0.1.2; NO PINNING
```

We also disallow multi-library imports on the same line because of the potential confusion.
Version pinning is also comment sensitive.

```python
import kochen, logging  # v0.1.2; NO PINNING
import logging  # import kochen  # v0.1.2; NO PINNING
```

Note also that line continuations cannot precede a comment.


## Deprecated method

Old method worked by performing AST recursive depth-first search,
starting from the Python entrypoint (i.e. retrieved via
`sys.modules["__main__"]`) using '_search_importline()'. This is
obviously very inefficient, and will break under edge cases, since
it is not known a-priori how deep the library import statement is
nested. Documenting it here for archival purposes:

* Searching code works by looking up currently imported modules of the root script
  * Works because cascaded library imports are cached immediately after import
  * Depth-first search with function signature `_search_importline(path, depth=0, max_depth=MAX_DEPTH)`
* Traversal via the Abstract Syntax Tree, generated using the `ast` module
  * Import-type node check with `isinstance(node, (ast.Import, ast.ImportFrom))`
  * Line number can then be used to retrieve the source line directly

Some relevant references:

1. AST traversal adapted from source, <https://stackoverflow.com/a/9049549>
2. AST get_source_segment documentation, <https://docs.python.org/3.8/library/ast.html#ast.get_source_segment>
3. Standard library module names, <https://docs.python.org/3/library/sys.html#sys.stdlib_module_names>

Source code for this style of version pin lookup is in `kochen:v0.2025.15`.

### Deprecated logging

```python
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
```
