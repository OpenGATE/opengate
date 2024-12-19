import os
import sys

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
if sys.platform == "win32":
    print(os.path.dirname(pathCurrentFile))
    os.add_dll_directory(os.path.dirname(pathCurrentFile))

from .opengate_core import *
from .g4DataSetup import *
from .qt5Setup import *

if os.environ.get("GATEONRTD", None) is None:
    check_g4_data()
    set_g4_data_path()
    set_qt5_path()
