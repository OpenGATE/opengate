/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamRunAction.h"
#include "GamSourceManager.h"
#include "G4UserRunAction.hh"

void init_GamRunAction(py::module &m) {

    py::class_<GamRunAction,
        G4UserRunAction,
        std::unique_ptr<GamRunAction, py::nodelete>>(m, "GamRunAction")
        .def(py::init<GamSourceManager *>())
        .def("RegisterActor", &GamRunAction::RegisterActor);
}

