import setuptools
from setuptools import find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as fh:
    version = fh.read()

all_packages = find_packages()
selected_packages = []
for p in all_packages:
    if "opengate_core" not in p:
        selected_packages.append(p)

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
    python_requires=">=3.5",
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        "opengate_core==" + version,
        "gatetools",
        "tqdm",
        "colored",
        "click",
        "python-box",
        "anytree",
        "numpy",
        "itk",
        "uproot",
        "sphinx",
        "scipy",
        "sphinx_pdj_theme",
        "matplotlib",
        "myst-parser",
        "GitPython",
        "colorlog",
    ],
    scripts=[
        "opengate/tests/opengate_tests",
        "opengate/tests/opengate_tests_wip",
        "opengate/tests/opengate_tests_utils",
        "opengate/opengate_info",
        "opengate/opengate_user_info",
    ],
)
