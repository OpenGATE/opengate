import os
import platform

from .g4DataSetup import *


# Set Qt5 data paths:
def set_qt5_path():
    s = platform.system()
    if s == "Linux" or s == "Windows":
        g4libFolder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "opengate_core.libs"
        )
    elif s == "Darwin":
        g4libFolder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), ".dylibs"
        )

    os.environ["QTHOME"] = ""
    os.environ["QTLIBPATH"] = g4libFolder
    plugins_folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "plugins"
    )
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugins_folder
    # Linux wheels: the other Qt plugins (xcbglintegrations, needed for the
    # OpenGL viewer, and imageformats) are in subfolders of the plugins folder,
    # found by Qt through QT_PLUGIN_PATH. Not done for the source builds (no
    # such folder), which use the plugins of the installed Qt.
    if s == "Linux" and os.path.isdir(
        os.path.join(plugins_folder, "xcbglintegrations")
    ):
        paths = [plugins_folder]
        if os.environ.get("QT_PLUGIN_PATH"):
            paths.append(os.environ["QT_PLUGIN_PATH"])
        os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(paths)
