# Versioning

Old method worked by performing AST recursive depth-first search,
starting from the Python entrypoint (i.e. retrieved via
'sys.modules["__main__"]') using '_search_importline()'. This is
obviously very inefficient, and will break under edge cases, since
it is not known a-priori how deep the library import statement is
nested.


Generally does not work in certain REPLs (e.g. CPython) because the.

This can be tested by printing out the call stack during the version request, e.g.
in 'kochen.versioning._get_requested_version()'.
The REPL directly pre-processes the executed lines by stripping all comments:
this can be observed by inspecting the base of the call stack and noting the lengths
of the source code does not include whitespace and comments.

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

Insted, we rely on

## Tracing

Here is a simplified control flow chart when Python REPL is triggered, obtained by tracing the source. There might be errors, so beware!
Relevant files for Python 3.8:

* [Modules/main.c](https://github.com/python/cpython/blob/39b2f82717a69dde7212bc39b673b0f55c99e6a3/Modules/main.c)
* [Python/pythonrun.c](https://github.com/python/cpython/blob/39b2f82717a69dde7212bc39b673b0f55c99e6a3/Python/pythonrun.c)

```
(Modules/main.c) Py_RunMain
└ pymain_run_python
  ├ pymain_import_readline  # imports GNU readline library (or abstraction of it)
  ├ pymain_run_stdin
  └ pymain_repl
    └ (Python/pythonrun.c) PyRun_AnyFileFlags  # with <stdin> file
      └ PyRun_AnyFileExFlags
        └ PyRun_InteractiveLoopFlags
          └ PyRun_InteractiveOneObjectEx
            └ run_mod
              ├ PyAST_CompileObject
              └ run_eval_code_obj
                └ (Python/ceval.c) PyEval_EvalCode  # frame is created here
```

Of particular note is the use of C-based readline to store history, before storing the executing command as a file and compiling
it into bytecode (which would have already been preprocessed). This means the only sensible way to read the actual code context is to use
the `readline` interface provided as a [builtin library](https://docs.python.org/3.8/library/readline.html#module-readline).
The readline seems to be called prior to any statement evaluation, and so can be used to directly pull the user history.

* GNU history: https://cgit.git.savannah.gnu.org/cgit/readline.git/tree/history.h
  * Readline: https://github.com/python/cpython/blob/3.8/Modules/readline.c#L693
* New _pyrepl package from 3.13 onwards: https://github.com/python/cpython/tree/main/Lib/_pyrepl
  * Based on PyPy's REPL
  * PEP 762: https://peps.python.org/pep-0762/

REPL exclusion:


    # For Python <3.13, the REPL script does not belong to any package
    try:
        main_module = sys.modules["__main__"]
        # print(main_module.In)
        # https://stackoverflow.com/questions/1156023/print-current-call-stack-from-a-method-in-code

        # hey = (inspect.stack(context=3), inspect.currentframe())
        path_main = main_module.__file__
    except (KeyError, AttributeError):  # ignore interactive sessions
        return installed_version

    # For Python >=3.13, the REPL is assigned to package '_pyrepl' and __file__
    # is no longer unset.
    if main_module.__package__ == "_pyrepl":
        return installed_version


Search for the line reference to import of target library.

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


def _search_importline(path, depth=0, max_depth=MAX_IMPORTSEARCH_DEPTH):

isinstance(node, (ast.Import, ast.ImportFrom))

Doing a cached DFS then looking up lineno for file.

* Probably requires global import.

isinstance(node, )