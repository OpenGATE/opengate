/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4NavigationHistory.hh"
#include "G4VSolid.hh"

void init_G4NavigationHistory(py::module &m) {
  py::class_<G4NavigationHistory>(m, "G4NavigationHistory")

      .def("GetDepth", &G4NavigationHistory::GetDepth)
      .def("GetMaxDepth", &G4NavigationHistory::GetMaxDepth)
      .def("GetTransform", &G4NavigationHistory::GetTransform)
      .def("GetTopTransform", &G4NavigationHistory::GetTopTransform)
      .def("GetReplicaNo", &G4NavigationHistory::GetReplicaNo)
      .def("GetVolumeType", &G4NavigationHistory::GetVolumeType)
      .def("GetVolume", &G4NavigationHistory::GetVolume,
           py::return_value_policy::reference);
}
