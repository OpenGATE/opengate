
#include <pybind11/pybind11.h>
#include <pybind11/operators.h>


#include "G4RunManager.hh"

namespace py = pybind11;



void init_G4RunManager(py::module & m) {
  
  py::class_<G4RunManager>(m, "G4RunManager")
    .def(py::init())


    // test with known arg type
    .def("RestoreRandomNumberStatus", &G4RunManager::RestoreRandomNumberStatus)

    // test with unknown arg type
    //    .def("SetUserInitialization", &G4RunManager::SetUserInitialization)

    ;

}
