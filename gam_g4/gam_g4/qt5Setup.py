import wget
import os
import tarfile
import platform
import sys
from .g4DataSetup import *


# Set Qt5 data paths:
def set_qt5_path():

    s = platform.system()
    if s == 'Linux':
        g4libFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../gam_g4.libs")
    elif s == 'Darwin':
        g4libFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".dylibs")

    os.environ["QTHOME"] = ""
    os.environ["QTLIBPATH"] = g4libFolder
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "plugins")
    
