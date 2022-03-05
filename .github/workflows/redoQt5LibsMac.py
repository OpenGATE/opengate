#Only MacOs

import os
import subprocess
libs = [ ]

dictLibs = { "@rpath/libz.1.dylib": "@loader_path/../../.dylibs/libz.1.2.11.dylib",
             "@rpath/libpng16.16.dylib": "@loader_path/../../.dylibs/libpng16.16.dylib",
             "@rpath/libQt5Gui.5.dylib": "@loader_path/../../.dylibs/libQt5Gui.5.9.7.dylib",
             "@rpath/libQt5Core.5.dylib": "@loader_path/../../.dylibs/libQt5Core.5.9.7.dylib",
             "@rpath/libQt5PrintSupport.5.dylib": "@loader_path/../../.dylibs/libQt5PrintSupport.5.9.7.dylib",
             "@rpath/libQt5Widgets.5.dylib": "@loader_path/../../.dylibs/libQt5Widgets.5.9.7.dylib",
             "@rpath/libQt5Svg.5.dylib": "@loader_path/../miniconda/libQt5Svg.5.9.7.dylib",
             "@rpath/libc++.1.dylib": "@loader_path/../../.dylibs/libc++.1.dylib",
             "@rpath/libjpeg.9.dylib": "@rpath/libjpeg.9.dylib"
           }

for root, dirs, files in os.walk('gam_g4/plugins'):
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
            depLib = line.lstrip().split(' ')[0]
            print(depLib)
            if not os.path.basename(depLib) == os.path.basename(lib):
                command = "install_name_tool -change " + depLib + " " + dictLibs[depLib] + " " + lib
                output = subprocess.run(command.split(), stdout=subprocess.PIPE)
    #print(output)

