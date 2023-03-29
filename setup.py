import setuptools
from setuptools import find_packages
import os

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as fh:
    version = fh.read()

all_packages = find_packages()
selected_packages = []
for p in all_packages:
    if "opengate_core" not in p:
        selected_packages.append(p)

# For windows, this package is needed
install_requires_windows = []
if os.name == "nt":
    install_requires_windows = [msvc - runtime]

setuptools.setup(
    name="opengate",
    version=version,
    author="Opengate collaboration",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="Simulation for Medical Physics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OpenGATE/opengate",
    packages=selected_packages,
    python_requires=">=3.7",
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        "colored",
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
    ]
    + install_requires_windows,
    scripts=[
        "opengate/bin/opengate_tests",
        "opengate/bin/opengate_tests_utils",
        "opengate/bin/opengate_info",
        "opengate/bin/opengate_user_info",
        "opengate/bin/dose_rate",
        "opengate/bin/split_spect_projections",
        "opengate/bin/voxelize_iec_phantom",
        "opengate/bin/opengate_visu",
    ],
)
