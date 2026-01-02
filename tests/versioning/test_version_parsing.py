
import pytest

from kochen.versioning import _parse_version_pin, _version_str2tuple

pinned_version_str = "0.10.3"
pinned_version = _version_str2tuple(pinned_version_str)
contexts = [
    "import kochen",  # import
    "import  kochen  ",
    "import kochen as k",  # alias
    "import  kochen  as  k  ",
    "import kochen.versioning",  # submodule
    "import   kochen.versioning ",
    "from kochen import versioning",  # importfrom
    "from   kochen   import   versioning  ",
    "from kochen import (",  # multline
    "from  kochen  import   (  ",
    "from kochen import ( versioning )",
    "from kochen import  (versioning  ,)  ",
    "from kochen import ( versioning as version,",
    "from kochen import ( versioning  as   version  ",
    "from kochen.versioning import *",  # star
    "from  kochen.versioning  import   *  ",
]


@pytest.fixture(params=contexts)
def context_unpinned(request):
    return request.param

def test_version_parsing_unpinned(context_unpinned):
    version = _parse_version_pin(context_unpinned)
    assert version is None


# Single multi-statement line with comments basically comments everything else out.
# This is expected behaviour: do not implement negative lookahead to delimit ';'
@pytest.fixture(params=[
    f"{c} # @#&!;  import distraction # v{pinned_version_str}" for c in contexts
])
def context_unpinned_multistatement(request):
    return request.param

def test_version_parsing_unpinned_multistatement(context_unpinned_multistatement):
    version = _parse_version_pin(context_unpinned_multistatement)
    assert version == pinned_version


@pytest.fixture(params=[
    f"{c} # v{pinned_version_str}" for c in contexts
])
def context_pinned(request):
    return request.param

def test_version_parsing_pinned(context_pinned):
    version = _parse_version_pin(context_pinned)
    assert version == pinned_version


# Should match the earliest seen version
@pytest.fixture(params=[
    f"{c} # v{pinned_version_str}; import distraction # v0.3.9" for c in contexts
])
def context_pinned_multistatement(request):
    return request.param

def test_version_parsing_pinned_multistatement(context_pinned_multistatement):
    version = _parse_version_pin(context_pinned_multistatement)
    assert version == pinned_version


def test_version_parsing_commented():
    version = _parse_version_pin(f"import logging  # import kochen  # v{pinned_version_str}")
    assert version is None
