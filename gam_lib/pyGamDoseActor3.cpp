/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamDoseActor3.h"


void init_GamDoseActor3(py::module &m) {
    py::class_<GamDoseActor3, GamVActor>(m, "GamDoseActor3")
        .def(py::init())
        .def_readwrite("cpp_image", &GamDoseActor3::cpp_image)
        .def("SaveImage", &GamDoseActor3::SaveImage);
}

