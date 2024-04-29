#!/usr/bin/env python3
# Justin, 2022-12-21
"""Common utilities for kochen framework.

"""

# Default when running tests
#__file__ = "common.py"

from kochen.versioning import __version__, get_version, _cache

namespace = "common"
version = get_version(namespace)

def check_version_consistency():
    assert "1b" > "1a" > "1"
    assert "2" > "1"
    assert "20" > "2"
    assert "2.0" > "2"

check_version_consistency()

def __getattr__(name):
    print("HELLO")
    print(name)

    # Dynamically pull function with current version
    # as upper bound.

    # Better to use a binary search tree if dynamically querying versions
    # Not particularly efficient though, need O(1) lookup for performance,
    # or at least O(log n) during library load time.
    return _cache[__version__][name]


@version("1")
def test_identitytest(value):
    return f"{value}_v1"

@version("2.0")
def test_identitytest(value):
    return f"{value}_v2"

@version("2.1")
def test_identitytest(value):
    return f"{value}_v2.1"

print(_cache)

del test_identitytest