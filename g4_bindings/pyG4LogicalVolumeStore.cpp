/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4LogicalVolumeStore.hh"

void init_G4LogicalVolumeStore(py::module &m) {

    py::class_<G4LogicalVolumeStore>(m, "G4LogicalVolumeStore")

        .def("GetInstance", &G4LogicalVolumeStore::GetInstance,
             py::return_value_policy::reference)
        .def("GetVolume", &G4LogicalVolumeStore::GetVolume);
}
