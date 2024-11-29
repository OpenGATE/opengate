/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateVoxelSource.h"

void init_GateVoxelSource(py::module &m) {

  py::class_<GateVoxelSource, GateGenericSource>(m, "GateVoxelSource")
      .def(py::init())
      .def("GetSPSVoxelPosDistribution",
           &GateVoxelSource::GetSPSVoxelPosDistribution,
           py::return_value_policy::reference_internal)
      .def("InitializeUserInfo", &GateVoxelSource::InitializeUserInfo);
}
