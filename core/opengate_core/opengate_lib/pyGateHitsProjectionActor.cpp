/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateHitsProjectionActor.h"

void init_GateHitsProjectionActor(py::module &m) {

    py::class_<GateHitsProjectionActor,
        std::unique_ptr<GateHitsProjectionActor, py::nodelete>,
        GateVActor>(m, "GateHitsProjectionActor")
        .def(py::init<py::dict &>())
        .def_readwrite("fImage", &GateHitsProjectionActor::fImage)
        .def_readwrite("fPhysicalVolumeName", &GateHitsProjectionActor::fPhysicalVolumeName);
}

