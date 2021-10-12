import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gam-gate",
    version="0.2",
    author="Opengate collaboration",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="Simulation for Medical Physics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dsarrut/gam-gate",
    packages=['gam_gate'],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    install_requires=[
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
        'colorlog']
)
