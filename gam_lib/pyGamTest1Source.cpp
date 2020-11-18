/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamTest1Source.h"
#include "GamVSource.h"

void init_GamTest1Source(py::module &m) {

    py::class_<GamTest1Source, GamVSource>(m, "GamTest1Source")
        .def(py::init())
        .def_readonly("n", &GamTest1Source::n)
        .def("initialize", &GamTest1Source::initialize);
}

