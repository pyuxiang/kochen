import setuptools

requirements = [
    "numpy",
    "importlib-metadata; python_version<'3.8'"
]

requirements_dev = [
    "pytest",
]

# We use the deprecated setuptools mechanism since
# Python 3.6 only comes with setuptools==40.6.2-59.6.0
# pip ~21.3.1 seems to behave poorly with newer pyproject.toml
# semantics
setuptools.setup(
    name="boiler",
    version="0.0.8",
    description="A compilation of boilerplate code",
    url="https://pyuxiang.com",
    author="Justin",
    author_email="justin@pyuxiang.com",
    license="GPLv3",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    extras_require={
        "dev": requirements_dev,
    },
    python_requires=">=3.6",
)
