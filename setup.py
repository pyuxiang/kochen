import setuptools

requirements = [
    "numpy",
]

requirements_dev = [
    "pytest",
]

setuptools.setup(
    name="boiler",
    version="0.0.3",
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
