/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSteppingAction.h"
#include <G4UserSteppingAction.hh>
#include <pybind11/pybind11.h>

void init_GateSteppingAction(py::module &m) {
  py::class_<GateSteppingAction, G4UserSteppingAction,
             std::unique_ptr<GateSteppingAction, py::nodelete>>(
      m, "GateSteppingAction")
      .def(py::init())
      .def("RegisterAuxiliaryAttribute",
           &GateSteppingAction::RegisterAuxiliaryAttribute);
}
