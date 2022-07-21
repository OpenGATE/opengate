/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamHitsProjectionActor.h"

void init_GamHitsProjectionActor(py::module &m) {

    py::class_<GamHitsProjectionActor,
        std::unique_ptr<GamHitsProjectionActor, py::nodelete>,
        GamVActor>(m, "GamHitsProjectionActor")
        .def(py::init<py::dict &>())
        .def_readwrite("fImage", &GamHitsProjectionActor::fImage)
        .def_readwrite("fPhysicalVolumeName", &GamHitsProjectionActor::fPhysicalVolumeName);
}

