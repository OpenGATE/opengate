/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateSPSPosDistribution.h"
#include "G4SPSPosDistribution.hh"

void init_GateSPSPosDistribution(py::module &m) {

    py::class_<GateSPSPosDistribution, G4SPSPosDistribution>(m, "GateSPSPosDistribution")
        .def(py::init());
}

