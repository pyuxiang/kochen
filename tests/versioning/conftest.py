import sys

import pytest


def uncache():
    if "kochen" in sys.modules:
        # Submodules should also be removed
        names = tuple(sys.modules.keys())
        for name in names:
            if name.startswith("kochen"):
                del sys.modules[name]

@pytest.fixture
def CACHE_DISABLED():
    """Remove kochen from import cache.

    pytest will preserve imports across tests, which results in
    tests that depend on specific version pins during import.
    """
    uncache()
    yield
    uncache()
