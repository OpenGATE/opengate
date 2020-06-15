import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gam",
    version="0.02",
    author="David Sarrut",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="Simulation for Medical Physics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dsarrut/gam",
    package_dir={'gam':'gam', 'gam2': 'gam2'},
    packages=['gam', 'gam2'], #setuptools.find_packages('gam'),
    #packages=['pygan'],
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
        'anytree'
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
