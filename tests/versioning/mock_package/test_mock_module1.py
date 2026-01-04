def test_importfrom_versionpin_identitytest1(CACHE_DISABLED):
    import kochen.common as kochen_common  # v0.2024.1
    assert kochen_common.test_identitytest("blah") == "blah_v0"
