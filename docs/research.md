# Import flow in Python

## Initial spec reading

(updated 2023-12-05)

Some historical documents cross-referenced when looking up the importing flow:

* PEP302: https://peps.python.org/pep-0302/#id17
    * Old document stating how import should be handled, specifically in two parts: (1) path finding, (2) importing. Sample code below.
    * In particular `sys.modules` need to be check if it already contains the fully qualified module name. This is also designed to be writable (!).

```python
def load_module(self, fullname):
    code = self.get_code(fullname)
    ispkg = self.is_package(fullname)
    mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
    mod.__file__ = "<%s>" % self.__class__.__name__
    mod.__loader__ = self
    if ispkg:
        mod.__path__ = []
        mod.__package__ = fullname
    else:
        mod.__package__ = fullname.rpartition('.')[0]
    exec(code, mod.__dict__)
    return mod
```

* Import language reference: https://docs.python.org/3/reference/import.html
    * The superseded version to PEP302. This entire section is particularly illuminating: https://docs.python.org/3/reference/import.html#loading
    * Sample code for the modernized duties of the 'loader' portion below:

```python
import sys
from collections.abc import Callable
from importlib.machinery import ModuleSpec
from types import ModuleType

def load_spec(spec, _init_module_attrs: Callable):
    """Loads module based on supplied spec.

    See [1] for the full specification. The module spec is defined in [3].
    Note that Callable is made subscriptable only from Python 3.9 onwards,
    with typing.Callable deprecated. So avoid annotations unless necessary.
    The proper form would be Callable[[ModuleSpec, ModuleType], None].

    ModuleType falls under the types library [2].

    References:
        [1]: https://docs.python.org/3/reference/import.html#loading
        [2]: https://docs.python.org/3/library/types.html#types.ModuleType
        [3]: https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec
    """

    module = None
    if spec.loader is not None and hasattr(spec.loader, 'create_module'):
        # It is assumed 'exec_module' will also be defined on the loader.
        module = spec.loader.create_module(spec)
    if module is None:
        module = ModuleType(spec.name)

    # The import-related module attributes get set here:
    _init_module_attrs(spec, module)

    if spec.loader is None:
        raise ImportError  # unsupported
    if spec.origin is None and spec.submodule_search_locations is not None:
        sys.modules[spec.name] = module  # namespace package
    elif not hasattr(spec.loader, 'exec_module'):
        module = spec.loader.load_module(spec.name)
    else:
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            try:
                del sys.modules[spec.name]
            except KeyError:
                pass
            raise
    return sys.modules[spec.name]
```

* Implementation of import: https://docs.python.org/3/library/importlib.html#module-importlib
    * The library 'importlib'. Be careful that the submodules 'metadata' and 'resources' are newer features of Python 3.7/3.8.

It seems like the correct way to go about implementing a custom namespace is indeed to inject a `MetaPathFinder` or `PathEntryFinder` (both interfaces are specified in `importlib.abc`, and defined in Python 3.6). The documentation supplied in `importlib` along with its recipes look valid: https://docs.python.org/3/library/importlib.html#examples

Some additional resources:

* `ModuleType`: https://docs.python.org/3/library/types.html#types.ModuleType
* `ModuleSpec`: https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec
* `meta_path`: https://docs.python.org/3/library/sys.html#sys.meta_path
* `path_hooks`: https://docs.python.org/3/library/sys.html#sys.path_hooks

## `importlib.load_module` minimal code

We dissect this example to see what we can glean from it:

```python
import importlib.util
import sys

def import_module(name, package=None):
    """An approximate implementation of import."""
    # Checks if relative import does not supply package name
    absolute_name = importlib.util.resolve_name(name, package)
    try:
        return sys.modules[absolute_name]  # already imported
    except KeyError:
        pass

    # Perform recursive import and get location from parent spec
    path = None
    if '.' in absolute_name:
        parent_name, _, child_name = absolute_name.rpartition('.')
        parent_module = import_module(parent_name)
        path = parent_module.__spec__.submodule_search_locations

    # Search for finder to supply module spec
    for finder in sys.meta_path:
        spec = finder.find_spec(absolute_name, path)
        if spec is not None:
            break
    else:
        msg = f'No module named {absolute_name!r}'
        raise ModuleNotFoundError(msg, name=absolute_name)

    # Load module from spec (loader is supplied within spec)
    module = importlib.util.module_from_spec(spec)
    sys.modules[absolute_name] = module
    spec.loader.exec_module(module)  # execute the module

    # Set subpackage as attribute of package, as per specification
    if path is not None:
        setattr(parent_module, child_name, module)
    return module
```

