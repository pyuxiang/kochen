# Module architecture

This design document itself seeks to properly elucidate the pros and cons
for different strategies in simultaneously maintaining different
versions of specific functions within the same codebase.

The goal is to derive a sufficiently stable API that can be robust towards
changes in the contract of the implemented functions, despite sharing the
same name and/or differing in function signatures.

## Possible scenario

User of library writes a piece of code that is subsequently unmaintained
for X years. This code is pulled out from the archives, and the next user
finds themselves unable to run the code due to updated function contracts.

The problem is further compounded by the fact that a modern version of the
same library is already being used.

### Proposed solution 1: Import different versions of the same library

This allows specific versions of the library to be referenced, and the
functions imported are in a self-consistent state.

One such mechanism is by dynamically modifying the library via some version
control system, before the function is referenced/loaded (since functions
are typically cached) and/or prior to execution of the function.

  * Problems would be reliance on a VCS on the system, plus additional
    runtime overhead when dynamically loading/executing functions.
  * This implies all function definitions should ideally be kept within the
    same version of the library, instead of being dynamically loaded
    across versions.

A side remark on storing library information associated with script:
the library version information should be tagged to the script somehow, so
that some dynamic function loader can determine which implementation to
import.

  * Possible strategy of modifying the file/module docstring to store
    this metadata. [Programmatic setting of docstring](https://stackoverflow.com/questions/4056983/how-do-i-programmatically-set-the-docstring)
    is possible, but generally not recommended.
  * Another option is to store versioning information in the extended
    attributes of a file, but this is highly filesystem dependent, and
    hence not portable.
  * Versioning as a hidden file is likely more extensible, but runs the
    risk of the file not being carried over when copying scripts.

Library/Function versions ought to be suitably versioned - the approach
to use is by storing a hidden file (typically by prepending a period)
for the particular library/versioning system, and storing either in
INI format (easy to configure), or JSON format (easy to serialize and
support limited typing).


### Proposed solution 2: Consolidate all functions into separate libraries

This involves marking `v1`, `v2`, etc. versions of the libraries,
then placing them within individual subpackages. The obvious benefit
lies in clear segregation of functions, and allows for parallel importing
of modules (as well as usage of specific versioned functions).

Main issue lies in maintaining an exponentially growing codebase due
to excessive code reuse and repetition. This strategy was initially
attempted in earlier iterations of this library, with limited success.

  * For example, developer has difficulties determining which version
    of the library a particular function is stored in, especially if using
    a sparse versioning strategy (i.e. reimplement in incremented version
    number only if function is updated, otherwise fallback to latest).
  * Bugfixing becomes a massive pain when multiple copies of the same
    function with the same bug exists.

Similar approaches have been implemented, including in `flask` where some
limited subset of the library is [replicated](https://stackoverflow.com/a/28797512),
leaving the rest of the common functions in the same library. This is
possible only if the common function themselves are already pre-specified
and stable. This is reflected more simply in [StackOverflow](https://stackoverflow.com/a/29160710).


### Proposed solution 3: Creating functions within codebase and dynamically import

Functions to write as per normal:

```python
# kochen/pathlib.py
def read_path(*args):
    pass  # function definition here

# main.py
import kochen.pathlib as pathlib
pathlib.read_path
```

When updating the function, older versions of the function can be
preserved by dragging it into some legacy codebase, and tagging it with a
specific version using a decorator (this definition should be extensible).
Specific versions of functions can be imported by using a version directive
in the module import path (perhaps via a shim).

```python
# kochen/legacy/pathlib.py
@version(1)
def read_path(*args):
    pass

# kochen/pathlib.py
def read_path(*args):
    pass  # updated function definition

# main.py
import kochen.v1.pathlib as pathlib_v1
import kochen.pathlib as pathlib
pathlib_v1.read_path
pathlib.read_path
```

Problem now is all the functions within the legacy codebase *should avoid*
depending on different versions of the libraries.
Either functions should be dynamically
loaded within the function itself, or we avoid this problem entirely by
ensuring modules are generally standalone. The former is p


TODO: To think about the merits and demerits of this proposal.

Extremely legacy code should be shelved somewhere with version labelling,
outside the main codebase. These can then be dynamically pulled when
querying the function.


## Appendix

The main lesson learnt from maintaining packages is that versioning is a
horribly difficult problem (when version constraints and others start
to come into play). Version freezing and documentation of build environment
is extremely critical for a stable codebase.

Many attempts have been made to resolve library versions
([python-multiple-versions](https://discuss.python.org/t/allowing-multiple-versions-of-same-python-package-in-pythonpath/2219),
[multiversion](https://github.com/mitsuhiko/multiversion)),
primarily in the field of using incompatible upstream dependencies.
This is still an unsolved problem.
