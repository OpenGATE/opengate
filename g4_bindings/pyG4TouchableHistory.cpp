/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VSolid.hh"
#include "G4TouchableHistory.hh"

void init_G4TouchableHistory(py::module &m) {
    py::class_<G4TouchableHistory>(m, "G4TouchableHistory")

            .def("GetVolume", &G4TouchableHistory::GetVolume, py::return_value_policy::reference)
            .def("GetSolid", &G4TouchableHistory::GetSolid, py::return_value_policy::reference)
            .def("GetTranslation", &G4TouchableHistory::GetTranslation)
            .def("GetRotation", &G4TouchableHistory::GetRotation)
            .def("GetReplicaNumber", &G4TouchableHistory::GetReplicaNumber)
            .def("GetHistoryDepth", &G4TouchableHistory::GetHistoryDepth)
            .def("GetHistory", &G4TouchableHistory::GetHistory, py::return_value_policy::reference);
}

