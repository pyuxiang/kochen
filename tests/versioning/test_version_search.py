import subprocess

import kochen.versioning

def test_version_nested_import1(CACHE_DISABLED):
    from .mock_package.test_mock_module1 import test_importfrom_versionpin_identitytest1 as test
    test(None)


def test_version_nested_import2(CACHE_DISABLED):
    from .mock_package.test_mock_module2 import test_importfrom_versionpin_identitytest2 as test
    test(None)


def test_command_import():
    # Note the specific choice of quotation marks below is intentional:
    # Windows Powershell encapsulates string with single quotes, and use of single
    # quotes for the Python command will result in a malformed command.
    version = subprocess.check_output(
        r'python -c "import kochen; print(kochen.versioning.requested_version)"',
        shell=True,
    )
    version = version.decode().strip()
    assert version == str(kochen.versioning.installed_version)

    # Version pinning will not work, and should return latest as well.
    version = subprocess.check_output(
        'python -c "import kochen  # v0.10.20\nprint(kochen.versioning.requested_version)"',
        shell=True,
    )
    version = version.decode().strip()
    # TODO: Does not work on Windows Powershell; newline is not parsed in Powershell
    #       and is thus commented out during execution.
    # assert version == str(kochen.versioning.installed_version)
