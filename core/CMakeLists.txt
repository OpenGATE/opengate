# --------------------------------------------------
#   Copyright (C): OpenGATE Collaboration
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE.md for further details
# --------------------------------------------------

cmake_minimum_required(VERSION 2.8.12)

# remove warning about project version
cmake_policy(SET CMP0048 NEW)

project(opengate_core)

set(CMAKE_CXX_STANDARD 17)

# Need Geant4
find_package(Geant4 REQUIRED OPTIONAL_COMPONENTS qt)
include(${Geant4_USE_FILE})
message(STATUS "OPENGATE - Geant4 version ${Geant4_VERSION}")

if (Geant4_multithreaded_FOUND)
    message(STATUS "OPENGATE - Geant4 is compiled with MT (MultiThread)")
ENDIF ()
find_package(Threads REQUIRED)

#GDML
IF (Geant4_gdml_FOUND)
    message(STATUS "OPENGATE - Geant4 is compiled with GDML")
    add_definitions(-DUSE_GDML=1)
ENDIF ()

# QT in Geant4
IF (Geant4_qt_FOUND OR Geant4_vis_opengl_x11_FOUND)
    message(STATUS "OPENGATE - Geant4 is compiled with QT")
    find_package(OpenGL QUIET)
    include_directories(${OPENGL_INCLUDE_DIR})
    add_definitions(-DUSE_USE_VISU=1)
ELSE ()
    message(STATUS "OPENGATE without Geant4 visualisation")
    add_definitions(-DUSE_USE_VISU=0)
ENDIF ()

# Need pybind11
add_subdirectory(external/pybind11)
#find_package(pybind11 REQUIRED)
#message(STATUS "OPENGATE - pybind11 version = ${pybind11_VERSION}")
#message(STATUS "OPENGATE - pybind11 = ${pybind11_INCLUDE_DIRS}")

# itk
find_package(ITK 5.0 REQUIRED)
if (ITK_FOUND)
    include("${ITK_USE_FILE}")
    message(STATUS "OPENGATE - ITK version = ${ITK_VERSION}")
else (ITK_FOUND)
    message(FATAL_ERROR "Cannot build without ITK.  Please set ITK_DIR.")
endif (ITK_FOUND)

# fmt
add_subdirectory(external/fmt EXCLUDE_FROM_ALL)

# root ? NOT root for the moment (use G4GenericAnalysisManager)
#IF (FALSE)
#find_package(ROOT)
#if (ROOT_FOUND)
#    include_directories(${ROOT_INCLUDE_DIRS})
#    set(LINK_DIRECTORIES ${ROOT_LIBRARY_DIR})
#    message(STATUS "OPENGATE - ROOT version = ${ROOT_VERSION} in ${ROOT_INCLUDE_DIRS} ${ROOT_LIBRARY_DIR}")
#else (ROOT_FOUND)
#    MESSAGE("Root not found! Please install Root and make it available in PATH")
#ENDIF()
#ENDIF()


# Create the geant4 python module
file(GLOB all_SRCS
        "${PROJECT_SOURCE_DIR}/opengate_core/g4_bindings/*.cpp"
        "${PROJECT_SOURCE_DIR}/opengate_core/opengate_lib/*.cpp"
        "${PROJECT_SOURCE_DIR}/opengate_core/opengate_lib/digitizer/*.cpp"
        )
pybind11_add_module(opengate_core
        #NO_EXTRAS
        #THIN_LTO
        opengate_core/opengate_core.cpp
        ${all_SRCS}
        )

if (WIN32)
    if (MSVC)
        #message("I am MSCV")
        set_target_properties(opengate_core PROPERTIES COMPILE_FLAGS "/MP /bigobj ")
        #set_target_properties(opengate_core PROPERTIES LINK_FLAGS "/NODEFAULTLIB:itkvnl_algo-5.1.lib")

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
#target_link_libraries(opengate_core PRIVATE pybind11::module ${Geant4_LIBRARIES} Threads::Threads ${ITK_LIBRARIES})

# additional utilities
target_include_directories(opengate_core PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/external/)

#set(CMAKE_VERBOSE_MAKEFILE on)
target_link_libraries(opengate_core PRIVATE pybind11::module ${Geant4_LIBRARIES} Threads::Threads ${ITK_LIBRARIES} fmt::fmt-header-only)

# Do not not add ${PYTHON_LIBRARIES}) here (seg fault)
