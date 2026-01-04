def test_importfrom_versionpin_identitytest2(CACHE_DISABLED):
    from kochen import (  # v0.2025.7
        sampleutil
    )
    assert sampleutil.foo() == "v0.2025.8"
