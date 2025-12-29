from kochen.versioning import deprecated


@deprecated("0.2025.10")
def foo():
    return "v0.2025.10"


@deprecated("0.2025.12")  # marks the latest version this was deprecated after
def foo(x=None):
    return f"v0.2025.12_{x}"
