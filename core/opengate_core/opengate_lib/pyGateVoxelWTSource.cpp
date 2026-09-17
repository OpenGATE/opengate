/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateSPSVoxelsPosDistribution.h"
#include "GateVoxelWTSource.h"

void init_GateVoxelWTSource(py::module &m) {

  py::class_<GateVoxelWTSource, GateWindowTurboSource>(m, "GateVoxelWTSource")
      .def(py::init())
      .def("GetSPSVoxelPosDistribution",
           &GateVoxelWTSource::GetSPSVoxelPosDistribution,
           py::return_value_policy::reference_internal)
      .def("InitializeUserInfo", &GateVoxelWTSource::InitializeUserInfo);
}
