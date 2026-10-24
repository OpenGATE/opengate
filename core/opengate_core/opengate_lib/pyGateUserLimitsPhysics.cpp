/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUserLimitsPhysics.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

void init_GateUserLimitsPhysics(py::module &m) {
  // G4VModularPhysicsList owns the constructors registered with
  // RegisterPhysics and deletes them with the physics list: Python must not
  // delete it as well.
  py::class_<GateUserLimitsPhysics, G4VPhysicsConstructor,
             std::unique_ptr<GateUserLimitsPhysics, py::nodelete>>(
      m, "GateUserLimitsPhysics")
      .def(py::init<const std::vector<std::string> &, bool, bool>(),
           // The arguments are converted before the guard is taken. The
           // constructor only stores flat values; the Geant4 objects are
           // created later, in C++, by ConstructProcess.
           py::call_guard<py::gil_scoped_release>(), py::arg("particles"),
           py::arg("apply_to_all") = false,
           py::arg("apply_to_all_charged") = false);
}
