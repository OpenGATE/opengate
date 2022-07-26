/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Navigator.hh"

void init_G4Navigator(py::module &m) {
    py::class_<G4Navigator>(m, "G4Navigator")
        .def(py::init())
        .def("LocateGlobalPointAndSetup", &G4Navigator::LocateGlobalPointAndSetup, py::return_value_policy::reference)
        .def("SetWorldVolume", &G4Navigator::SetWorldVolume)
        .def("GetLocalToGlobalTransform", &G4Navigator::GetLocalToGlobalTransform);
}

