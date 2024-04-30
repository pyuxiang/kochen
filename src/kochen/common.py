#!/usr/bin/env python3
# Justin, 2022-12-21
"""Common utilities for kochen framework."""

# Use the versioning system
from kochen.versioning import get_namespace_versioning
version, __getattr__ = get_namespace_versioning(__name__)

@version("0.2024.1")
def test_identitytest(value):
    return f"{value}_v0"

@version("2.0")
def test_identitytest(value):
    return f"{value}_v2"

@version("2.1")
def test_identitytest(value):
    return f"{value}_v2.1"
