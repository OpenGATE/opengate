cmake_minimum_required(VERSION 2.8.12)
project(py_geant4)

find_package(Geant4 REQUIRED)

INCLUDE(${Geant4_USE_FILE})

find_package(pybind11 REQUIRED)

pybind11_add_module(geant4 geant4.cpp 
  pyG4ThreeVector.cpp
  pyG4RunManager.cpp 
  )

target_link_libraries(geant4 PRIVATE pybind11::module ${Geant4_LIBRARIES})

