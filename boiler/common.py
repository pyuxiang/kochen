#!/usr/bin/env python3
# Justin, 2022-12-21
"""Common utilities for boiler framework.

"""

# Default when running tests
#__file__ = "common.py"

from typing import Optional

# Avoid using defaultdict in case of API changes
_dynamic_loader = {}

def version(version_str: str, namespace: Optional[str] = None):
    def cacher(func):

        # Cache function in loader for dynamic calls
        if namespace not in _dynamic_loader:
            _dynamic_loader[namespace] = {}
        _dynamic_loader[namespace][version_str] = func

        # TODO(Justin): Remove this patch that ignores namespac
        if version_str not in _dynamic_loader:
            _dynamic_loader[version_str] = {}
        _dynamic_loader[version_str][func.__name__] = func

        # Part of static compilation, might be needed for plain compile
        # otherwise, 'common.test_function' will be assigned None.
        # TODO(Justin): Check if necessary, perhaps for compatibility
        #               with other libraries.
        return func
    
    # Assign namespace to local filename
    if namespace is None:

        # Retrieve only filename excl. extension,
        # so as to avoid importing pathlib
        _namespace = __file__
        if "/" in _namespace:
            _namespace = _namespace.split("/")[-1]
        if "." in _namespace:
            _namespace = _namespace[:_namespace.index(".")]
        namespace = _namespace

    return cacher

_current_version = "2"

def check_version_consistency():
    assert "1b" > "1a" > "1"
    assert "2" > "1"
    assert "20" > "2"
    assert "2.0" > "2"

check_version_consistency()

def __getattr__(name):
    print(name)
    
    # Dynamically pull function with current version
    # as upper bound.

    # Better to use a binary search tree if dynamically querying versions
    # Not particularly efficient though, need O(1) lookup for performance,
    # or at least O(log n) during library load time.
    return _dynamic_loader[_current_version][name]


@version("1")
def test_identitytest(value):
    return f"{value}_v1"

@version("2")
def test_identitytest(value):    
    return f"{value}_v2"

@version("2.1")
def test_identitytest(value):    
    return f"{value}_v2.1"

print(_dynamic_loader)

del test_identitytest