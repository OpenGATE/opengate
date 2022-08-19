/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateRunAction.h"
#include "GateSourceManager.h"
#include "G4UserRunAction.hh"

void init_GateRunAction(py::module &m) {

    py::class_<GateRunAction,
        G4UserRunAction,
        std::unique_ptr<GateRunAction, py::nodelete>>(m, "GateRunAction")
        .def(py::init<GateSourceManager *>())
        .def("RegisterActor", &GateRunAction::RegisterActor);
}

