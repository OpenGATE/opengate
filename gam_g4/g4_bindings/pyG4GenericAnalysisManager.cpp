/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4GenericAnalysisManager.hh"

namespace py = pybind11;

void init_G4GenericAnalysisManager(py::module &m) {

    py::class_<G4GenericAnalysisManager,
        std::unique_ptr<G4GenericAnalysisManager>>(m, "G4GenericAnalysisManager")
        //.def(py::init<>())
        .def_static("Instance", &G4GenericAnalysisManager::Instance, py::return_value_policy::reference)
        .def("GetNofNtuples", &G4GenericAnalysisManager::GetNofNtuples)
        //.def("GetNtuple", &G4GenericAnalysisManager::GetNtuple)
        ;

}
