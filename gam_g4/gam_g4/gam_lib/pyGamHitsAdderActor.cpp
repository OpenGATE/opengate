/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamHitsAdderActor.h"

void init_GamHitsAdderActor(py::module &m) {

    py::class_<GamHitsAdderActor,
        std::unique_ptr<GamHitsAdderActor, py::nodelete>,
        GamVActor>(m, "GamHitsAdderActor")
        .def(py::init<py::dict &>());
}

