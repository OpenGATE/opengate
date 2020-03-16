import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gam",
    version="0.01",
    author="David Sarrut",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="Simulation for Medical Physics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dsarrut/gam",
    package_dir={'':'gam'},
    packages=setuptools.find_packages('gam'),
    #packages=['pygan'],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        'tqdm',
        'colorama',
        'click',
        'scipy',
        #'torch'   # better to install torch manually to match cuda version
      ]
    # scripts=[
    #     'bin/gam_train',
    #     'bin/gam_info',
    #     'bin/gam_plot',
    #     'bin/gam_generate',
    #     'bin/gam_convert_pth_to_pt',
    #     'bin/gam_wasserstein',
    #     'bin/gam_garf_generate_img'
    # ]
)
