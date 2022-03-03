/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamTrackingAction.h"
#include "G4UserTrackingAction.hh"

void init_GamTrackingAction(py::module &m) {

    py::class_<GamTrackingAction,
    G4UserTrackingAction,
            std::unique_ptr<GamTrackingAction, py::nodelete>>(m, "GamTrackingAction")
            .def(py::init())
            .def("RegisterActor", &GamTrackingAction::RegisterActor);
}

