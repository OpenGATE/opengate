/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamParticleFilter.h"
#include "GamVFilter.h"

void init_GamParticleFilter(py::module &m) {
    py::class_<GamParticleFilter, GamVFilter>(m, "GamParticleFilter")
        .def(py::init())
        .def("Initialize", &GamParticleFilter::Initialize);
}

