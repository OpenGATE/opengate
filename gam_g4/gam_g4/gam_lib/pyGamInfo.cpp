/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamInfo.h"

void init_GamInfo(py::module &m) {
    py::class_<GamInfo>(m, "GamInfo")
        .def(py::init())
        .def("get_G4MULTITHREADED", &GamInfo::get_G4MULTITHREADED)
        .def("get_G4Version", &GamInfo::get_G4Version)
        .def("get_G4Date", &GamInfo::get_G4Date)
        .def("get_ITKVersion", &GamInfo::get_ITKVersion);
}

