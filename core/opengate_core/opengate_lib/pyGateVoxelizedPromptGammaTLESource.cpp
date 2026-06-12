/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVoxelizedPromptGammaTLESource.h"
#include <pybind11/pybind11.h>

void init_GateVoxelizedPromptGammaTLESource(py::module &m) {

  py::class_<GateVoxelizedPromptGammaTLESource, GateGenericSource>(
      m, "GateVoxelizedPromptGammaTLESource")
      .def(py::init())
      .def("GetSPSVoxelPosDistribution",
           &GateVoxelizedPromptGammaTLESource::GetSPSVoxelPosDistribution,
           py::return_value_policy::reference_internal)
      .def("InitializeUserInfo",
           &GateVoxelizedPromptGammaTLESource::InitializeUserInfo);
}
