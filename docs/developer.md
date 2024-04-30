# Development

## Versioning system

The versioning of this library must follow the `[MAJOR].[YEAR].[MINOR]` format, similar to that practiced by PlantUML. This is effectively a combination of [semantic versioning](https://semver.org/) and [calendar versioning](https://calver.org/):

* MAJOR should be incremented, whenever a big breaking change in API is expected (usually in the versioning system `kochen.versioning` itself). The library is otherwise designed to be strongly backward compatible, and this number is not expected to be incremented
* YEAR should follow the current year of release. This gives the user reasonable clarity on whether the library requested by the script (or the installed library) is current or not.
* MINOR should be incremented, whenever new features or bugfixes are pushed out. Set to zero when updating YEAR.

Because features are expected to be pushed to this library fairly frequently, the minor version is also expected to be updated often, i.e. the minor version is really more of a build/patch number. Since features developed within the year should be reasonably supported, a year number is appropriate.

The SSOT for versioning is in the `pyproject.toml:version` field. This metadata will be dynamically retrieved upon module instantiation of `kochen.versioning`, and disseminated to the other submodules in the library.

### How it works

#### Library function definition

The relevant functions to capture under the versioning system should follow a similar format for each submodule:

```python
# kochen/mathutil.py
from kochen.versioning import get_namespace_versioning
version, version_cleanup, __getattr__ = \
    get_namespace_versioning(__name__, globals())

@version("0.2024.1")
def f(value):
    return value

version_cleanup()
```

#### Library install

When the user installs the library, the version number in the `pyproject.toml` is cached as part of the library metadata.

#### Library import

When the user imports the library, the initial import line usually looks like this:

```python
import kochen  # for v0.2024.1
```

The `__init__.py` for the library further triggers the versioning system via:

```python
# kochen/__init__.py
import kochen.versioning
```

The version number is tagged to the initial library import line, and the latter can be located anywhere in the script dependency chain; the `versioning._search_importline` will traverse the dependency DAG from the root script, using `ast` to identify the imported modules and `sys.modules` to fish out the module file that was imported, rinse and repeat.

Once the target import line is found, the version number in the comments is extracted with `versioning.RE_VERSION_STRING`, and exposed as `requested_version` as a tuple of integers. The `installed_version` is also cached.

The rest of the library then loads using the versioning definition above. The `@versioning.version` decorator performs caching of functions relative to the requested and installed library versions.

#### Library function call

At runtime, the function name is passed to the corresponding submodule, which performs a dynamic lookup using `__getattr__` attribute assigned to `versioning.search`. This is simply a hashtable lookup.

Dynamic referencing of function versions has not yet been implemented.
