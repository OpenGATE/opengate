# Only MacOs

import os
import subprocess

libs = []

dictLibs = {
    "@rpath/libz.1.dylib": "@loader_path/../../.dylibs/libz.1.2.11.dylib",
    "@rpath/libpng16.16.dylib": "@loader_path/../../.dylibs/libpng16.16.dylib",
    "@rpath/libQt6Gui.6.dylib": "@loader_path/../../.dylibs/libQt6Gui.6.6.0.dylib",
    "@rpath/libQt6Core.6.dylib": "@loader_path/../../.dylibs/libQt6Core.6.6.0.dylib",
    "@rpath/libQt6PrintSupport.6.dylib": "@loader_path/../../.dylibs/libQt6PrintSupport.6.6.0.dylib",
    "@rpath/libQt6Widgets.6.dylib": "@loader_path/../../.dylibs/libQt6Widgets.6.6.0.dylib",
    "@rpath/libQt6Svg.6.dylib": "@loader_path/../miniconda/libQt6Svg.6.6.0.dylib",
    "@rpath/libQt6DBus.6.dylib": "@loader_path/../miniconda/libQt6DBus.6.6.0.dylib",
    "@rpath/libQt6Quick.6.dylib": "@loader_path/../miniconda/libQt6Quick.6.6.0.dylib",
    "@rpath/libQt6WebSockets.6.dylib": "@loader_path/../miniconda/libQt6WebSockets.6.6.0.dylib",
    "@rpath/libQt6QmlModels.6.dylib": "@loader_path/../miniconda/libQt6QmlModels.6.6.0.dylib",
    "@rpath/libQt6Qml.6.dylib": "@loader_path/../miniconda/libQt6Qml.6.6.0.dylib",
    "@rpath/libQt6Network.6.dylib": "@loader_path/../miniconda/libQt6Network.6.6.0.dylib",
    "@rpath/libQt6Pdf.6.dylib": "@loader_path/../miniconda/libQt6Pdf.6.6.0.dylib",
    "@rpath/libc++.1.dylib": "@loader_path/../../.dylibs/libc++.1.dylib",
    "@rpath/libjpeg.8.dylib": "@rpath/libjpeg.8.dylib",
    "@rpath/libwebp.7.dylib": "@rpath/libwebp.7.dylib",
    "@rpath/libwebpdemux.2.dylib": "@rpath/libwebpdemux.2.dylib",
    "@rpath/libwebpmux.3.dylib": "@rpath/libwebpmux.3.dylib",
    "@rpath/libtiff.6.dylib": "@rpath/libtiff.6.dylib",
}

for root, dirs, files in os.walk("opengate_core/plugins"):
    for file in files:
        if file.endswith(".dylib"):
            libs.append(os.path.join(root, file))
print(libs)

for lib in libs:
    command = "otool -L " + lib
    output = subprocess.run(command.split(), stdout=subprocess.PIPE)
    output = output.stdout.decode("utf-8")
    print(os.path.basename(lib))
    for line in output.splitlines():
        if line.lstrip().startswith("@rpath/"):
            depLib = line.lstrip().split(" ")[0]
            print(depLib)
            if not os.path.basename(depLib) == os.path.basename(lib):
                command = (
                    "install_name_tool -change "
                    + depLib
                    + " "
                    + dictLibs[depLib]
                    + " "
                    + lib
                )
                output = subprocess.run(command.split(), stdout=subprocess.PIPE)
    # print(output)
