/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamKineticEnergyFilter.h"
#include "GamVFilter.h"

void init_GamKineticEnergyFilter(py::module &m) {
    py::class_<GamKineticEnergyFilter, GamVFilter>(m, "GamKineticEnergyFilter")
        .def(py::init())
        .def("Initialize", &GamKineticEnergyFilter::Initialize);
}

