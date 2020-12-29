/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamSteppingAction.h"
#include "G4UserSteppingAction.hh"

void init_GamSteppingAction(py::module &m) {

    py::class_<GamSteppingAction, G4UserSteppingAction>(m, "GamSteppingAction")
        .def(py::init())
        .def("RegisterActor", &GamSteppingAction::RegisterActor);
}

