import site
import os
import sys


def get_site_packages_dir():
    site_package = [p for p in site.getsitepackages() if "site-packages" in p]
    if len(site_package) > 0:
        site_package = site_package[0]
    else:
        site_package = site.getusersitepackages()
    return site_package


def get_libG4_path(lib):
    for element in os.listdir(
        os.path.join(get_site_packages_dir(), "opengate_core.libs")
    ):
        if "libG4" + lib in element:
            return os.path.join(get_site_packages_dir(), "opengate_core.libs", element)


# Some Python versions distributed by Conda have a buggy `os.add_dll_directory`
# which prevents binary wheels from finding the FFmpeg DLLs in the `av.libs`
# directory. We work around this by adding `av.libs` to the PATH.
if os.name == "nt":
    os.environ["PATH"] = (
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, "opengate_core.libs")
        )
        + os.pathsep
        + os.environ["PATH"]
    )
    os.add_dll_directory(
        os.path.join(os.path.dirname(__file__), os.pardir, "opengate_core.libs")
    )

pathCurrentFile = os.path.abspath(__file__)
if sys.platform == "linux" or sys.platform == "linux2":
    if (
        "site-packages" in pathCurrentFile
    ):  # opengate_core is installed using wheel (for "pip install -e .", the paths are different)
        reloadPython = False
        if (
            "LD_LIBRARY_PATH" not in os.environ
            or os.path.join(get_site_packages_dir(), "opengate_core.libs")
            not in os.environ["LD_LIBRARY_PATH"]
        ):
            reloadPython = True

        if (
            "LD_PRELOAD" not in os.environ
            or get_libG4_path("processes") not in os.environ["LD_PRELOAD"]
            or get_libG4_path("geometry") not in os.environ["LD_PRELOAD"]
        ):
            reloadPython = True

        if reloadPython:
            print(
                "opengate_core is not detected. Be sure to execute these lines before to run python:"
            )
            print(
                "export LD_LIBRARY_PATH="
                + os.path.join(get_site_packages_dir(), "opengate_core.libs")
                + ":${LD_LIBRARY_PATH}"
            )
            print(
                "export LD_PRELOAD="
                + get_libG4_path("processes")
                + ":"
                + get_libG4_path("geometry")
                + ":${LD_PRELOAD}"
            )
            sys.exit(-1)
elif sys.platform == "win32":
    print(os.path.dirname(pathCurrentFile))
    os.add_dll_directory(os.path.dirname(pathCurrentFile))

from .opengate_core import *
from .g4DataSetup import *
from .qt5Setup import *


check_g4_data()
set_g4_data_path()

set_qt5_path()
