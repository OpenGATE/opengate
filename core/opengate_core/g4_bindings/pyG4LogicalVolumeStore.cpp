/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <ct/functionarity.h>

namespace py = pybind11;

#include "G4LogicalVolumeStore.hh"

void init_G4LogicalVolumeStore(py::module &m) {
    using pybind11::operator""_a;

    auto g4LogicalVolumeStore = py::class_<G4LogicalVolumeStore>(m, "G4LogicalVolumeStore")
        .def("GetInstance", &G4LogicalVolumeStore::GetInstance, py::return_value_policy::reference)
        // Additional functions, because the store is a vector
        .def("size", [](G4LogicalVolumeStore *r) { return r->size(); })
        .def("Get", [](G4LogicalVolumeStore *r, int i) {
            return (*r)[i];
        }, py::return_value_policy::reference);

    constexpr auto getVolumeArity = ct::functionArity(&G4LogicalVolumeStore::GetVolume);
    if constexpr(getVolumeArity == 2) {
      g4LogicalVolumeStore
          .def("GetVolume", &G4LogicalVolumeStore::GetVolume,
               "name"_a,
               "verbose"_a = true
          );
    } else if constexpr(getVolumeArity == 3) {
      g4LogicalVolumeStore
          .def("GetVolume", &G4LogicalVolumeStore::GetVolume,
               "name"_a,
               "verbose"_a = true,
               "reverseSearch"_a = false
          );
    }
}
