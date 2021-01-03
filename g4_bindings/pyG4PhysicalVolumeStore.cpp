/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4PhysicalVolumeStore.hh"

void init_G4PhysicalVolumeStore(py::module &m) {

    py::class_<G4PhysicalVolumeStore>(m, "G4PhysicalVolumeStore")

            .def("GetInstance", &G4PhysicalVolumeStore::GetInstance,
                 py::return_value_policy::reference)
            .def("GetVolume", &G4PhysicalVolumeStore::GetVolume);
}
