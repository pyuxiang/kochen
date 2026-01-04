def test_deprecation_outdated_unimplemented(CACHE_DISABLED):
    from kochen.sampleutil import foo  # v0.2025.7
    assert foo() == "v0.2025.8"

def test_deprecation_outdated_at_deprec(CACHE_DISABLED):
    from kochen.sampleutil import foo  # v0.2025.10
    assert foo() == "v0.2025.10"

def test_deprecation_outdated_after_deprec(CACHE_DISABLED):
    from kochen.sampleutil import foo  # v0.2025.11
    assert foo() == "v0.2025.12"

def test_deprecation_outdated_before_latest(CACHE_DISABLED):
    from kochen.sampleutil import foo  # v0.2025.15
    assert foo() == "latest"

def test_deprecation_latest(CACHE_DISABLED):
    from kochen.sampleutil import foo
    assert foo() == "latest"

def test_deprecation_future(CACHE_DISABLED):
    from kochen.sampleutil import foo  # v9999
    assert foo() == "latest"
