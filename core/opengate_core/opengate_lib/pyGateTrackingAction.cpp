/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4UserTrackingAction.hh"
#include "GateTrackingAction.h"

void init_GateTrackingAction(py::module &m) {

  py::class_<GateTrackingAction, G4UserTrackingAction,
             std::unique_ptr<GateTrackingAction, py::nodelete>>(
      m, "GateTrackingAction")
      .def(py::init())
      .def_readwrite("fUserEventInformationFlag",
                     &GateTrackingAction::fUserEventInformationFlag)
      .def("RegisterActor", &GateTrackingAction::RegisterActor);
}
