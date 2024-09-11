/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4UserStackingAction.hh"
#include "GateSourceManager.h"
#include "GateStackingAction.h"

void init_GateStackingAction(py::module &m) {

  py::class_<GateStackingAction, G4UserStackingAction,
             std::unique_ptr<GateStackingAction, py::nodelete>>(
      m, "GateStackingAction")
      .def(py::init<>())
      .def("RegisterActor", &GateStackingAction::RegisterActor);
}
