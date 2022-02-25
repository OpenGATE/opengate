
import site
import os
import sys

def get_site_packages_dir():
    site_package = [p for p  in site.getsitepackages()
                    if "site-packages" in p][0]
    return(site_package)

def get_libG4_path(lib):
    for element in os.listdir(os.path.join(get_site_packages_dir(), "gam_g4.libs")):
        if "libG4" + lib in element:
            return(os.path.join(get_site_packages_dir(), "gam_g4.libs", element))

pathCurrentFile = os.path.abspath(__file__)
if sys.platform == "linux" or sys.platform == "linux2":
    if "site-packages" in pathCurrentFile: #gam-g4 is installed using wheel (for "pip install -e .", the paths are different)
        reloadPython = False
        if 'LD_LIBRARY_PATH' not in os.environ or os.path.join(get_site_packages_dir(), "gam_g4.libs") not in os.environ['LD_LIBRARY_PATH']:
            reloadPython = True

        if 'LD_PRELOAD' not in os.environ or get_libG4_path("processes") not in os.environ['LD_PRELOAD'] or get_libG4_path("geometry") not in os.environ['LD_PRELOAD']:
            reloadPython = True

        if reloadPython:
            print("gam-g4 is not detected. Be sure to execute these lines before to run python:")
            print("export LD_LIBRARY_PATH=" + os.path.join(get_site_packages_dir(), "gam_g4.libs") + ":${LD_LIBRARY_PATH}")
            print("export LD_PRELOAD=" + get_libG4_path("processes") + ":" + get_libG4_path("geometry") + ":${LD_PRELOAD}")
            sys.exit(-1)


from .gam_g4 import *
from .g4DataSetup import *
from .qt5Setup import *

check_G4_data_folder()
set_G4_data_path()

set_qt5_path()
