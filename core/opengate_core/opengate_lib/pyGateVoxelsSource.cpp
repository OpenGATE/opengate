/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateVoxelsSource.h"

void init_GateVoxelsSource(py::module &m) {

    py::class_<GateVoxelsSource, GateGenericSource>(m, "GateVoxelsSource")
        .def(py::init())
        .def("GetSPSVoxelPosDistribution", &GateVoxelsSource::GetSPSVoxelPosDistribution,
             py::return_value_policy::reference_internal)
        .def("InitializeUserInfo", &GateVoxelsSource::InitializeUserInfo);
}

