/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamSPSVoxelsPosDistribution.h"
#include "GamSPSPosDistribution.h"

void init_GamSPSVoxelsPosDistribution(py::module &m) {

    py::class_<GamSPSVoxelsPosDistribution, GamSPSPosDistribution>(m, "GamSPSVoxelsPosDistribution")
        .def(py::init())
        .def("SetCumulativeDistributionFunction", &GamSPSVoxelsPosDistribution::SetCumulativeDistributionFunction)
        .def_readwrite("cpp_edep_image", &GamSPSVoxelsPosDistribution::cpp_image);
}