The `resolve_name` method will error only when a relative import is triggered, but there is no associated package relative to it. For top-level modules, this is followed by searching for a finder in `sys.meta_path` to check if any available finder can supply a `ModuleSpec` containing the appropriate loader for the import flow (defined per [PEP451](
https://peps.python.org/pep-0451/)).

```python
# Warning: will likely defer with installed libraries
>>> sys.meta_path
[<class '_frozen_importlib.BuiltinImporter'>, <class '_frozen_importlib.FrozenImporter'>, <class '_frozen_importlib_external.PathFinder'>]

# Example from another installation
[<_distutils_hack.DistutilsMetaFinder object at 0x7febadd66410>, <class '_frozen_importlib.BuiltinImporter'>, <class '_frozen_importlib.FrozenImporter'>, <class '_frozen_importlib_external.PathFinder'>, <class '__editable___kochen_0_1_0_finder._EditableFinder'>]

# Warning: may differ across compilations
>>> sys.builtin_module_names  # contains names of built-in modules, defined only from 3.10
('_abc', '_ast', '_codecs', '_collections', '_functools', '_imp', '_io', '_locale', '_operator', '_signal', '_sre', '_stat', '_string', '_symtable', '_thread', '_tracemalloc', '_warnings', '_weakref', 'atexit', 'builtins', 'errno', 'faulthandler', 'gc', 'itertools', 'marshal', 'posix', 'pwd', 'sys', 'time', 'xxsubtype')

>>> sys.meta_path[0].find_spec("time")
ModuleSpec(name='time', loader=<class '_frozen_importlib.BuiltinImporter'>, origin='built-in')

>>> sys.meta_path[2].find_spec("numpy")
ModuleSpec(name='numpy', loader=<_frozen_importlib_external.SourceFileLoader object at 0x7febadd9f460>, origin='/home/justin/.pyenv/versions/3.10.6/lib/python3.10/site-packages/numpy/__init__.py', submodule_search_locations=['/home/justin/.pyenv/versions/3.10.6/lib/python3.10/site-packages/numpy'])

# Objects on `sys.meta_path` are classes
>>> sys.meta_path[2].__mro__
(<class '_frozen_importlib_external.PathFinder'>, <class 'object'>)
>>> type(sys.meta_path[2])
<class 'type'>
```

Some lessons learnt:

* Do not mess with editable installations, these will have special sideloaded behaviour introduced by the module backend builder which will likely be hard to control for.
* Here's another person's writeup on importers, pretty cool: https://github.com/0cjs/sedoc/blob/master/lang/python/importers.md
* According to the writeup, the `_frozen_importlib_external.PathFinder` (instance of `MetaPathFinder`) internally performs a search for a path hook in `sys.path_hooks` (basically a list of `Callable[[str],PathEntryFinder]`, each taking in a fullpath).
    * The empty string is probably the current working directory.
    * Finders (found or otherwise `None`) are cached in the `sys.path_importer_cache` dictionary.

```python
>>> sys.path_hooks
[<class 'zipimport.zipimporter'>, <function FileFinder.path_hook.<locals>.path_hook_for_FileFinder at 0x7fb57d364af0>]

# File finder to search directories for files
>>> ff = sys.path_hooks[1]
>>> ff.__mro__
(<class '_frozen_importlib_external.FileFinder'>, <class 'object'>)

# Path search to pass to each finder in `sys.path_hooks`
>>> sys.path  # formatted
[
    '/srv/samba/lightstick/by-programs/software',  # empty string if main is not script
    '/home/justin/.pyenv/versions/3.10.6/lib/python310.zip',
    '/home/justin/.pyenv/versions/3.10.6/lib/python3.10',
    '/home/justin/.pyenv/versions/3.10.6/lib/python3.10/lib-dynload',
    '/home/justin/.local/lib/python3.10/site-packages',
    '/home/justin/.pyenv/versions/3.10.6/lib/python3.10/site-packages',
    '/srv/samba/lightstick/by-programs/software/QKDServer',
]

# FileFinder -> PathEntryFinder -> ModuleSpec
# Note the result is the same as above code block.
>>> ff("/home/justin/.pyenv/versions/3.10.6/lib/python3.10/site-packages").find_spec("numpy")
ModuleSpec(name='numpy', loader=<_frozen_importlib_external.SourceFileLoader object at 0x7fb57c42ed10>, origin='/home/justin/.pyenv/versions/3.10.6/lib/python3.10/site-packages/numpy/__init__.py', submodule_search_locations=['/home/justin/.pyenv/versions/3.10.6/lib/python3.10/site-packages/numpy'])
```

More lessons learnt:

* For each `sys.path` and `sys.path_hooks` combination, the resulting `PathEntryFinder` returned is used to perform the spec search.
    * This means the direct method is to inject a function in `sys.path_hooks` that intercepts the directory where the module is located, and returns a custom `ModuleSpec` that implements its own loader.
* Editable entries are injected in `sys.meta_path` instead, likely since the fullpath is cached by pip at installation time.
    * Injection of a namespace upon import of a top-level package, can be done by inspecting the search locations then using it as a supplied path.

```python
>>> editablefinder  # from `sys.meta_path`
<class '__editable___S15lib_0_2_0_finder._EditableFinder'>
>>> editablefinder.find_spec("S15lib")
ModuleSpec(name='S15lib', loader=<_frozen_importlib_external.SourceFileLoader object at 0x7fb57c42ecb0>, origin='/srv/samba/lightstick/by-programs/software/pyS15/S15lib/__init__.py', submodule_search_locations=['/srv/samba/lightstick/by-programs/software/pyS15/S15lib'])
>>> editablefinder.find_spec("S15lib").submodule_search_locations
['/srv/samba/lightstick/by-programs/software/pyS15/S15lib']
```

To implement custom importing (adapted from the guide mentioned earlier):

```python
sys.path_hooks.insert(0, custom_path_hook)

def custom_path_hook(path):
    return CustomFinder(path)

# Note that PathEntryFinders do require instantiation
class CustomFinder(importlib.abc.PathEntryFinder):
    """

    References:
        [1]: https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder
    """
    def __init__(self, path):
        self.path = path

    # Required interfaces
    def find_spec(self, fullname, target=None) -> ModuleSpec:
        return get_module_spec(self.path, fullname, target)
    def invalidate_caches(self):  # optional if any caches are used
        pass

# Concrete implementation
def get_module_spec(path, name, target=None):
    import importlib.util
    location = search_for_importfile(path, name)
    return importlib.util.spec_from_file_location(name)

# Looks like build backends require some explicit definition of package structure
# if not in standard src/{{PACKAGENAME}}/ or {{PACKAGENAME}}/.
# Not sure if this is the same.
def search_for_importfile(path, name):
    for directory in [  # sample implementation
        pathlib.Path(path) / name,
        pathlib.Path(path) / "src",
        pathlib.Path(path) / "src" / name,
    ]:
        entrypoint = directory / "__init__.py"
        if entrypoint.exists():
            return entrypoint
    return None
```

A more direct way is to rely on the fact that the top-level package needs to be imported first, before subpackages are imported. This means one can inject the custom loader in the `__init__.py` of the top-level which will be executed for subsequent subpackage loading.
In other words, the injection point is `spec.loader.exec_module(module)`, and we assume `sys.modules[PACKAGE]` is already populated with the base module. This simplifies the setup to the code block below:

```python
# Following the `import_module` code
import_module("kochen.versioning")  # full path
import_module(".mathutil", "kochen")  # relative path
import_module("kochen.v2.mathutil")  # what we want

# Parent module and child directories
absolute_name = "kochen.v2"
parent = sys.modules["kochen"]  # guaranteed
child_name = "v2"
path = parent.__spec__.submodule_search_locations

# Check for version string here
# e.g. child_name <= parent.__version__

# Injected finder
# We are done here once we define the injected_finder, i.e. KochenFinder
spec = injected_finder.find_spec(absolute_name, path)

#...

# Defining the finder now
sys.meta_paths.append(KochenFinder)

# Note this has no instantiation (as opposed to PathEntryFinder)
class KochenFinder(importlib.abc.MetaPathFinder):
    @staticmethod
    def find_spec(fullname, path, target=None):
        # We ignore 'target' here (likely the parent module object),
        # since we have a clear idea of what we want
        # fullname == "kochen.v2"
        # path == <root to kochen library>

        # Goal here to define a custom loader to force a namespace
        return KochenLoader()

def KochenLoader(importlib.abc.FileLoader):  # not sure if correct loader
    def create_module(spec):
        return None  # let system create module
    def exec_module(module):
        # Probably to inject 'child_name' version string into module
        # then load the module of specified version.
        exec(code, module.__dict__)
```

Okay I am done here for today. Back to actual work.

Some interesting last minute stuff:

* Magic numbers are provided to distinguish compiled Python binaries, see [here](https://github.com/python/cpython/blob/main/Lib/importlib/_bootstrap_external.py#L220).
* Import code in CPython are achieved by `PathFinder` and `FileFinder` [here](https://github.com/python/cpython/blob/main/Lib/importlib/_bootstrap_external.py#L1752):
    * `PathFinder.find_spec` implementation [here](https://github.com/python/cpython/blob/main/Lib/importlib/_bootstrap_external.py#L1533)
    * Time to do some code tracing!
