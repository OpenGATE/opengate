# --------------------------------------------------
#   Copyright (C): OpenGATE Collaboration
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE.md for further details
# --------------------------------------------------

cmake_minimum_required(VERSION 2.8.12)

# remove warning about project version
cmake_policy(SET CMP0048 NEW)

project(gam_g4)

set(CMAKE_CXX_STANDARD 17)

# Need Geant4
find_package(Geant4 REQUIRED qt)
include(${Geant4_USE_FILE})
message(STATUS "GAM - Geant4 version ${Geant4_VERSION}")

if (Geant4_multithreaded_FOUND)
    message(STATUS "GAM - Geant4 is compiled with MT (MultiThread)")
ENDIF ()
find_package(Threads REQUIRED)


# QT in Geant4
IF (Geant4_qt_FOUND OR Geant4_vis_opengl_x11_FOUND)
    message(STATUS "GAM - Geant4 is compiled with QT")
    find_package(OpenGL QUIET)
    include_directories(${OPENGL_INCLUDE_DIR})
ENDIF ()

# Need pybind11
add_subdirectory(pybind11)
#find_package(pybind11 REQUIRED)
#message(STATUS "GAM - pybind11 version = ${pybind11_VERSION}")
#message(STATUS "GAM - pybind11 = ${pybind11_INCLUDE_DIRS}")

# itk
find_package(ITK 5.0 REQUIRED)
if (ITK_FOUND)
    include("${ITK_USE_FILE}")
    message(STATUS "GAM - ITK version = ${ITK_VERSION}")
else (ITK_FOUND)
    message(FATAL_ERROR "Cannot build without ITK.  Please set ITK_DIR.")
endif (ITK_FOUND)

# fmt
add_subdirectory(fmt EXCLUDE_FROM_ALL)

# root ? NOT root for the moment (use G4GenericAnalysisManager)
#IF (FALSE)
#find_package(ROOT)
#if (ROOT_FOUND)
#    include_directories(${ROOT_INCLUDE_DIRS})
#    set(LINK_DIRECTORIES ${ROOT_LIBRARY_DIR})
#    message(STATUS "GAM - ROOT version = ${ROOT_VERSION} in ${ROOT_INCLUDE_DIRS} ${ROOT_LIBRARY_DIR}")
#else (ROOT_FOUND)
#    MESSAGE("Root not found! Please install Root and make it available in PATH")
#ENDIF()
#ENDIF()


# Create the geant4 python module
file(GLOB all_SRCS
        "${PROJECT_SOURCE_DIR}/gam_g4/g4_bindings/*.cpp"
        "${PROJECT_SOURCE_DIR}/gam_g4/gam_lib/*.cpp"
        )
pybind11_add_module(gam_g4
        #NO_EXTRAS
        #THIN_LTO
        gam_g4/gam_g4.cpp
        ${all_SRCS}
        )

if (WIN32)
    if (MSVC)
        #message("I am MSCV")
        set_target_properties(gam_g4 PROPERTIES COMPILE_FLAGS "/MP /bigobj ")
        #set_target_properties(gam_g4 PROPERTIES LINK_FLAGS "/NODEFAULTLIB:itkvnl_algo-5.1.lib")

        # /NODEFAULTLIB
        # set_target_properties(geant4 PROPERTIES LINK_FLAGS "/LTCG ")
        #        if (NOT ${U_CMAKE_BUILD_TYPE} MATCHES DEBUG)
        #            message("I am HERE")
        #            # Enforce size-based optimization and link time code generation on MSVC
        #            # (~30% smaller binaries in experiments).
        #            set_target_properties(geant4 APPEND_STRING PROPERTY COMPILE_FLAGS "/Os /GL ")
        #            set_target_properties(geant4 APPEND_STRING PROPERTY LINK_FLAGS "/LTCG ")
        #        endif()
    endif ()
endif ()

# correct one on OSX
#target_link_libraries(gam_g4 PRIVATE pybind11::module ${Geant4_LIBRARIES} Threads::Threads ${ITK_LIBRARIES})

#set(CMAKE_VERBOSE_MAKEFILE on)
target_link_libraries(gam_g4 PRIVATE pybind11::module ${Geant4_LIBRARIES} Threads::Threads ${ITK_LIBRARIES} fmt::fmt-header-only)
#target_link_libraries(gam_g4 PRIVATE pybind11::module ${Geant4_LIBRARIES} ${ROOT_LIBRARIES}  Threads::Threads ${ITK_LIBRARIES} fmt::fmt-header-only)

## FIXME on linux need something like the following to avoid "cannot allocate memory in static TLS block"
#export LD_PRELOAD=/home/dsarrut/src/geant4/build-geant4.10.07-debug-mt/BuildProducts/lib64/libG4processes.so
#export LD_PRELOAD=/home/dsarrut/src/geant4/build-geant4.10.07-debug-mt/BuildProducts/lib64/libG4geometry.so


# Do not not add ${PYTHON_LIBRARIES}) here (seg fault)
