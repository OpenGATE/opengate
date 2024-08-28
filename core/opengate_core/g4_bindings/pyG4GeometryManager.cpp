/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4GeometryManager.hh"
#include "G4VPhysicalVolume.hh"

void init_G4GeometryManager(py::module &m) {

  // No destructor for this singleton class
  py::class_<G4GeometryManager,
             std::unique_ptr<G4GeometryManager, py::nodelete>>(
      m, "G4GeometryManager")

      .def_static("GetInstance", &G4GeometryManager::GetInstance,
                  py::return_value_policy::reference)

      .def("OpenGeometry", &G4GeometryManager::OpenGeometry)
      .def("CloseGeometry", &G4GeometryManager::CloseGeometry);
}
