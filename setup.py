import os
from setuptools import setup

with open("VERSION", "r") as fh:
    version = fh.read()[:-1]

# For windows, this package is needed
install_requires_windows = []
if os.name == "nt":
    install_requires_windows = ["msvc-runtime"]

setup(
    install_requires=[
        "colored>1.5",
        "opengate-core==" + version,
        "gatetools",
        "click",
        "python-box<7.0.0",
        "anytree",
        "numpy",
        "itk",
        "uproot",
        "scipy",
        "matplotlib",
        "GitPython",
        "meshio",
        "radioactivedecay",
        "jsonpickle",
        "pandas",
        "awkward-pandas",
        "tables",
        "requests",
        "PyYAML",
        "SimpleITK",
        "spekpy",
        "icrp107-database>=0.0.3",
        "loguru",
    ]
    + install_requires_windows,
)
