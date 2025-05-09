import os
import re
import sys
import platform
import subprocess
import json
import setuptools
import sysconfig
from pathlib import Path


def warning(s):
    print(s)


def get_cmake_dir() -> Path:
    plat_name = sysconfig.get_platform()
    python_version = sysconfig.get_python_version()
    dir_name = f"cmake.{plat_name}-{sys.implementation.name}-{python_version}"
    cmake_dir = Path(get_base_dir()) / "core" / "build" / dir_name
    cmake_dir.mkdir(parents=True, exist_ok=True)
    return cmake_dir


def get_base_dir() -> Path:
    return Path(__file__).parent.parent.resolve()


with open("../VERSION", "r") as fh:
    version = fh.read()[:-1]

from setuptools import Extension, find_packages
from setuptools.command.build_ext import build_ext
from distutils.version import LooseVersion


class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=""):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    def run(self):
        try:
            out = subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: "
                + ", ".join(e.name for e in self.extensions)
            )

        if platform.system() == "Windows":
            cmake_version = LooseVersion(
                re.search(r"version\s*([\d.]+)", out.decode()).group(1)
            )
            if cmake_version < "3.1.0":
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        # required for auto-detection of auxiliary "native" libs

        if not extdir.endswith(os.path.sep):
            extdir += os.path.sep

        cmake_args = [
            "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + extdir,
            "-DPYTHON_EXECUTABLE=" + sys.executable,
        ]

        # cfg = 'Debug' if self.debug else 'Release'
        cfg = "Release"
        build_args = ["--config", cfg]

        # Pile all .so in one place and use $ORIGIN as RPATH
        cmake_args += ["-DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE"]
        cmake_args += ["-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE"]
        cmake_args += ["-DCMAKE_INSTALL_RPATH={}".format("$ORIGIN")]
        # cmake_args += ['-DCMAKE_CXX_FLAGS="-Wno-self-assign -Wno-extra-semi"']
        cmake_args += ["-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]

        if platform.system() == "Windows":
            cmake_args += [
                "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), extdir)
            ]
            # cmake_args += ['-G "CodeBlocks - NMake Makefiles"']
            if sys.maxsize > 2**32:
                cmake_args += ["-A", "x64"]
            build_args += ["--", "/m"]
        else:
            cmake_args += ['-DCMAKE_CXX_FLAGS="-Wno-pedantic"']
            cmake_args += ["-DCMAKE_BUILD_TYPE=" + cfg]
            build_args += ["--", "-j4"]

        env = os.environ.copy()

        env["CXXFLAGS"] = '{} -DVERSION_INFO=\\"{}\\"'.format(
            env.get("CXXFLAGS", ""), self.distribution.get_version()
        )

        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)

        print()
        print()
        warning("-----------------------------------")
        warning("-----------------------------------")
        print()
        print()

        print(f"Build folder : {self.build_temp}")

        print("Try to open config.json file")
        fn = "config.json"
        sconfig = {"G4INSTALL": "", "ITKDIR": ""}
        if "G4INSTALL" in env:
            sconfig["G4INSTALL"] = env["G4INSTALL"]
        if "ITKDIR" in env:
            sconfig["ITKDIR"] = env["ITKDIR"]
        try:
            f = open(fn, "r")
            sconfig = json.load(f)
        except IOError:
            print("No config file, use default")
        print("Config : ", sconfig)
        print()

        cmake_args += ["-DGeant4_DIR=" + sconfig["G4INSTALL"]]
        cmake_args += ["-DITK_DIR=" + sconfig["ITKDIR"]]

        print("CMAKE args", cmake_args)
        print()

        cmake_dir = get_cmake_dir()
        print("CMAKE build dir", cmake_dir)
        print()

        print("Starting cmake ...")
        subprocess.check_call(
            ["cmake", ext.sourcedir] + cmake_args, cwd=cmake_dir, env=env
        )
        print("cmake done")
        # subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=cmake_dir)

        subprocess.check_call(
            ["cmake", "--build", ".", "--target", ext.name] + build_args,
            cwd=cmake_dir,
        )


if platform.system() == "Darwin":
    package_data = {
        "opengate_core": ["plugins/platforms/*.dylib"]
        + ["plugins/imageformats/*.dylib"]
        + ["plugins/miniconda/libQt5Svg.5.9.7.dylib"]
    }
    # package_data = {}
else:
    package_data = {"opengate_core": ["plugins/*/*.so"]}

setuptools.setup(
    name="opengate-core",
    version=version,
    author="Opengate collaboration",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="Simulation for Medical Physics",
    long_description="Simulation for Medical Physics",
    long_description_content_type="text/markdown",
    url="https://github.com/OpenGATE/opengate",
    ext_package="opengate_core",
    ext_modules=[CMakeExtension("opengate_core")],
    cmdclass=dict(build_ext=CMakeBuild),
    packages=find_packages(),
    package_data=package_data,
    zip_safe=False,
    python_requires=">=3.9",
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    install_requires=["wget", "colored>1.5", "requests"],
)
