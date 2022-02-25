import setuptools
from setuptools import find_packages

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gam-gate",
    version="0.2.4",
    author="Opengate collaboration",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="Simulation for Medical Physics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dsarrut/gam-gate",
    packages=find_packages(),
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        'gam-g4',
        'gatetools',
        'tqdm',
        'colored',
        'click',
        'python-box',
        'anytree',
        'numpy',
        'itk',
        'uproot',
        'sphinx',
        'scipy',
        'sphinx_pdj_theme',
        'recommonmark',
        'matplotlib',
        'colorlog'],
    scripts=[
        'gam_tests/gam_gate_tests',
        'gam_tests/gam_gate_tests_wip',
        'gam_gate/gam_gate_info',
        'gam_gate/gam_gate_user_info'
    ]
)
