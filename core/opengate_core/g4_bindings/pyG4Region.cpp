/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4LogicalVolume.hh"
#include "G4ProductionCuts.hh"
#include "G4Region.hh"
#include "G4UserLimits.hh"

void init_G4Region(py::module &m) {
  py::class_<G4Region, std::unique_ptr<G4Region, py::nodelete>>(m, "G4Region")

      //.def(py::init<>())
      // no constructor needed because regions are created via the
      // FindOrCreateRegion method of Geant4's RegionStore
      .def("GetName", &G4Region::GetName)
      .def("SetProductionCuts", &G4Region::SetProductionCuts)
      .def("GetProductionCuts", &G4Region::GetProductionCuts,
           py::return_value_policy::reference_internal)
      .def("SetUserLimits", &G4Region::SetUserLimits)
      .def("GetUserLimits", &G4Region::GetUserLimits,
           py::return_value_policy::reference_internal)
      .def("AddRootLogicalVolume", &G4Region::AddRootLogicalVolume);
}
