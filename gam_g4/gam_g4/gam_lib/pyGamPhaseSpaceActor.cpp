/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include "GamPhaseSpaceActor.h"

void init_GamPhaseSpaceActor(py::module &m) {

    py::class_<GamPhaseSpaceActor, GamVActor>(m, "GamPhaseSpaceActor")
        .def(py::init<py::dict &>())
        .def_readonly("fNumberOfAbsorbedEvents", &GamPhaseSpaceActor::fNumberOfAbsorbedEvents);
}

