/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include "GatePhaseSpaceActor.h"

void init_GatePhaseSpaceActor(py::module &m) {

    py::class_<GatePhaseSpaceActor, GateVActor>(m, "GatePhaseSpaceActor")
        .def(py::init<py::dict &>())
        .def_readonly("fNumberOfAbsorbedEvents", &GatePhaseSpaceActor::fNumberOfAbsorbedEvents);
}

