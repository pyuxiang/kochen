def test_importfrom_versionpin_identitytest2(CACHE_DISABLED):
    from kochen import (  # v2.0.1
        common
    )
    assert common.test_identitytest(123) == "123_v2"
