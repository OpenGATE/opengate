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
#include "GateSPSVoxelsPosDistribution.h"

void init_GateSPSVoxelsPosDistribution(py::module &m) {

  py::class_<GateSPSVoxelsPosDistribution, GateSPSPosDistribution>(
      m, "GateSPSVoxelsPosDistribution")
      .def(py::init())
      .def("SetCumulativeDistributionFunction",
           &GateSPSVoxelsPosDistribution::SetCumulativeDistributionFunction)
      .def("VGenerateOne", &GateSPSVoxelsPosDistribution::VGenerateOne)
      .def_readwrite("cpp_edep_image",
                     &GateSPSVoxelsPosDistribution::cpp_image);
}
