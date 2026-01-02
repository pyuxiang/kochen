import subprocess

import kochen

def test_repl_import_latest():
    # Note the specific choice of quotation marks below is intentional:
    # Windows Powershell encapsulates string with single quotes, and use of single
    # quotes for the Python command will result in a malformed command.
    version = subprocess.check_output(
        r'python -c "import kochen; print(kochen.__version__)"',
        shell=True,
    )
    version = version.decode().strip()
    assert version == str(kochen.__version__)


def test_repl_import_pinned():
    expected = "(0, 10, 20)"

    # Generic version pinning
    version = subprocess.check_output(
        'python -c "import kochen  # v0.10.20\nprint(kochen.__version__)"',
        shell=True,
    )
    version = version.decode().strip()
    assert version == expected

    # Malformed spaces during pinning
    version = subprocess.check_output(
        'python -c "import kochen#v0.10.20  \n print(kochen.__version__)"',
        shell=True,
    )
    version = version.decode().strip()
    assert version == expected
