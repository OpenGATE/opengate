/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <functionarity.h>

namespace py = pybind11;

#include "G4PhysicalVolumeStore.hh"

void init_G4PhysicalVolumeStore(py::module &m) {
    using pybind11::operator""_a;

    auto g4PhysicalVolumeStore = py::class_<G4PhysicalVolumeStore>(m, "G4PhysicalVolumeStore")
        .def("GetInstance", &G4PhysicalVolumeStore::GetInstance,
             py::return_value_policy::reference);

    constexpr auto getVolumeArity = ct::functionArity(&G4PhysicalVolumeStore::GetVolume);
    if constexpr(getVolumeArity == 2) {
      g4PhysicalVolumeStore
          .def("GetVolume", &G4PhysicalVolumeStore::GetVolume,
               "name"_a,
               "verbose"_a = true
          );
    } else if constexpr(getVolumeArity == 3) {
      g4PhysicalVolumeStore
          .def("GetVolume", &G4PhysicalVolumeStore::GetVolume,
               "name"_a,
               "verbose"_a = true,
               "reverseSearch"_a = false
          );
    }
}
