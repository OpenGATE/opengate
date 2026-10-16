/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSPSPosDistribution.h"
#include "GateSPSVoxelsPosDistribution.h"
#include <cstddef>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

namespace {

using CDFArray = py::array_t<double, py::array::c_style | py::array::forcecast>;

void SetCumulativeDistributionFunction(GateSPSVoxelsPosDistribution &source,
                                       const CDFArray &cdfZ,
                                       const CDFArray &cdfY,
                                       const CDFArray &cdfX) {
  source.SetCumulativeDistributionFunction(cdfZ.data(), cdfY.data(),
                                           cdfX.data(), cdfX.shape(2),
                                           cdfX.shape(1), cdfY.shape(0));
}

} // namespace

void init_GateSPSVoxelsPosDistribution(py::module &m) {

  py::class_<GateSPSVoxelsPosDistribution, GateSPSPosDistribution>(
      m, "GateSPSVoxelsPosDistribution")
      .def(py::init())
      .def("SetCumulativeDistributionFunction",
           &SetCumulativeDistributionFunction)
      .def("VGenerateOne", &GateSPSVoxelsPosDistribution::VGenerateOne)
      .def_readwrite("cpp_edep_image",
                     &GateSPSVoxelsPosDistribution::cpp_image);
}
