from kochen.datautil.latest import filecache

from kochen.versioning import deprecated_after


# Buggy implementation!
# f.__name__ renames the decorating wrapper instead of the actual function,
# so this function actually doesn't work as advertised.
@deprecated_after("0.2026.4")
def datacache(
    data=None,
    name="~~adhocdatastorage~~",  # must be invalid function name
    path=None,
    backend: str = "pickle",
):
    """Analog to 'filecache' but for data.

    Examples:
        >>> if (data := datacache()) is None:
        ...     data = 42  # generate data, i.e. expensive
        ...     datacache(data)
        >>> datacache()
        42
    """
    overwrite = data is not None

    # Use the same filecache mechanism
    @filecache(path=path, overwrite=overwrite, backend=backend)
    def f():
        return data

    f.__name__ = name  # this implementation is bugger
    return f()
