# Boilerplate library

Pain point: Repetitive coding of the same functionality, which often involves doing the same Google searches.
Really a list of recipes for consolidation.

Some workflows:

Run tests:

```
uvx --isolated --with-editable .[all] pytest
```

Install library:

```
pip install -e .
```

Uninstall library:

```
python setup.py develop -u
```

## Design rationale

This is partly spurred by my usage of convenience scripts in the context of an experimental physics laboratory,
with the following usage observations:

**Problem**:
Scripts are commonly archived for reference, either for reuse or for referencing data collection strategies. Old scripts tend to break from outdated API.

* **Solution**: Ensure that the library is strongly back-compatible with old functionality,
    not just via version-control, but every commit should be back-compatible.
* **Problem**: Functions that share the same name are essentially overridden
    (no signature polymorphism).
* **Problem**: Functions being used may become opaque to the user, e.g. when using an IDE
    which can perform static declaration lookups, dynamic assignment of functionality (especially under a different alias) can lead to difficulties in usage.
* **Anti-pattern**: Avoid declaring functions with different names to differentiate minute
    behavioural changes. This can quickly pollute the library namespace.
* **Solution**: Stick to the same function names as much as possible, and clearly define
    the function contract. Best if a static type checker is used to enforce contractual obligations. Where functions are likely deprecated, throw out one (and only one) warning during initial script invocation.
* **Possible solution**: Pre-compile currently used library into current directory, so that
    library references change from global reference to local reference.
* **Problem**: Precompilation and duplication of libraries can lead to bloated software size
    and excessive duplication in a version-controlled environment. This also makes usage of
    updated libraries in an old environment difficult.
* **Possible solution**: Use of decorators to mark the version of certain functions.
    This mark ought to be representative of the development order of the library, i.e. older
    commits to the library should have older marks (perhaps a datetime). Individual scripts should keep track of which functions it should be calling, perhaps as a version pinning
    comment if no such comment is initially detected.
    Calling of newer functionality should still be supported, i.e. forward-compatibility.
* **Anti-pattern**: Marking of functions by shelving them within subdirectory corresponding
    to their version number should be avoided. This poses issues when (1) cross-referencing
    similar but competing implementations, (2) developer overhead from choosing directories.

**Problem**: Old scripts may have missing nested directory dependencies.

* **Solution**:
    Package all required functionality in a single library. Where not possible, pull the
    library functions into a version-control and/or a centralized environment.
* **Anti-pattern**: Functionality that are frequently updated and
    cannot be reasonably maintained
    (e.g. porting of `numpy` functions is not feasible long-term - will
    eventually deviate from updated implementations) should be delegated to third-party libraries.
* **Anti-pattern**: Avoid deploying of library as a standalone

**Problem**: Older API may depend on older implementations of third-party libraries.

* **Anti-pattern**:
    Developer could document which libraries the functions were written for, and
    throw warnings when libraries invoked do not match those specified by function.
    This however increases documentation overhead (grows with size of library),
    and may not necessarily extend to later releases which may be compatible.
* **Possible solution**:
    Provide suggestion of possible version conflict during a third-party library dependency call.
* **Problem**:
    Wrong diagnosis can occur, e.g. errors due to buggy implementation of third-party functionality.
* **Solution**:
    Not solved.

**Problem**: Scripts referencing libraries deployed in a central networked repository may
    break when connection to said network is lost. Even more so for this glue library.

* **Solution**: Avoid performing `git clone ... && pip install -e .` workflows, especially
    over a network. Where possible, enforce either `pip install git+...` or `pip install [PYPI]` workflows instead.
* **Possible solution**: For locally developed third-party dependencies, rely on virtual
    file systems (that cache contents and update dynamically whenever a change is detected),
    or prepare mirrors (i.e. defer to local library if central repository cannot be accessed).

Still a work-in-progress!

----

Some newer updates after a long lull on implementing the deprecation method.
Firstly, there seems to be some proposal [PEP723](https://peps.python.org/pep-0723/) floating around that are still provisional as of 2023-11-30 (looks like [PEP722](https://peps.python.org/pep-0722/) has been rejected in favor of PEP723). PEP723 suggests to have a following code block for embedding `pyproject.toml` in single-file scripts (arguably important for users who are not necesarily familiar with installing dependencies). Looks like this:

```python
# /// pyproject
# [run]
# requires-python = ">=3.11"
# dependencies = [
#   "requests<3",
#   "rich",
# ]
# ///
```

Note this does not actually fix the problem of having conflicting library versions. We want full backwards compatibility, as far as this library is concerned (hard to control versions on other dependencies, which is the whole point of trying to have this library self-contained).

Had a realization that library versioning should not be controlled by `git`, which limits applicability in cases where the library files are directly copied, or where `git` was not used to clone the repository in the first place. Need to somehow embed the version that is used by the script, hopefully automagically. This looks like a possible method: [Method 1](https://stackoverflow.com/questions/45684307/get-source-script-details-similar-to-inspect-getmembers-without-importing-the) and [Method 2](https://stackoverflow.com/questions/34491808/how-to-get-the-current-scripts-code-in-python) and [Method 3](https://stackoverflow.com/questions/427453/how-can-i-get-the-source-code-of-a-python-function).

Some goals:

* Backward compatibility only up till Py3.6, because the lab