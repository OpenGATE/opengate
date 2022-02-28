/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Region.hh"
#include "G4ProductionCuts.hh"
#include "G4LogicalVolume.hh"

void init_G4Region(py::module &m) {
    py::class_<G4Region>(m, "G4Region")

        //.def(py::init<>())
        .def("GetName", &G4Region::GetName)
        .def("SetProductionCuts", &G4Region::SetProductionCuts)
        .def("GetProductionCuts", &G4Region::GetProductionCuts)
        .def("AddRootLogicalVolume", &G4Region::AddRootLogicalVolume);
}
