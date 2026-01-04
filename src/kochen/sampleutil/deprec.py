from kochen.versioning import deprecated_after


# Use for versions: v0.2025.{9,10}
@deprecated_after("0.2025.10")
def foo():
    return "v0.2025.10"


# Use for versions: v0.2025.{11,12}
@deprecated_after("0.2025.12")
def foo():
    return "v0.2025.12"


# Note: out-of-order intentional
# Use for versions: <= v0.2025.8
@deprecated_after("0.2025.8")
def foo():
    return "v0.2025.8"


# Use for versions: v0.2025.13
@deprecated_after("0.2025.13")
def foo():
    return "v0.2025.13"
