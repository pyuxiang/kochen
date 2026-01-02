import subprocess

import kochen.versioning

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
    assert version == str(kochen.versioning.installed_version)
