/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include <vector>
#include "G4RegionStore.hh"
#include "G4Region.hh"

void init_G4RegionStore(py::module &m) {
    py::class_<G4RegionStore>(m, "G4RegionStore")
        .def("size", [](G4RegionStore *r) { return r->size(); })
        .def("Get", [](G4RegionStore *r, int i) { return (*r)[i]; }, py::return_value_policy::reference)
        .def("GetInstance", &G4RegionStore::GetInstance, py::return_value_policy::reference)
        .def("GetRegion", &G4RegionStore::GetRegion, py::return_value_policy::reference)
        .def("FindOrCreateRegion", &G4RegionStore::FindOrCreateRegion);
}
