/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateTimeStepAction.h"

void init_GateTimeStepAction(py::module &m) {

  py::class_<GateTimeStepAction, G4UserTimeStepAction,
             std::unique_ptr<GateTimeStepAction, py::nodelete>>(
      m, "GateTimeStepAction")
      .def(py::init())
      .def("RegisterActor", &GateTimeStepAction::RegisterActor,
           py::arg("actor"));
}
