/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateHitsAdderActor.h"

void init_GateHitsAdderActor(py::module &m) {

    py::class_<GateHitsAdderActor,
        std::unique_ptr<GateHitsAdderActor, py::nodelete>,
        GateVActor>(m, "GateHitsAdderActor")
        .def(py::init<py::dict &>());
}

