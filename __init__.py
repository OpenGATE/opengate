
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

if sys.platform == "linux" or sys.platform == "linux2":
    reloadPython = False
    if 'LD_LIBRARY_PATH' not in os.environ:
        os.environ['LD_LIBRARY_PATH'] = ""
    if os.path.join(get_site_packages_dir(), "gam_g4.libs") not in os.environ['LD_LIBRARY_PATH']:
        os.environ['LD_LIBRARY_PATH'] = os.path.join(get_site_packages_dir(), "gam_g4.libs") + ":" + os.environ['LD_LIBRARY_PATH']
        reloadPython = True

    if 'LD_PRELOAD' not in os.environ:
        os.environ['LD_PRELOAD'] = ""
    if get_libG4_path("processes") + ":" + get_libG4_path("geometry") not in os.environ['LD_PRELOAD']:
        os.environ['LD_PRELOAD'] = get_libG4_path("processes") + ":" + get_libG4_path("geometry") + ":" + os.environ['LD_PRELOAD']
        reloadPython = True

    if reloadPython:
        try:
            os.execv(sys.argv[0], sys.argv)
        except Exception:
            print('Failed re-exec:')
            sys.exit(1)

from .gam_g4 import *
from .g4DataSetup import *
from .qt5Setup import *

check_G4_data_folder()
set_G4_data_path()

set_qt5_path()
