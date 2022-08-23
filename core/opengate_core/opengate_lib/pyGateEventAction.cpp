/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateEventAction.h"

void init_GateEventAction(py::module &m) {

  py::class_<GateEventAction, G4UserEventAction,
             std::unique_ptr<GateEventAction, py::nodelete>>(m,
                                                             "GateEventAction")
      .def(py::init())
      .def("RegisterActor", &GateEventAction::RegisterActor);
}
