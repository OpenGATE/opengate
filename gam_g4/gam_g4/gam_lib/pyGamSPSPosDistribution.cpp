/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamSPSPosDistribution.h"
#include "G4SPSPosDistribution.hh"

void init_GamSPSPosDistribution(py::module &m) {

    py::class_<GamSPSPosDistribution, G4SPSPosDistribution>(m, "GamSPSPosDistribution")
        .def(py::init());
}

