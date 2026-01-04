def test_importfrom_versionpin_identitytest1(CACHE_DISABLED):
    import kochen.sampleutil as submodule  # v0.2025.13
    assert submodule.foo() == "v0.2025.13"
