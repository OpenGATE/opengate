/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "pybind11/pybind11.h"
#include <G4ParticleDefinition.hh>
#include <G4PhysicsListHelper.hh>
#include <G4VProcess.hh>

namespace py = pybind11;

void init_G4PhysicsListHelper(py::module &m) {
  py::class_<G4PhysicsListHelper,
             std::unique_ptr<G4PhysicsListHelper, py::nodelete>>(
      m, "G4PhysicsListHelper")
      .def_static("GetPhysicsListHelper",
                  &G4PhysicsListHelper::GetPhysicsListHelper,
                  py::return_value_policy::reference)
      .def("RegisterProcess", &G4PhysicsListHelper::RegisterProcess,
           py::arg("process"), py::arg("particle"));
}
