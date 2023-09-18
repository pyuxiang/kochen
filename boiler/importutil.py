import importlib
import sys

class SuppressPrint:
    """Suppress print messages, i.e. stdout.

    Useful for debugging / profiling / suppressing stdout from functions
    beyond your control. Works by creating a context within which outputs
    to stdout are redirected to /dev/null.

    Examples:
        >>> def f(x):
        ...     print("Returning x + 1")
        ...     return x+1
        >>> with SuppressPrint():
        ...     result = sum([f(x) for x in range(3)])
        >>> result
        6
    """
    def __enter__(self):
        self.restore, sys.stdout = sys.stdout, None
    def __exit__(self, *args):
        sys.stdout = self.restore

def import_pyfile(filepath):
    """Dynamic import of Python files.

    Useful for automating testing of standardized python scripts, e.g.
    student submissions in a Python course. A strong warning for such
    a use-case: vet through untrusted scripts before actually running them.
    """
    if not filepath.is_file():
        raise FileNotFoundError(f'{filepath} does not exist.')
    sys.path.insert(0, filepath.parent)
    with SuppressPrint():
        try:
            module = importlib.import_module(filepath.name)
        except:
            raise RuntimeError(f'{filepath.name} cannot be imported properly.')
    # To import specific module functionality, use the getattr function
    # and check for AttributeError
    return module

