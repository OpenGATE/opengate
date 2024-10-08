import os
from setuptools import setup

with open("VERSION", "r") as fh:
    version = fh.read()[:-1]

# For windows, this package is needed
install_requires_windows = []
if os.name == "nt":
    install_requires_windows = [msvc - runtime]

setup(
    install_requires=[
        "colored>1.5",
        "opengate_core==" + version,
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
        "colorlog",
        "numpy-stl @ git+https://github.com/tbaudier/numpy-stl@c7c46838c750eeda794fd568d7c57e6eca1af5a2",
        "radioactivedecay",
        "jsonpickle",
        "pandas",
        "requests",
    ]
    + install_requires_windows,
)
