/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamDoseActor.h"

void init_GamDoseActor(py::module &m) {
    py::class_<GamDoseActor,
            std::unique_ptr<GamDoseActor, py::nodelete>, GamVActor>(m, "GamDoseActor")
            .def(py::init<py::dict &>())
            .def_readwrite("cpp_image", &GamDoseActor::cpp_image);
}

